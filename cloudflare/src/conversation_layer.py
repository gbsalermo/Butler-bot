"""Contexto operacional curto, ações sobre itens recentes e agenda enriquecida.

Este módulo continua ativo para referências como ``essa``/``ela`` e para a
integração de rotinas na agenda. Ele não é mais responsável por disparar
lembretes de tarefas/compromissos: ``reliable_reminders.py`` é a autoridade.
Menus principais também não são definidos aqui; usa-se ``app.MAIN_KB``, que é
sincronizado com ``operational_menu.py`` durante o bootstrap.
"""

import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone

import app
import routine_integration
import runtime_guard
from nlu import parse_date, parse_time, validate_future
from settings import UTC_OFFSET_HOURS
from telegram_api import answer_callback, send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
CANCEL_KB = [["❌ Cancelar ação"]]
DAY_NAMES = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value).strip()


def _row(row, key, default=None):
    if row is None:
        return default
    try:
        return getattr(row, key)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


async def _rows(stmt):
    result = await stmt.all()
    data = getattr(result, "results", None)
    if data is None:
        return []
    try:
        return list(data)
    except Exception:
        return data.to_py() if hasattr(data, "to_py") else []


def _now():
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


def _keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


async def _remember(db, uid, kind, target_id=None, detail=None):
    payload = json.dumps({"kind": kind, "id": target_id, "detail": detail or {}}, ensure_ascii=False)
    await db.prepare(
        "INSERT INTO natural_events(user_id,event_type,target_id,detail) VALUES(?,'context',?,?)"
    ).bind(uid, target_id, payload).run()


async def _context(db, uid):
    row = await db.prepare(
        "SELECT detail FROM natural_events WHERE user_id=? AND event_type='context' ORDER BY id DESC LIMIT 1"
    ).bind(uid).first()
    if not row:
        return None
    try:
        return json.loads(_row(row, "detail") or "{}")
    except Exception:
        return None


async def _resolve_item(db, uid, text, kind=None):
    m = re.search(r"#(\d+)", text or "")
    if m:
        sql = "SELECT * FROM daily_items WHERE id=? AND user_id=?"
        params = [int(m.group(1)), uid]
        if kind:
            sql += " AND kind=?"
            params.append(kind)
        return await db.prepare(sql).bind(*params).first()

    n = _norm(text)
    if any(x in n.split() for x in ("essa", "esse", "isso", "ela", "ele")) or n in (
        "certo",
        "ok",
        "feito",
        "pronto",
        "ja foi",
    ):
        ctx = await _context(db, uid)
        if ctx and ctx.get("kind") in ("tarefa", "compromisso", "lembrete") and ctx.get("id"):
            row = await db.prepare("SELECT * FROM daily_items WHERE id=? AND user_id=?").bind(
                ctx["id"], uid
            ).first()
            if row and (not kind or _row(row, "kind") == kind):
                return row

    sql = "SELECT * FROM daily_items WHERE user_id=? AND status='pendente'"
    if kind:
        sql += " AND kind=?"
        stmt = db.prepare(sql + " ORDER BY id DESC LIMIT 10").bind(uid, kind)
    else:
        stmt = db.prepare(sql + " ORDER BY id DESC LIMIT 10").bind(uid)
    rs = await _rows(stmt)
    cleaned = re.sub(
        r"^(?:concluir|conclui|cancela|cancelar|adia|adiar|joga|passa|marca|marcar|essa|esse|isso|ela|ele)\s+",
        "",
        text or "",
        flags=re.I,
    ).strip()
    if cleaned:
        matches = [
            r
            for r in rs
            if _norm(cleaned) in _norm(_row(r, "title"))
            or _norm(_row(r, "title")) in _norm(cleaned)
        ]
        if len(matches) == 1:
            return matches[0]
    if len(rs) == 1:
        return rs[0]
    return None


def _parse_shift(text, now):
    n = _norm(text)
    m = re.search(r"(?:adia|adiar|joga|passa).*?(\d+)\s*(minuto|minutos|min|hora|horas)\b", n)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        delta = timedelta(hours=amount) if "hora" in unit else timedelta(minutes=amount)
        target = now + delta
        return target.date(), target.strftime("%H:%M")
    d = parse_date(text, now.date())
    tm = parse_time(text)
    if d:
        return d, tm
    return None, None


