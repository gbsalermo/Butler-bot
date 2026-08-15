import re
import unicodedata
from datetime import datetime, timedelta, timezone

import app
import conversation_layer
import routine_integration
import runtime_guard
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
MAIN_KB = [["🌙 Day-off"],["➕ Adicionar","🗓️ Hoje"],["🛒 Item faltando","📚 Matérias"],["🏠 Cotidiano","🏋️ Musculação"]]
GROCERY_KB = [["➕ Adicionar item","📋 Ver itens faltando"],["🏠 Menu principal"]]
ROUTINE_KB = [["➕ Adicionar rotina", "📋 Minhas rotinas"],["✅ Marcar rotina feita", "🗑️ Remover rotina"],["⬅️ Voltar ao cotidiano"]]


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9 ]+", " ", value).strip()


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


def _inline(rows):
    return {"inline_keyboard": [[{"text": label, "callback_data": data} for label, data in row] for row in rows]}


def _now():
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


async def _save_checkpoint_smart(db, uid, routine, target_time=None):
    """Marca um checkpoint sem exigir que a resposta ocorra exatamente no minuto do lembrete.

    Sem target explícito, escolhe o checkpoint vencido mais recente ainda não confirmado.
    Isso permite, por exemplo, confirmar às 14:20 o checkpoint das 14:00.
    """
    routine_id = int(_row(routine, "id"))
    scheduled = routine_integration._times(_row(routine, "time_hhmm"))
    today = _now().date()
    done = await routine_integration._status(db, routine_id, today, scheduled)

    if scheduled:
        if target_time and target_time in scheduled:
            done.add(target_time)
        else:
            current = _now().strftime("%H:%M")
            eligible = [t for t in scheduled if t <= current and t not in done]
            if eligible:
                done.add(eligible[-1])
            else:
                pending = [t for t in scheduled if t not in done]
                if pending:
                    # Se ainda não venceu nenhum, mantém o comportamento previsível do fluxo manual.
                    done.add(pending[0])
    else:
        done.add("feito")

    complete = (not scheduled) or all(t in done for t in scheduled)
    import json
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


async def _item_reminders_10_5(db, token):
    now = _now(); today = now.date(); current = now.strftime("%H:%M")
    users = await _rows(db.prepare("SELECT u.id,u.telegram_chat_id,a.day_off FROM users u JOIN assistant_state a ON a.user_id=u.id"))
    for user in users:
        if int(_row(user, "day_off", 0)):
            continue
        uid = int(_row(user, "id")); chat = int(_row(user, "telegram_chat_id"))
        items = await _rows(db.prepare("SELECT id,kind,title,details,due_time FROM daily_items WHERE user_id=? AND status='pendente' AND due_date=? AND due_time IS NOT NULL").bind(uid, today.isoformat()))
        for item in items:
            iid = int(_row(item, "id")); kind = _row(item, "kind"); simple = _row(item, "details") == "simple_reminder"
            h, m = map(int, _row(item, "due_time").split(":"))
            due = datetime.combine(today, datetime.min.time()).replace(hour=h, minute=m)

            # Lembrete simples continua no horário exato. Tarefa -10, compromisso -5.
            advance = 0 if simple else (10 if kind == "tarefa" else 5)
            desired = due - timedelta(minutes=advance)

            # Bloqueia as regras antigas do scheduler base: tarefa no horário e compromisso -10.
            legacy_target = due if kind == "tarefa" else due - timedelta(minutes=10)
            if legacy_target.strftime("%H:%M") == current:
                legacy_key = f"item:{iid}:{today}:{legacy_target.strftime('%H:%M')}"
                await db.prepare("INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)").bind(uid, legacy_key).run()

            if desired.strftime("%H:%M") != current:
                continue
            key = f"item:new:{iid}:{today}:{desired.strftime('%H:%M')}"
            exists = await db.prepare("SELECT id FROM notification_log WHERE user_id=? AND notification_key=?").bind(uid, key).first()
            if exists:
                continue

            if simple:
                markup = _inline([[("👌 Entendi", f"item:done:{iid}")]])
                text = f"🔔 {_row(item,'title')} — {_row(item,'due_time')}. Só um aviso."
            elif kind == "tarefa":
                markup = _inline([[('✅ Feito', f'item:done:{iid}'), ('⏰ +30 min', f'item:snooze:{iid}:30')], [('🚫 Cancelar', f'item:cancel:{iid}')]])
                text = f"✅ {_row(item,'title')} às {_row(item,'due_time')}. Faltam 10 minutos. Dá tempo de parar de fingir que esqueceu. 😌"
            else:
                markup = _inline([[('👌 Ciente', f'item:done:{iid}'), ('⏰ +30 min', f'item:snooze:{iid}:30')]])
                text = f"📅 {_row(item,'title')} às {_row(item,'due_time')}. Faltam 5 minutos. Se organize."

            await conversation_layer._remember(db, uid, "lembrete" if simple else kind, iid)
            await send_message(token, chat, text, reply_markup=markup)
            await db.prepare("INSERT INTO notification_log(user_id,notification_key) VALUES(?,?)").bind(uid, key).run()

            # Já bloqueia também o disparo legado futuro da mesma obrigação.
            future_legacy_key = f"item:{iid}:{today}:{legacy_target.strftime('%H:%M')}"
            await db.prepare("INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)").bind(uid, future_legacy_key).run()
            if simple:
                await db.prepare("UPDATE daily_items SET status='concluido',completed_at=CURRENT_TIMESTAMP WHERE id=?").bind(iid).run()


