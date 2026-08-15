import re
import unicodedata

import app
import attendance_patch as attendance
from attendance_enhancement import ensure_schema
from telegram_api import send_message

MANAGE_ATTENDANCE_KB = [
    ["📊 Ver faltas", "✏️ Editar limite"],
    ["🗑️ Excluir falta", "⬅️ Voltar às matérias"],
]


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def _recent_absences(db, uid, subject_id=None, limit=20):
    sql = """
        SELECT sa.id,sa.subject_id,sa.class_date,sa.absence_count,sa.start_time,sa.end_time,s.name
        FROM subject_absences sa
        JOIN subjects s ON s.id=sa.subject_id
        WHERE sa.user_id=?
    """
    params = [uid]
    if subject_id is not None:
        sql += " AND sa.subject_id=?"
        params.append(subject_id)
    sql += " ORDER BY sa.class_date DESC, sa.start_time DESC, sa.id DESC LIMIT ?"
    params.append(limit)
    return await attendance._rows(db.prepare(sql).bind(*params))


def _absence_label(row, index=None):
    prefix = f"{index}. " if index is not None else ""
    date_value = attendance._row(row, "class_date") or ""
    date_text = f"{date_value[8:10]}/{date_value[5:7]}/{date_value[:4]}" if len(date_value) >= 10 else date_value
    count = int(attendance._row(row, "absence_count", 1) or 1)
    unit = "falta" if count == 1 else "faltas"
    return (
        f"{prefix}{attendance._row(row,'name')} — {date_text} "
        f"{attendance._row(row,'start_time')}–{attendance._row(row,'end_time')} "
        f"({count} {unit})"
    )


async def _show_delete_list(db, token, chat_id, uid, rows):
    if not rows:
        await send_message(token, chat_id, "🗑️ Não há aulas faltadas registradas para excluir. Pela primeira vez, ausência de falta é uma boa notícia.", reply_markup=_kb(MANAGE_ATTENDANCE_KB))
        return
    ids = [int(attendance._row(r, "id")) for r in rows]
    await app.set_state(db, uid, "attendance_delete_choose", {"absence_ids": ids})
    out = ["🗑️ Qual aula faltada você quer remover do histórico?"]
    for i, row in enumerate(rows, 1):
        out.append(f"• {_absence_label(row, i)}")
    out.append("\nCada item representa uma aula inteira. Se a aula durou 2h, remover esse registro desconta 2 faltas.\nManda o número; nada será apagado antes da confirmação.")
    buttons = [[str(i)] for i in range(1, min(len(rows), 10) + 1)]
    buttons.append(["❌ Cancelar ação"])
    await send_message(token, chat_id, "\n".join(out), reply_markup=_kb(buttons))


async def _resolve_subject(db, uid, query):
    return await attendance._subject_by_text(db, uid, query)


