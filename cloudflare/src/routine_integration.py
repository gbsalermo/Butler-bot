import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone

import app
import runtime_guard
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
DAY_NAMES = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
ROUTINE_KB = [["➕ Adicionar rotina", "📋 Minhas rotinas"], ["✅ Marcar rotina feita", "🗑️ Remover rotina"], ["⬅️ Voltar ao cotidiano"]]
CANCEL_KB = [["❌ Cancelar ação"]]


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


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


def _times(value):
    found = re.findall(r"\b(?:[01]\d|2[0-3]):[0-5]\d\b", value or "")
    return list(dict.fromkeys(found))


def _parse_times(text):
    normalized = _norm(text)
    times = []
    for h, m in re.findall(r"\b([01]?\d|2[0-3])(?::|h)([0-5]\d)?\b", normalized):
        times.append(f"{int(h):02d}:{int(m or 0):02d}")
    return list(dict.fromkeys(times))


def _applies(weekdays, target):
    value = _norm(weekdays or "todos os dias")
    if not value or "todos os dias" in value or value in ("todos", "diario", "diaria"):
        return True
    today = _norm(DAY_NAMES[target.weekday()])
    return today in value


def _decode_status(value, scheduled):
    if value == "feito":
        return set(scheduled)
    try:
        payload = json.loads(value or "{}")
        return set(payload.get("done") or [])
    except Exception:
        return set()


async def _status(db, routine_id, day, scheduled):
    row = await db.prepare("SELECT status FROM routine_logs WHERE routine_id=? AND log_date=?").bind(routine_id, day.isoformat()).first()
    return _decode_status(_row(row, "status"), scheduled)


async def _save_checkpoint(db, uid, routine, target_time=None):
    routine_id = int(_row(routine, "id"))
    scheduled = _times(_row(routine, "time_hhmm"))
    today = datetime.now(timezone.utc).astimezone(LOCAL_TZ).date()
    done = await _status(db, routine_id, today, scheduled)

    if scheduled:
        if target_time and target_time in scheduled:
            done.add(target_time)
        elif target_time is None:
            pending = [t for t in scheduled if t not in done]
            if pending:
                done.add(pending[0])
    else:
        done.add("feito")

    complete = (not scheduled) or all(t in done for t in scheduled)
    status = "feito" if complete else json.dumps({"done": sorted(done), "total": scheduled}, ensure_ascii=False)
    await db.prepare("INSERT INTO routine_logs(routine_id,log_date,status) VALUES(?,?,?) ON CONFLICT(routine_id,log_date) DO UPDATE SET status=excluded.status").bind(routine_id, today.isoformat(), status).run()

    if complete:
        category = _row(routine, "category")
        goal = await db.prepare("SELECT id FROM goals WHERE user_id=? AND lower(name)=lower(?) LIMIT 1").bind(uid, category).first()
        if goal:
            note = f"rotina:{routine_id}"
            gid = int(_row(goal, "id"))
            await db.prepare("INSERT INTO goal_progress(goal_id,amount,log_date,note) SELECT ?,1,?,? WHERE NOT EXISTS(SELECT 1 FROM goal_progress WHERE goal_id=? AND log_date=? AND note=?)").bind(gid, today.isoformat(), note, gid, today.isoformat(), note).run()
    return done, scheduled, complete