async def handle_message(db, token, message):
    chat = message.get("chat") or {}; chat_id = chat.get("id")
    if chat_id is None:
        return False
    uid = await _uid(db, int(chat_id))
    if not uid:
        return False
    text = (message.get("text") or "").strip(); n = _norm(text)

    # Mercado informal: "acabou o café", "cabô café", "não tem mais açúcar", etc.
    grocery_patterns = [
        r"^(?:acabou|acabo|cabo|cabou)\s+(?:o|a|os|as)?\s*(.+)$",
        r"^(?:nao tem mais|nao temos mais|ta sem|to sem|estou sem)\s+(.+)$",
        r"^(?:precisa comprar|precisamos comprar)\s+(.+)$",
    ]
    for pattern in grocery_patterns:
        match = re.match(pattern, n)
        if match:
            raw_items = match.group(1).strip()
            items = [x.strip() for x in re.split(r",|\s+e\s+", raw_items) if x.strip()]
            if items:
                for item in items:
                    await db.prepare("INSERT INTO grocery_items(user_id,name,missing) VALUES(?,?,1) ON CONFLICT(user_id,name) DO UPDATE SET missing=1,updated_at=CURRENT_TIMESTAMP").bind(uid, item).run()
                await send_message(token, int(chat_id), "🛒 Anotado: " + ", ".join(items) + ". Acabou em casa, virou problema da lista. 😌", reply_markup=_kb(GROCERY_KB))
                return True

    # Confirmação natural de rotina fora do lembrete: "bebi água", "fiz inglês", "cumpri a rotina de água".
    if re.match(r"^(?:ja\s+)?(?:bebi|fiz|cumpri|completei|terminei)\b", n):
        routines = await _rows(db.prepare("SELECT id,name,category,time_hhmm,weekdays FROM routines WHERE user_id=? AND active=1").bind(uid))
        tail = re.sub(r"^(?:ja\s+)?(?:bebi|fiz|cumpri|completei|terminei)\s+", "", n).strip()
        matches = []
        for routine in routines:
            hay = _norm((_row(routine, "name") or "") + " " + (_row(routine, "category") or ""))
            if tail and (tail in hay or any(tok and tok in hay for tok in tail.split() if len(tok) >= 3)):
                matches.append(routine)
        if len(matches) == 1:
            routine = matches[0]
            done, scheduled, complete = await _save_checkpoint_smart(db, uid, routine, None)
            if complete:
                msg = f"✅ {_row(routine,'name')} concluída hoje. Meta contabilizada. 🔥"
            else:
                msg = f"✅ {_row(routine,'name')}: {len(done)}/{len(scheduled)} checkpoint(s). Pode confirmar depois do horário também; eu não exijo pontualidade de relógio suíço."
            await send_message(token, int(chat_id), msg, reply_markup=_kb(ROUTINE_KB))
            return True

    return False


def install():
    # Troca a decisão de checkpoint manual usada pelas outras camadas.
    routine_integration._save_checkpoint = _save_checkpoint_smart

    # O scheduler da conversation_layer consulta esse símbolo global a cada tick.
    # Substituindo aqui, mantemos o restante do scheduler e só trocamos a política dos itens.
    conversation_layer._pre_send_item_reminders = _item_reminders_10_5