def _recurrence(text):
    n = _norm(text)
    m = re.search(r"\b(\d+)\s*x\s*(?:por|na)?\s*semana\b", n)
    if m:
        return f"{int(m.group(1))}x por semana"
    if "dias uteis" in n or "dia util" in n or "segunda a sexta" in n:
        return "segunda,terça,quarta,quinta,sexta"
    if "fim de semana" in n:
        return "sábado,domingo"
    days = [d for d in DAY_NAMES if _norm(d) in n]
    if days:
        return ",".join(days)
    if "todo dia" in n or "todos os dias" in n or "diariamente" in n:
        return "todos os dias"
    m = re.search(r"a cada\s+(\d+)\s+dias?", n)
    if m:
        return f"a cada {int(m.group(1))} dias"
    return "todos os dias"


def _times(text):
    n = _norm(text)
    out = []
    for h, m in re.findall(r"\b([01]?\d|2[0-3])(?::|h)([0-5]\d)?\b", n):
        t = f"{int(h):02d}:{int(m or 0):02d}"
        if t not in out:
            out.append(t)
    return out


async def _weekly_done(db, routine_id, target):
    start = target - timedelta(days=target.weekday())
    end = start + timedelta(days=6)
    row = await db.prepare(
        "SELECT COUNT(*) n FROM routine_logs WHERE routine_id=? AND log_date BETWEEN ? AND ? AND status='feito'"
    ).bind(routine_id, start.isoformat(), end.isoformat()).first()
    return int(_row(row, "n", 0))


async def _smart_routines(db, uid, target):
    rs = await _rows(
        db.prepare(
            "SELECT id,name,category,time_hhmm,weekdays,created_at FROM routines "
            "WHERE user_id=? AND active=1 ORDER BY name"
        ).bind(uid)
    )
    out = []
    for r in rs:
        rec = _norm(_row(r, "weekdays") or "todos os dias")
        quota = re.search(r"(\d+)x por semana", rec)
        applies = routine_integration._applies(_row(r, "weekdays"), target)
        if quota:
            goal = int(quota.group(1))
            done_week = await _weekly_done(db, int(_row(r, "id")), target)
            applies = done_week < goal
        elif rec.startswith("a cada "):
            m = re.search(r"a cada (\d+) dias", rec)
            try:
                created = date.fromisoformat((_row(r, "created_at") or "")[:10])
                applies = ((target - created).days % int(m.group(1)) == 0) if m else True
            except Exception:
                applies = True
        if not applies:
            continue

        scheduled = routine_integration._times(_row(r, "time_hhmm"))
        done = await routine_integration._status(db, int(_row(r, "id")), target, scheduled)
        if scheduled:
            marks = "  ".join(("✅" if t in done else "⏳") + f" {t}" for t in scheduled)
            suffix = (
                f" • semana {await _weekly_done(db, int(_row(r,'id')), target)}/{int(quota.group(1))}"
                if quota
                else ""
            )
            out.append(
                f"• {_row(r,'name')}\n  {marks}\n  Progresso: "
                f"{sum(t in done for t in scheduled)}/{len(scheduled)}{suffix}"
            )
        else:
            complete = "feito" in done
            suffix = (
                f" • semana {await _weekly_done(db, int(_row(r,'id')), target)}/{int(quota.group(1))}"
                if quota
                else ""
            )
            out.append(f"• {'✅' if complete else '⏳'} {_row(r,'name')}{suffix}")
    return "\n🧘 Rotinas\n" + "\n".join(out) if out else ""


async def _what_now(db, uid):
    now = _now()
    today = now.date()
    current = now.strftime("%H:%M")
    overdue = await _rows(
        db.prepare(
            "SELECT id,title,due_date,due_time FROM daily_items WHERE user_id=? "
            "AND kind='tarefa' AND status='pendente' AND "
            "(due_date<? OR (due_date=? AND due_time IS NOT NULL AND due_time<?)) "
            "ORDER BY due_date,due_time LIMIT 3"
        ).bind(uid, today.isoformat(), today.isoformat(), current)
    )
    upcoming = await _rows(
        db.prepare(
            "SELECT id,kind,title,due_time FROM daily_items WHERE user_id=? "
            "AND status='pendente' AND due_date=? AND due_time>=? ORDER BY due_time LIMIT 3"
        ).bind(uid, today.isoformat(), current)
    )
    wd = app.WEEKDAY_NAMES[today.weekday()]
    classes = await _rows(
        db.prepare(
            "SELECT s.name,ss.start_time,ss.location FROM subjects s "
            "JOIN subject_sessions ss ON ss.subject_id=s.id "
            "WHERE s.user_id=? AND s.active=1 AND ss.weekday=? AND ss.start_time>=? "
            "ORDER BY ss.start_time LIMIT 2"
        ).bind(uid, wd, current)
    )
    lines = ["🕴️ Agora:"]
    if overdue:
        lines.append("\n📌 Antes de inventar coisa nova, tem isso atrasado:")
        lines += [f"• #{_row(r,'id')} {_row(r,'title')}" for r in overdue]
        await _remember(db, uid, "tarefa", int(_row(overdue[0], "id")))
    candidates = []
    for r in upcoming:
        candidates.append(
            (_row(r, "due_time"), "📋", _row(r, "title"), int(_row(r, "id")), _row(r, "kind"))
        )
    for r in classes:
        candidates.append((_row(r, "start_time"), "🎓", _row(r, "name"), None, "aula"))
    candidates.sort(key=lambda x: x[0])
    if candidates:
        t, icon, title, iid, kind = candidates[0]
        lines.append(f"\n⏭️ Próximo horário: {icon} {t} — {title}")
        if iid:
            await _remember(db, uid, kind, iid)
    elif not overdue:
        lines.append("\nNada com horário agora. Aproveite antes que eu encontre alguma pendência escondida. 😌")
    routines = await _smart_routines(db, uid, today)
    if routines:
        lines.append(routines)
    return "\n".join(lines)


