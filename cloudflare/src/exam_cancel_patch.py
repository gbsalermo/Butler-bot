import re
import unicodedata
from datetime import datetime, timedelta, timezone

import academic_intelligence
import app
import runtime_guard
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
ACADEMIC_KB = [
    ["📚 Minhas matérias", "⚙️ Gerenciar matérias"],
    ["📝 Adicionar prova", "📋 Provas"],
    ["🚫 Cancelar prova"],
    ["📥 Importar grade por PDF/texto"],
    ["🏠 Menu principal"],
]
CANCEL_KB = [["❌ Cancelar ação"]]


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9# ]+", " ", value)
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


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


async def _future_exams(db, uid):
    today = datetime.now(timezone.utc).astimezone(LOCAL_TZ).date().isoformat()
    return await _rows(db.prepare("""
        SELECT di.id,di.title,di.due_date,di.due_time,s.name subject
        FROM daily_items di
        LEFT JOIN subjects s ON di.details='exam:'||s.id
        WHERE di.user_id=? AND di.status='pendente'
          AND di.details LIKE 'exam:%' AND di.due_date>=?
        ORDER BY di.due_date,COALESCE(di.due_time,'99:99'),di.id
    """).bind(uid,today))


async def _resolve_exam(db, uid, text):
    exams = await _future_exams(db, uid)
    n = _norm(text)
    m = re.search(r"#(\d+)", text or "")
    if m:
        iid = int(m.group(1))
        matches = [e for e in exams if int(_row(e,"id")) == iid]
        return (matches[0] if len(matches) == 1 else None), exams

    cleaned = re.sub(r"^(?:butler\s+)?(?:cancela|cancelar|cancele|remove|remover|apaga|apagar)\s+(?:a\s+)?prova\s+(?:de|da|do)?\s*", "", n).strip()
    if cleaned:
        matches = []
        for e in exams:
            hay = _norm((_row(e,"subject") or "") + " " + (_row(e,"title") or ""))
            if cleaned in hay or hay in cleaned:
                matches.append(e)
            elif any(tok in hay for tok in cleaned.split() if len(tok) >= 3):
                matches.append(e)
        unique = []
        seen = set()
        for e in matches:
            iid = int(_row(e,"id"))
            if iid not in seen:
                seen.add(iid); unique.append(e)
        if len(unique) == 1:
            return unique[0], exams
    if len(exams) == 1:
        return exams[0], exams
    return None, exams


async def _cancel_exam(db, uid, exam):
    await db.prepare("UPDATE daily_items SET status='cancelado',cancelled_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=? AND details LIKE 'exam:%'").bind(int(_row(exam,"id")),uid).run()


async def handle_message(db, token, message):
    chat = (message.get("chat") or {}).get("id")
    if chat is None:
        return False
    uid = await _uid(db, int(chat))
    if not uid:
        return False
    text = (message.get("text") or "").strip()
    n = _norm(text)
    state, payload = await runtime_guard._state(db, uid)

    # Cancelamento universal durante o wizard de prova.
    if state in ("ai_exam_subject", "ai_exam_date", "ai_exam_time") and (text == "❌ Cancelar ação" or n in ("cancelar", "cancela", "cancelar acao", "para", "parar", "desiste", "desisti")):
        await runtime_guard._clear(db, uid)
        await send_message(token, int(chat), "🚫 Cadastro da prova cancelado. Nada foi salvo. A prova continua existindo na vida real, infelizmente. 😏", reply_markup=_kb(ACADEMIC_KB))
        return True

    # Fluxo de seleção iniciado pelo botão.
    if state == "ai_cancel_exam":
        if text == "❌ Cancelar ação" or n in ("cancelar", "cancela", "cancelar acao", "voltar"):
            await runtime_guard._clear(db, uid)
            await send_message(token, int(chat), "Cancelamento de prova abortado. A prova segue ameaçando normalmente. 😌", reply_markup=_kb(ACADEMIC_KB))
            return True
        exam, exams = await _resolve_exam(db, uid, text)
        if not exam:
            await send_message(token, int(chat), "Não achei uma prova única. Manda o nome da matéria ou o #ID da lista. Eu me recuso a cancelar prova no modo roleta-russa.", reply_markup=_kb(CANCEL_KB))
            return True
        await _cancel_exam(db, uid, exam)
        await runtime_guard._clear(db, uid)
        await send_message(token, int(chat), f"🚫 {_row(exam,'title')} cancelada. Um problema a menos no calendário. Não se empolgue, o semestre ainda está aí. 😏", reply_markup=_kb(ACADEMIC_KB))
        return True

    if text == "🚫 Cancelar prova":
        exams = await _future_exams(db, uid)
        if not exams:
            await send_message(token, int(chat), "Não há prova futura para cancelar. Pela primeira vez, esse botão trouxe boas notícias. 😌", reply_markup=_kb(ACADEMIC_KB))
            return True
        await runtime_guard._set_state(db, uid, "ai_cancel_exam", {})
        lines = ["Qual prova você quer cancelar?"]
        for e in exams:
            when = f"{_row(e,'due_date')[8:10]}/{_row(e,'due_date')[5:7]}" + (f" {_row(e,'due_time')}" if _row(e,'due_time') else "")
            lines.append(f"• #{_row(e,'id')} {_row(e,'subject') or _row(e,'title')} — {when}")
        await send_message(token, int(chat), "\n".join(lines), reply_markup=_kb(CANCEL_KB))
        return True

    # Linguagem natural: cancela/remove/apaga a prova de X.
    if "prova" in n and re.search(r"\b(cancela|cancelar|cancele|remove|remover|apaga|apagar)\b", n):
        exam, exams = await _resolve_exam(db, uid, text)
        if exam:
            await _cancel_exam(db, uid, exam)
            await send_message(token, int(chat), f"🚫 {_row(exam,'title')} cancelada. Pronto. Uma data a menos para olhar com desconfiança. 😌", reply_markup=_kb(ACADEMIC_KB))
            return True
        if not exams:
            await send_message(token, int(chat), "Não achei nenhuma prova futura para cancelar. Excelente problema para não ter.", reply_markup=_kb(ACADEMIC_KB))
            return True
        await runtime_guard._set_state(db, uid, "ai_cancel_exam", {})
        await send_message(token, int(chat), "Achei mais de uma possibilidade. Qual prova exatamente? Use o nome da matéria ou o #ID em `📋 Provas`.", reply_markup=_kb(CANCEL_KB))
        return True

    return False


def install():
    academic_intelligence.ACADEMIC_KB = ACADEMIC_KB
    app.ACADEMIC_KB = ACADEMIC_KB