async def _agenda_routines(db, uid, target):
    routines = await _rows(db.prepare("SELECT id,name,category,time_hhmm,weekdays FROM routines WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
    applicable = [r for r in routines if _applies(_row(r, "weekdays"), target)]
    if not applicable:
        return ""
    out = ["\n🧘 Rotinas"]
    for routine in applicable:
        scheduled = _times(_row(routine, "time_hhmm"))
        done = await _status(db, int(_row(routine, "id")), target, scheduled)
        if scheduled:
            checkpoints = "  ".join(("✅" if t in done else "⏳") + f" {t}" for t in scheduled)
            progress = sum(1 for t in scheduled if t in done)
            out.append(f"• {_row(routine,'name')}\n  {checkpoints}\n  Progresso: {progress}/{len(scheduled)}")
        else:
            complete = "feito" in done
            out.append(f"• {'✅' if complete else '⏳'} {_row(routine,'name')} — sem horário")
    return "\n".join(out)


async def _dispatch_one_routine(db, token, uid, chat, routine, today, now):
    """Processa uma rotina sem permitir que falhas contaminem outras rotinas/usuários."""
    if not _applies(_row(routine, "weekdays"), today):
        return

    rid = int(_row(routine, "id"))
    scheduled = _times(_row(routine, "time_hhmm"))
    done = await _status(db, rid, today, scheduled)

    due_unnotified = []
    for target_time in scheduled:
        if target_time in done:
            continue
        try:
            h, m = map(int, target_time.split(":"))
        except Exception:
            continue
        desired = datetime.combine(today, datetime.min.time()).replace(hour=h, minute=m, tzinfo=LOCAL_TZ)
        if now < desired:
            continue
        key = f"routine:{rid}:{today.isoformat()}:{target_time}"
        existing = await db.prepare(
            "SELECT id FROM notification_log WHERE user_id=? AND notification_key=?"
        ).bind(uid, key).first()
        if not existing:
            due_unnotified.append((desired, target_time, key))

    if not due_unnotified:
        return

    due_unnotified.sort(key=lambda x: x[0])
    latest_desired, latest_time, latest_key = due_unnotified[-1]

    # Não registramos checkpoints antigos como "enviados" antes de uma entrega real.
    # Eles simplesmente deixam de ser candidatos enquanto houver um checkpoint mais recente,
    # evitando falsos positivos no diagnóstico e preservando o histórico real.
    late_minutes = max(0, int((now - latest_desired).total_seconds() // 60))
    payload = {"routine_id": rid, "time": latest_time, "name": _row(routine, "name")}
    await runtime_guard._set_state(db, uid, "guard_routine_checkpoint", payload)
    timing = (
        f"⏰ Checkpoint {latest_time} — aviso atrasou {late_minutes} min."
        if late_minutes > 2 else f"⏰ Checkpoint {latest_time}."
    )

    # scheduled_delivery_guard substitui send_message por envio confirmado.
    # Se falhar, a exceção fica restrita a esta rotina e o notification_log não é gravado.
    await send_message(
        token,
        chat,
        f"🧘 Rotina — {_row(routine,'name')}\n{timing}\n\nQuando cumprir, pode responder só `certo`, `feito` ou usar o botão.",
        reply_markup=_kb([[f"✅ Feito — #{rid} {latest_time}"], ["🏠 Menu principal"]]),
    )
    await db.prepare(
        "INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)"
    ).bind(uid, latest_key).run()


async def _routine_reminders(db, token):
    """Scheduler autoritativo de rotinas, resiliente por usuário e por rotina."""
    now = datetime.now(timezone.utc).astimezone(LOCAL_TZ)
    today = now.date()
    users = await _rows(db.prepare(
        "SELECT u.id,u.telegram_chat_id,COALESCE(a.day_off,0) day_off FROM users u "
        "LEFT JOIN assistant_state a ON a.user_id=u.id"
    ))

    for user in users:
        if int(_row(user, "day_off", 0)):
            continue
        try:
            uid = int(_row(user, "id"))
            chat = int(_row(user, "telegram_chat_id"))
        except Exception as exc:
            print(f"[routine-scheduler] invalid-user error={type(exc).__name__}:{exc}")
            continue

        routines = await _rows(db.prepare(
            "SELECT id,name,category,time_hhmm,weekdays FROM routines "
            "WHERE user_id=? AND active=1 AND time_hhmm IS NOT NULL ORDER BY id"
        ).bind(uid))

        for routine in routines:
            rid = _row(routine, "id")
            try:
                await _dispatch_one_routine(db, token, uid, chat, routine, today, now)
            except Exception as exc:
                print(
                    f"[routine-scheduler] error user_id={uid} routine_id={rid} "
                    f"type={type(exc).__name__} message={str(exc)[:300]}"
                )
                continue


def install_routine_integration():
    original_agenda = app.agenda_text
    original_pre_dispatch = runtime_guard.handle_pre_dispatch

    async def agenda_with_routines(db, uid, target, include_overdue=False):
        base = await original_agenda(db, uid, target, include_overdue)
        extra = await _agenda_routines(db, uid, target)
        return base + extra

    async def pre_dispatch_with_routines(db, token, message):
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        text = (message.get("text") or "").strip()
        if chat_id is not None:
            uid = await runtime_guard._uid(db, int(chat_id))
            if uid:
                state, payload = await runtime_guard._state(db, uid)

                if state == "guard_routine_when":
                    times = _parse_times(text)
                    n = _norm(text)
                    days = [d for d in DAY_NAMES if _norm(d) in n]
                    weekdays = ",".join(days) if days else "todos os dias"
                    time_value = ",".join(times) if times else None
                    await db.prepare("INSERT INTO routines(user_id,name,category,time_hhmm,weekdays,active) VALUES(?,?,?,?,?,1)").bind(uid, payload.get("name"), payload.get("category"), time_value, weekdays).run()
                    await runtime_guard._clear(db, uid)
                    when = " / ".join(times) if times else "sem horário"
                    await send_message(token, int(chat_id), f"🧘 Rotina `{payload.get('name')}` criada.\nHorários: {when}\nDias: {weekdays}.\nMeta ligada: {payload.get('category')}.\n\nAgora ela entra na agenda nos dias ativos e só conta como concluída quando todos os checkpoints do dia forem confirmados.", reply_markup=_kb(ROUTINE_KB))
                    return True

                if state == "guard_routine_checkpoint" and _norm(text) in ("certo", "ok", "feito", "pronto", "concluido", "concluida"):
                    routine = await db.prepare("SELECT id,name,category,time_hhmm,weekdays FROM routines WHERE id=? AND user_id=? AND active=1").bind(payload.get("routine_id"), uid).first()
                    if routine:
                        done, scheduled, complete = await _save_checkpoint(db, uid, routine, payload.get("time"))
                        await runtime_guard._clear(db, uid)
                        if complete:
                            msg = f"✅ {_row(routine,'name')} concluída hoje. {len(scheduled) if scheduled else 1}/{len(scheduled) if scheduled else 1}. A meta também recebeu o crédito. 🔥"
                        else:
                            msg = f"✅ Checkpoint {payload.get('time')} de {_row(routine,'name')} registrado. {len(done)}/{len(scheduled)}. Ainda não terminou o expediente dessa rotina. 😌"
                        await send_message(token, int(chat_id), msg, reply_markup=_kb(ROUTINE_KB))
                        return True

                m = re.match(r"^✅\s*Feito\s*[—-]\s*#(\d+)\s+(\d{2}:\d{2})$", text, re.I)
                if m:
                    routine = await db.prepare("SELECT id,name,category,time_hhmm,weekdays FROM routines WHERE id=? AND user_id=? AND active=1").bind(int(m.group(1)), uid).first()
                    if routine:
                        done, scheduled, complete = await _save_checkpoint(db, uid, routine, m.group(2))
                        await runtime_guard._clear(db, uid)
                        msg = f"✅ {_row(routine,'name')}: {len(done)}/{len(scheduled) if scheduled else 1}" + (" — rotina concluída hoje. 🔥" if complete else ".")
                        await send_message(token, int(chat_id), msg, reply_markup=_kb(ROUTINE_KB))
                        return True

                if state == "guard_routine_done":
                    candidate = None
                    m = re.search(r"#?(\d+)", text)
                    if m:
                        candidate = await db.prepare("SELECT id,name,category,time_hhmm,weekdays FROM routines WHERE id=? AND user_id=? AND active=1").bind(int(m.group(1)), uid).first()
                    if candidate:
                        done, scheduled, complete = await _save_checkpoint(db, uid, candidate, None)
                        await runtime_guard._clear(db, uid)
                        msg = f"✅ {_row(candidate,'name')}: {len(done)}/{len(scheduled) if scheduled else 1}" + (" — concluída hoje e contabilizada na meta. 🔥" if complete else ". Próximo checkpoint continua pendente.")
                        await send_message(token, int(chat_id), msg, reply_markup=_kb(ROUTINE_KB))
                        return True

        return await original_pre_dispatch(db, token, message)

    app.agenda_text = agenda_with_routines
    # Importante: não embrulhar app.scheduled_tick. O entry.py já chama
    # _routine_reminders diretamente como scheduler autoritativo.
    runtime_guard.handle_pre_dispatch = pre_dispatch_with_routines