async def _smart_morning(db, uid, chat, token, today):
    base = await app.agenda_text(db, uid, today, True)
    now = _now()
    current = now.strftime("%H:%M")
    next_item = await db.prepare(
        "SELECT kind,title,due_time FROM daily_items WHERE user_id=? AND status='pendente' "
        "AND due_date=? AND due_time>=? ORDER BY due_time LIMIT 1"
    ).bind(uid, today.isoformat(), current).first()
    overdue = await db.prepare(
        "SELECT COUNT(*) n FROM daily_items WHERE user_id=? AND kind='tarefa' "
        "AND status='pendente' AND due_date<?"
    ).bind(uid, today.isoformat()).first()
    intro = "☀️ Resumo da manhã"
    if int(_row(overdue, "n", 0)):
        intro += f"\n📌 {int(_row(overdue,'n',0))} pendência(s) de dias anteriores. Elas sobreviveram à noite, infelizmente."
    if next_item:
        intro += f"\n⏭️ Primeiro compromisso com horário: {_row(next_item,'due_time')} — {_row(next_item,'title')}"
    await send_message(
        token,
        chat,
        intro
        + "\n\n"
        + base
        + "\n\nPrioridade clara, agenda visível. Agora vem aquela etapa antiquada de realmente fazer as coisas. 😌",
        reply_markup=_keyboard(app.MAIN_KB),
    )