async def handle_message(db, token, message):
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    uid = await attendance._uid(db, int(chat_id))
    if uid is None:
        return False
    await ensure_schema(db)

    text = (message.get("text") or "").strip()
    n = _norm(text)
    state, payload = await app.get_state(db, uid)

    if state == "attendance_delete_choose":
        if n in {"cancelar", "cancelar acao"}:
            await app.clear_state(db, uid)
            await send_message(token, chat_id, "Certo. Nenhuma aula faltada foi mexida.", reply_markup=_kb(MANAGE_ATTENDANCE_KB))
            return True
        if not re.fullmatch(r"\d{1,2}", n):
            await send_message(token, chat_id, "Escolha pelo número da lista ou cancele.")
            return True
        idx = int(n) - 1
        ids = payload.get("absence_ids") or []
        if idx < 0 or idx >= len(ids):
            await send_message(token, chat_id, "Esse número não está na lista.")
            return True
        row = await db.prepare("""
            SELECT sa.id,sa.class_date,sa.absence_count,sa.start_time,sa.end_time,s.name
            FROM subject_absences sa JOIN subjects s ON s.id=sa.subject_id
            WHERE sa.id=? AND sa.user_id=?
        """).bind(ids[idx], uid).first()
        if not row:
            await app.clear_state(db, uid)
            await send_message(token, chat_id, "Esse registro de aula faltada já não existe mais.", reply_markup=_kb(MANAGE_ATTENDANCE_KB))
            return True
        count = int(attendance._row(row, "absence_count", 1) or 1)
        unit = "falta" if count == 1 else "faltas"
        await app.set_state(db, uid, "attendance_delete_confirm", {"absence_id": int(attendance._row(row, "id"))})
        await send_message(
            token,
            chat_id,
            "⚠️ Confirma remover esta aula faltada?\n\n"
            + _absence_label(row)
            + f"\n\nAo confirmar, esse bloco inteiro será removido e {count} {unit} deixarão de contar no total da matéria.",
            reply_markup=_kb([["✅ Confirmar exclusão"], ["❌ Cancelar ação"]]),
        )
        return True

    if state == "attendance_delete_confirm":
        if n in {"cancelar", "cancelar acao", "nao", "não"}:
            await app.clear_state(db, uid)
            await send_message(token, chat_id, "Cancelado. A aula faltada continua contabilizada.", reply_markup=_kb(MANAGE_ATTENDANCE_KB))
            return True
        if text != "✅ Confirmar exclusão" and n not in {"confirmar exclusao", "confirmar", "sim", "excluir"}:
            await send_message(token, chat_id, "Confirme a exclusão ou cancele.")
            return True
        absence_id = int(payload.get("absence_id"))
        row = await db.prepare("""
            SELECT sa.id,sa.subject_id,sa.absence_count,s.name
            FROM subject_absences sa JOIN subjects s ON s.id=sa.subject_id
            WHERE sa.id=? AND sa.user_id=?
        """).bind(absence_id, uid).first()
        if not row:
            await app.clear_state(db, uid)
            await send_message(token, chat_id, "Esse registro já tinha sido removido.", reply_markup=_kb(MANAGE_ATTENDANCE_KB))
            return True
        removed = int(attendance._row(row, "absence_count", 1) or 1)
        await db.prepare("DELETE FROM subject_absences WHERE id=? AND user_id=?").bind(absence_id, uid).run()
        total = await attendance._total_absences(db, uid, int(attendance._row(row, "subject_id")))
        unit = "falta" if removed == 1 else "faltas"
        await app.clear_state(db, uid)
        await send_message(
            token,
            chat_id,
            f"✅ Aula faltada removida de {attendance._row(row,'name')}: -{removed} {unit}. Total agora: {total}.\nProfessor perdoou, sistema também. A burocracia perdeu uma. 😌",
            reply_markup=_kb(MANAGE_ATTENDANCE_KB),
        )
        return True

    if state == "attendance_edit_limit_subject":
        if n in {"cancelar", "cancelar acao"}:
            await app.clear_state(db, uid)
            await send_message(token, chat_id, "Edição cancelada.", reply_markup=_kb(MANAGE_ATTENDANCE_KB))
            return True
        subject, _ = await _resolve_subject(db, uid, text)
        if not subject:
            await send_message(token, chat_id, "Não achei essa matéria. Escolha uma da lista.", reply_markup=_kb(await attendance._subject_keyboard(db, uid)))
            return True
        sid = int(attendance._row(subject, "id"))
        settings = await attendance._settings(db, sid)
        current = attendance._row(settings, "absence_limit") if settings else None
        await app.set_state(db, uid, "attendance_edit_limit_value", {"subject_id": sid, "subject_name": attendance._row(subject, "name")})
        current_text = str(current) if current is not None else "não informado"
        await send_message(token, chat_id, f"✏️ Limite atual de {attendance._row(subject,'name')}: {current_text}.\nQual é o novo limite? Manda só o número.", reply_markup=_kb([["❌ Cancelar ação"]]))
        return True

    if state == "attendance_edit_limit_value":
        if n in {"cancelar", "cancelar acao"}:
            await app.clear_state(db, uid)
            await send_message(token, chat_id, "Edição cancelada.", reply_markup=_kb(MANAGE_ATTENDANCE_KB))
            return True
        if not re.fullmatch(r"\d{1,3}", n):
            await send_message(token, chat_id, "Manda só o novo limite em número.")
            return True
        value = int(n)
        if value <= 0:
            await send_message(token, chat_id, "O limite precisa ser maior que zero.")
            return True
        sid = int(payload.get("subject_id"))
        old = await attendance._settings(db, sid)
        old_value = attendance._row(old, "absence_limit") if old else None
        await attendance._set_limit(db, sid, value)
        total = await attendance._total_absences(db, uid, sid)
        await app.clear_state(db, uid)
        before = str(old_value) if old_value is not None else "não informado"
        await send_message(token, chat_id, f"✅ Limite de {payload.get('subject_name')} alterado: {before} → {value}. Você está com {total}/{value} falta(s).", reply_markup=_kb(MANAGE_ATTENDANCE_KB))
        return True

    if text == "✏️ Editar limite" or n in {"editar limite", "editar limite de faltas", "alterar limite de faltas", "mudar limite de faltas"}:
        await app.set_state(db, uid, "attendance_edit_limit_subject", {})
        await send_message(token, chat_id, "✏️ De qual matéria você quer alterar o limite?", reply_markup=_kb(await attendance._subject_keyboard(db, uid)))
        return True

    if text == "🗑️ Excluir falta" or n in {"excluir falta", "remover falta", "apagar falta", "corrigir falta", "excluir aula faltada", "remover aula faltada"}:
        await _show_delete_list(db, token, chat_id, uid, await _recent_absences(db, uid))
        return True

    m = re.search(r"(?:excluir|remove|remover|apaga|apagar|tirar|tira|retirar|retira|corrigir)\s+(?:a\s+)?(?:falta|aula faltada)\s+(?:de|em)\s+(.+)$", n)
    if not m:
        m = re.search(r"(?:professor|professora).*?(?:tirou|retirou|removeu|perdoou).*?(?:falta|aula faltada)\s+(?:de|em)\s+(.+)$", n)
    if m:
        subject, _ = await _resolve_subject(db, uid, m.group(1))
        if not subject:
            await send_message(token, chat_id, "Não consegui identificar a matéria dessa aula faltada.", reply_markup=_kb(MANAGE_ATTENDANCE_KB))
            return True
        rows = await _recent_absences(db, uid, int(attendance._row(subject, "id")))
        await _show_delete_list(db, token, chat_id, uid, rows)
        return True

    m = re.search(r"(?:muda|mude|altera|altere|editar|edita)\s+(?:o\s+)?limite\s+(?:de\s+faltas\s+)?(?:de|em)\s+(.+?)\s+(?:para|pra)\s+(\d{1,3})$", n)
    if m:
        subject, _ = await _resolve_subject(db, uid, m.group(1))
        if not subject:
            await send_message(token, chat_id, "Não consegui identificar a matéria.")
            return True
        value = int(m.group(2))
        if value <= 0:
            await send_message(token, chat_id, "O limite precisa ser maior que zero.")
            return True
        sid = int(attendance._row(subject, "id"))
        old = await attendance._settings(db, sid)
        old_value = attendance._row(old, "absence_limit") if old else None
        await attendance._set_limit(db, sid, value)
        await send_message(token, chat_id, f"✅ Limite de {attendance._row(subject,'name')} alterado de {old_value if old_value is not None else 'não informado'} para {value}.", reply_markup=_kb(MANAGE_ATTENDANCE_KB))
        return True

    return False


def install():
    row = ["✏️ Editar limite", "🗑️ Excluir falta"]
    try:
        if row not in app.ACADEMIC_KB:
            app.ACADEMIC_KB.insert(-1, row)
    except Exception:
        pass
    try:
        import academic_intelligence
        if row not in academic_intelligence.ACADEMIC_KB:
            academic_intelligence.ACADEMIC_KB.insert(-1, row)
    except Exception:
        pass