async def handle_message(db, token, message):
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return False
    uid = await _uid(db, int(chat_id))
    if not uid:
        return False
    text = (message.get("text") or "").strip()
    n = _norm(text)

    state, payload = await runtime_guard._state(db, uid)
    if state == "guard_routine_when":
        times = _times(text)
        recurrence = _recurrence(text)
        await db.prepare(
            "INSERT INTO routines(user_id,name,category,time_hhmm,weekdays,active) VALUES(?,?,?,?,?,1)"
        ).bind(
            uid,
            payload.get("name"),
            payload.get("category"),
            ",".join(times) if times else None,
            recurrence,
        ).run()
        await runtime_guard._clear(db, uid)
        await send_message(
            token,
            int(chat_id),
            f"🧘 Rotina `{payload.get('name')}` criada.\nHorários: "
            f"{' / '.join(times) if times else 'sem horário'}\nRecorrência: {recurrence}.\n\n"
            "Ela entra na agenda quando estiver ativa; rotina não é decoração de menu.",
            reply_markup=_keyboard(routine_integration.ROUTINE_KB),
        )
        return True

    if n in (
        "o que faco agora",
        "o que eu faco agora",
        "o que tenho agora",
        "qual a proxima coisa",
        "qual minha proxima coisa",
        "o que vem agora",
    ):
        await send_message(
            token,
            int(chat_id),
            await _what_now(db, uid),
            reply_markup=_keyboard(app.MAIN_KB),
        )
        return True

    if re.search(r"\b(conclui|concluir|feito|terminei|cancela|cancelar|mantem|pendente)\b", n) or n in (
        "certo",
        "ok",
        "pronto",
        "ja foi",
    ):
        item = await _resolve_item(db, uid, text)
        if item:
            iid = int(_row(item, "id"))
            title = _row(item, "title")
            kind = _row(item, "kind")
            if any(x in n for x in ("cancela", "cancelar")):
                await db.prepare(
                    "UPDATE daily_items SET status='cancelado',cancelled_at=CURRENT_TIMESTAMP "
                    "WHERE id=? AND user_id=?"
                ).bind(iid, uid).run()
                msg = f"🚫 {title} cancelado."
            elif any(x in n for x in ("mantem", "pendente")):
                await db.prepare(
                    "UPDATE daily_items SET status='pendente',completed_at=NULL,cancelled_at=NULL "
                    "WHERE id=? AND user_id=?"
                ).bind(iid, uid).run()
                msg = f"📌 {title} continua pendente."
            else:
                await db.prepare(
                    "UPDATE daily_items SET status='concluido',completed_at=CURRENT_TIMESTAMP "
                    "WHERE id=? AND user_id=?"
                ).bind(iid, uid).run()
                msg = f"✅ {title} concluído. Certo. Era isso que eu precisava saber. 😌"
            await _remember(db, uid, kind, iid)
            await send_message(
                token,
                int(chat_id),
                msg,
                reply_markup=_keyboard(app.MAIN_KB),
            )
            return True

    if any(x in n for x in ("adia", "adiar", "joga pra", "joga para", "passa pra", "passa para")):
        item = await _resolve_item(db, uid, text)
        if item:
            d, tm = _parse_shift(text, _now())
            if not d:
                await send_message(
                    token,
                    int(chat_id),
                    "Para quando? Ex.: `amanhã às 18h`, `adia isso 30 minutos` ou `passa essa pra sexta`.",
                    reply_markup=_keyboard(CANCEL_KB),
                )
                return True
            if not tm:
                tm = _row(item, "due_time")
            ok, msg = validate_future(d, tm, _now().replace(tzinfo=None))
            if not ok:
                await send_message(token, int(chat_id), msg, reply_markup=_keyboard(app.MAIN_KB))
                return True
            await db.prepare(
                "UPDATE daily_items SET due_date=?,due_time=?,status='pendente',"
                "postpone_count=postpone_count+1,snoozed_until=? WHERE id=? AND user_id=?"
            ).bind(
                d.isoformat(),
                tm,
                f"{d.isoformat()} {tm}" if tm else d.isoformat(),
                _row(item, "id"),
                uid,
            ).run()
            await _remember(db, uid, _row(item, "kind"), int(_row(item, "id")))
            await send_message(
                token,
                int(chat_id),
                f"⏰ {_row(item,'title')} foi para {d.strftime('%d/%m')}"
                + (f" às {tm}" if tm else "")
                + ". Mais uma negociação bem-sucedida com o futuro. 😏",
                reply_markup=_keyboard(app.MAIN_KB),
            )
            return True

    if ("qual era" in n or "qual tarefa" in n) and "tarefa" in n:
        d = parse_date(text, _now().date())
        if d:
            rs = await _rows(
                db.prepare(
                    "SELECT id,title,due_time,status FROM daily_items WHERE user_id=? "
                    "AND kind='tarefa' AND due_date=? ORDER BY due_time,id"
                ).bind(uid, d.isoformat())
            )
            if rs:
                await _remember(db, uid, "tarefa", int(_row(rs[0], "id")))
                await send_message(
                    token,
                    int(chat_id),
                    f"📋 {d.strftime('%d/%m')}:\n"
                    + "\n".join(
                        f"• #{_row(r,'id')} {_row(r,'title')}"
                        + (f" — {_row(r,'due_time')}" if _row(r, "due_time") else "")
                        for r in rs
                    ),
                    reply_markup=_keyboard(app.MAIN_KB),
                )
                return True

    if re.match(r"^(?:butler[, ]+)?(?:so\s+)?(?:me\s+)?(?:avisa|avise|lembra|lembre)(?:-me)?\b", n) and (
        "me avisa" in n
        or "me avise" in n
        or "so me lembra" in n
        or "lembra que" in n
        or "lembre que" in n
    ):
        d = parse_date(text, _now().date())
        tm = parse_time(text)
        if d and tm:
            title = re.sub(
                r"^(?:Butler[,!:\-]?\s*)?(?:só\s+)?(?:me\s+)?(?:avisa|avise|lembra|lembre)(?:-me)?\s*",
                "",
                text,
                flags=re.I,
            )
            title = re.sub(r"\b(?:hoje|amanhã|amanha)\b", "", title, flags=re.I)
            title = re.sub(
                r"(?:às|as)\s*\d{1,2}(?::\d{2}|h\d{0,2})?",
                "",
                title,
                flags=re.I,
            ).strip(" ,.-")
            cur = await db.prepare(
                "INSERT INTO daily_items(user_id,kind,title,details,due_date,due_time,status) "
                "VALUES(?,'tarefa',?,'simple_reminder',?,?,'pendente') RETURNING id"
            ).bind(uid, title or "lembrete", d.isoformat(), tm).first()
            iid = int(_row(cur, "id"))
            await _remember(db, uid, "lembrete", iid)
            await send_message(
                token,
                int(chat_id),
                f"🔔 Lembrete simples salvo para {d.strftime('%d/%m')} às {tm}: {title}. "
                "Depois de avisar, ele é arquivado; não vou fingir que isso virou tarefa.",
                reply_markup=_keyboard(app.MAIN_KB),
            )
            return True
    return False


async def handle_callback(db, token, callback):
    data = callback.get("data") or ""
    qid = callback.get("id")
    message = callback.get("message") or {}
    chat = (message.get("chat") or {}).get("id")
    if not chat or not data.startswith("item:"):
        return False
    uid = await _uid(db, int(chat))
    if not uid:
        return False
    parts = data.split(":")
    action = parts[1]
    iid = int(parts[2])
    item = await db.prepare("SELECT * FROM daily_items WHERE id=? AND user_id=?").bind(iid, uid).first()
    if not item:
        if qid:
            await answer_callback(token, qid, "Item não encontrado")
        return True
    if action == "done":
        await db.prepare(
            "UPDATE daily_items SET status='concluido',completed_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?"
        ).bind(iid, uid).run()
        msg = "✅ Feito."
    elif action == "cancel":
        await db.prepare(
            "UPDATE daily_items SET status='cancelado',cancelled_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?"
        ).bind(iid, uid).run()
        msg = "🚫 Cancelado."
    elif action.startswith("snooze"):
        mins = int(parts[3]) if len(parts) > 3 else 30
        target = _now() + timedelta(minutes=mins)
        await db.prepare(
            "UPDATE daily_items SET due_date=?,due_time=?,status='pendente',"
            "postpone_count=postpone_count+1,snoozed_until=? WHERE id=? AND user_id=?"
        ).bind(
            target.date().isoformat(),
            target.strftime("%H:%M"),
            target.strftime("%Y-%m-%d %H:%M"),
            iid,
            uid,
        ).run()
        msg = f"⏰ Adiado {mins} min."
    else:
        return False
    await _remember(db, uid, _row(item, "kind"), iid)
    if qid:
        await answer_callback(token, qid, msg)
    await send_message(
        token,
        int(chat),
        f"{msg} {_row(item,'title')}",
        reply_markup=_keyboard(app.MAIN_KB),
    )
    return True


async def _housekeeping(db):
    now = _now()
    today = now.date().isoformat()
    current = now.strftime("%H:%M")
    await db.prepare(
        "UPDATE daily_items SET status='concluido',completed_at=CURRENT_TIMESTAMP "
        "WHERE kind='compromisso' AND status='pendente' AND due_date IS NOT NULL "
        "AND (due_date<? OR (due_date=? AND due_time IS NOT NULL AND due_time<?))"
    ).bind(today, today, current).run()


def install():
    original_agenda = app.agenda_text
    original_scheduler = app.scheduled_tick
    app.morning_summary = _smart_morning

    async def agenda_clean(db, uid, target, include_overdue=False):
        base = await original_agenda(db, uid, target, include_overdue)
        if "\n🧘 Rotinas" in base:
            base = base.split("\n🧘 Rotinas", 1)[0]
        return base + await _smart_routines(db, uid, target)

    async def scheduler(db, token):
        # Itens temporais são tratados antes, em ``reliable_reminders``. Este
        # wrapper legado fica apenas com housekeeping e compatibilidade de rotina.
        await _housekeeping(db)
        now = _now()
        today = now.date()
        users = await _rows(db.prepare("SELECT id FROM users"))
        for u in users:
            uid = int(_row(u, "id"))
            routines = await _rows(
                db.prepare(
                    "SELECT id,time_hhmm,weekdays FROM routines WHERE user_id=? AND active=1"
                ).bind(uid)
            )
            for r in routines:
                q = re.search(r"(\d+)x por semana", _norm(_row(r, "weekdays") or ""))
                if q and await _weekly_done(db, int(_row(r, "id")), today) >= int(q.group(1)):
                    for t in routine_integration._times(_row(r, "time_hhmm")):
                        if t == now.strftime("%H:%M"):
                            key = f"routine:{_row(r,'id')}:{today.isoformat()}:{t}"
                            await db.prepare(
                                "INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)"
                            ).bind(uid, key).run()
        await original_scheduler(db, token)

    app.agenda_text = agenda_clean
    app.scheduled_tick = scheduler
