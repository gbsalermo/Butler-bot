"""UX operacional da Etapa 5 — Caixa de entrada / captura rápida.

A Inbox guarda texto sem classificar. Transformar em tarefa ou compromisso exige
uma escolha explícita e usa o gateway ``core_actions`` para não duplicar regras.
"""
from __future__ import annotations

import re

import app
import core_actions
import inbox_domain
from telegram_api import send_message

_STATE_UNSET = object()

INBOX_KB = [
    ["➕ Capturar", "📋 Pendentes"],
    ["🗄️ Arquivados"],
    ["⬅️ Minha vida"],
]
PROCESS_KB = [
    ["✅ Virar tarefa", "📅 Virar compromisso"],
    ["⬅️ Voltar ao item"],
]
ITEM_PENDING_KB = [
    ["🧭 Processar", "🗄️ Arquivar"],
    ["⬅️ Inbox"],
]
ITEM_ARCHIVED_KB = [
    ["♻️ Reabrir"],
    ["⬅️ Inbox"],
]
CANCEL_KB = [["❌ Cancelar ação"]]
DATE_KB = [["📌 Sem data"], ["❌ Cancelar ação"]]
TIME_KB = [["⏭️ Sem horário"], ["❌ Cancelar ação"]]

DIRECT_TEXTS = {
    "📥 Inbox",
    "📥 Caixa de entrada",
    "📥 Capturar na Inbox",
    "➕ Capturar",
    "📋 Pendentes",
    "🗄️ Arquivados",
    "⬅️ Inbox",
    "⬅️ Voltar ao item",
    "🧭 Processar",
    "🗄️ Arquivar",
    "♻️ Reabrir",
    "✅ Virar tarefa",
    "📅 Virar compromisso",
}
ITEM_BUTTON_RE = re.compile(r"^📥\s+#(\d+)\b")
ARCHIVED_BUTTON_RE = re.compile(r"^🗄️\s+#(\d+)\b")


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


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


def _short(text, size=38):
    text = " ".join(str(text or "").split())
    return text if len(text) <= size else text[: size - 3].rstrip() + "..."


def _button(item, archived=False):
    icon = "🗄️" if archived else "📥"
    return f"{icon} #{int(_row(item,'id'))} {_short(_row(item,'content'))}"


def _item_id(text):
    value = (text or "").replace("\ufe0f", "").replace("\u00a0", " ").strip()
    for rx in (ITEM_BUTTON_RE, ARCHIVED_BUTTON_RE):
        match = rx.match(value)
        if match:
            return int(match.group(1))
    return None


def _natural_capture(text):
    """Retorna (é pedido de Inbox, conteúdo extraído ou vazio).

    O gate é propositalmente estreito: a palavra solta ``anota`` não é suficiente,
    evitando sequestrar tarefas, lembretes ou outros domínios.
    """
    raw = " ".join((text or "").strip().split())
    if not raw:
        return False, None
    n = app.norm(raw)
    explicit_inbox = " inbox" in f" {n}" or "caixa de entrada" in n
    organize_later = "organizar depois" in n
    capture_verb = n.startswith(("joga ", "manda ", "bota ", "poe ", "anota ", "guarda ", "salva "))
    if not capture_verb or not (explicit_inbox or organize_later):
        return False, None

    if explicit_inbox:
        if ":" in raw:
            return True, raw.split(":", 1)[1].strip()
        # Sem dois pontos, remove somente uma instrução explícita no início.
        content = re.sub(
            r"^(?:joga|manda|bota|p[oõ]e|anota|guarda|salva)\s+(?:isso\s+)?(?:na|pra|para\s+a)?\s*(?:inbox|caixa\s+de\s+entrada)\s*",
            "",
            raw,
            flags=re.IGNORECASE,
        ).strip(" :-")
        return True, content

    # Ex.: "anota revisar autenticação pra eu organizar depois"
    content = re.sub(r"^(?:anota|guarda|salva)\s+", "", raw, flags=re.IGNORECASE)
    content = re.sub(
        r"\s+(?:pra|para)(?:\s+eu)?\s+organizar\s+depois\s*$",
        "",
        content,
        flags=re.IGNORECASE,
    ).strip(" :-")
    if app.norm(content) in {"isso", "isto", "aquilo"}:
        content = ""
    return True, content


async def _send(token, chat_id, text, rows=None):
    await send_message(token, int(chat_id), text, reply_markup=_kb(rows) if rows else None)


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(int(chat_id)).first()
    return int(_row(row, "id")) if row else None


async def _show_menu(token, chat_id):
    await _send(
        token,
        chat_id,
        "📥 Caixa de entrada\n\nJoga aqui o que você quer guardar agora e decidir depois. Nada vira tarefa ou compromisso sozinho.",
        INBOX_KB,
    )


async def _show_list(db, token, chat_id, uid, *, archived=False):
    status = "archived" if archived else "pending"
    items = await inbox_domain.list_items(db, uid, status=status)
    if not items:
        msg = "🗄️ Nenhum item arquivado." if archived else "📥 Sua caixa de entrada está vazia."
        await _send(token, chat_id, msg, INBOX_KB)
        return True
    title = "🗄️ Arquivados" if archived else "📋 Pendentes — mais antigos primeiro"
    lines = [title]
    rows = []
    for item in items:
        lines.append(f"#{_row(item,'id')} • {_short(_row(item,'content'), 72)}")
        rows.append([_button(item, archived=archived)])
    rows.append(["⬅️ Inbox"])
    await _send(token, chat_id, "\n".join(lines), rows)
    return True


async def _show_item(db, token, chat_id, uid, item_id):
    item = await inbox_domain.get_item(db, uid, item_id)
    if not item:
        await _send(token, chat_id, "Não encontrei esse item na sua caixa de entrada.", INBOX_KB)
        return True
    status = _row(item, "status")
    labels = {"pending": "⏳ Pendente", "archived": "🗄️ Arquivado", "converted": "✅ Convertido"}
    text = f"📥 #{item_id}\n{_row(item,'content')}\n\nStatus: {labels.get(status,status)}"
    if status == "converted":
        text += f"\nDestino: {_row(item,'converted_domain')} #{_row(item,'converted_target_id')}"
        rows = [["⬅️ Inbox"]]
    elif status == "archived":
        rows = ITEM_ARCHIVED_KB
    else:
        rows = ITEM_PENDING_KB
    await app.set_state(db, uid, "inbox_view", {"inbox_id": int(item_id)})
    await _send(token, chat_id, text, rows)
    return True


async def _finish_daily_conversion(db, token, chat_id, uid, payload, *, due_time=None):
    inbox_id = int(payload["inbox_id"])
    item = await inbox_domain.get_item(db, uid, inbox_id)
    if not item or _row(item, "status") != "pending":
        await app.clear_state(db, uid)
        await _send(token, chat_id, "Esse item não está mais pendente na Inbox.", INBOX_KB)
        return True
    kind = payload["kind"]
    target_id = await core_actions.create_daily_item_from_inbox(
        db,
        uid,
        inbox_id,
        kind,
        _row(item, "content"),
        payload.get("due_date"),
        due_time,
    )
    if not target_id:
        await _send(token, chat_id, "Não consegui converter esse item com segurança. Nada foi duplicado.", INBOX_KB)
        return True
    await inbox_domain.mark_converted(db, uid, inbox_id, kind, target_id)
    await app.clear_state(db, uid)
    label = "tarefa" if kind == "tarefa" else "compromisso"
    await _send(
        token,
        chat_id,
        f"✅ Inbox #{inbox_id} virou {label} #{target_id}. Ele saiu dos pendentes; não ficou uma cópia para você resolver duas vezes.",
        INBOX_KB,
    )
    return True


async def _handle_state(db, token, chat_id, uid, text, state, payload):
    if not state or not str(state).startswith("inbox_"):
        return False

    if text in {"❌ Cancelar ação", "/cancelar"}:
        item_id = payload.get("inbox_id")
        await app.clear_state(db, uid)
        if item_id:
            await _send(token, chat_id, "Operação cancelada. O item continua pendente.", None)
            return await _show_item(db, token, chat_id, uid, int(item_id))
        await _send(token, chat_id, "Captura cancelada.", INBOX_KB)
        return True

    if state == "inbox_capture":
        try:
            item_id = await inbox_domain.capture(db, uid, text, source="button")
        except ValueError as exc:
            await _send(token, chat_id, f"Não salvei: {exc}.", CANCEL_KB)
            return True
        await app.clear_state(db, uid)
        await _send(token, chat_id, f"📥 Guardado na Inbox como #{item_id}. Você decide o que isso vira quando quiser.", INBOX_KB)
        return True

    if state == "inbox_view":
        item_id = int(payload["inbox_id"])
        if text == "🧭 Processar":
            item = await inbox_domain.get_item(db, uid, item_id)
            if not item or _row(item, "status") != "pending":
                return await _show_item(db, token, chat_id, uid, item_id)
            await app.set_state(db, uid, "inbox_process", {"inbox_id": item_id})
            await _send(
                token,
                chat_id,
                "O que esse item virou? Eu só converto depois da sua escolha.",
                PROCESS_KB,
            )
            return True
        if text == "🗄️ Arquivar":
            await inbox_domain.archive(db, uid, item_id)
            await app.clear_state(db, uid)
            await _send(token, chat_id, "🗄️ Arquivado. Não criei tarefa, compromisso nem qualquer outra coisa.", INBOX_KB)
            return True
        if text == "♻️ Reabrir":
            await inbox_domain.reopen(db, uid, item_id)
            await _send(token, chat_id, "♻️ Voltou para os pendentes.", None)
            return await _show_item(db, token, chat_id, uid, item_id)
        if text == "⬅️ Inbox":
            await app.clear_state(db, uid)
            await _show_menu(token, chat_id)
            return True

    if state == "inbox_process":
        item_id = int(payload["inbox_id"])
        if text == "⬅️ Voltar ao item":
            return await _show_item(db, token, chat_id, uid, item_id)
        if text not in {"✅ Virar tarefa", "📅 Virar compromisso"}:
            await _send(token, chat_id, "Escolha Tarefa ou Compromisso, ou volte ao item.", PROCESS_KB)
            return True
        kind = "tarefa" if text == "✅ Virar tarefa" else "compromisso"
        await app.set_state(db, uid, f"inbox_convert_{kind}_date", {"inbox_id": item_id, "kind": kind})
        rows = DATE_KB if kind == "tarefa" else CANCEL_KB
        hint = "Quando? `hoje`, `amanhã`, `DD/MM` ou Sem data." if kind == "tarefa" else "Qual a data do compromisso? Use `hoje`, `amanhã` ou `DD/MM`."
        await _send(token, chat_id, hint, rows)
        return True

    if state in {"inbox_convert_tarefa_date", "inbox_convert_compromisso_date"}:
        kind = payload["kind"]
        n = app.norm(text)
        if kind == "tarefa" and (text == "📌 Sem data" or n == "sem data"):
            payload["due_date"] = None
            return await _finish_daily_conversion(db, token, chat_id, uid, payload, due_time=None)
        due = app.parse_date(text, app.now_local().date())
        if not due:
            await _send(token, chat_id, "Não reconheci a data. Use `hoje`, `amanhã` ou `DD/MM`.", DATE_KB if kind == "tarefa" else CANCEL_KB)
            return True
        ok, msg = app.validate_future(due, None, app.now_local())
        if not ok:
            await _send(token, chat_id, msg, DATE_KB if kind == "tarefa" else CANCEL_KB)
            return True
        payload["due_date"] = due.isoformat()
        await app.set_state(db, uid, f"inbox_convert_{kind}_time", payload)
        await _send(token, chat_id, "Horário? Ex.: `15h`, `15:30`, ou Sem horário.", TIME_KB)
        return True

    if state in {"inbox_convert_tarefa_time", "inbox_convert_compromisso_time"}:
        n = app.norm(text)
        tm = None if text == "⏭️ Sem horário" or n in {"sem horario", "sem hora"} else app.parse_time(text)
        if tm is None and not (text == "⏭️ Sem horário" or n in {"sem horario", "sem hora"}):
            await _send(token, chat_id, "Não reconheci o horário. Use `15h`, `15:30` ou Sem horário.", TIME_KB)
            return True
        due = app.parse_date(payload["due_date"], app.now_local().date()) if payload.get("due_date") else None
        if due:
            ok, msg = app.validate_future(due, tm, app.now_local())
            if not ok:
                await _send(token, chat_id, msg, TIME_KB)
                return True
        return await _finish_daily_conversion(db, token, chat_id, uid, payload, due_time=tm)

    await _send(token, chat_id, "Não reconheci essa opção da Inbox. Use os botões da tela.", INBOX_KB)
    return True


async def handle_message(db, token, message, *, uid=None, state=_STATE_UNSET, payload=None):
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if not text or chat_id is None:
        return False
    chat_id = int(chat_id)

    natural, natural_content = _natural_capture(text)
    direct = text in DIRECT_TEXTS or _item_id(text) is not None or natural

    if state is not _STATE_UNSET:
        inbox_state = bool(state and str(state).startswith("inbox_"))
        if not inbox_state and not direct:
            return False

    if uid is None:
        uid = await _uid(db, chat_id)
    if uid is None:
        return False

    if state is _STATE_UNSET:
        state, payload = await app.get_state(db, uid)
    payload = payload or {}

    if await _handle_state(db, token, chat_id, uid, text, state, payload):
        return True

    if natural:
        if not natural_content:
            await app.set_state(db, uid, "inbox_capture", {})
            await _send(token, chat_id, "O que quer guardar para organizar depois?", CANCEL_KB)
            return True
        try:
            item_id = await inbox_domain.capture(db, uid, natural_content, source="text")
        except ValueError as exc:
            await _send(token, chat_id, f"Não salvei: {exc}.", INBOX_KB)
            return True
        await _send(token, chat_id, f"📥 Guardado na Inbox como #{item_id}. Sem classificar por enquanto.", INBOX_KB)
        return True

    if text in {"📥 Inbox", "📥 Caixa de entrada", "⬅️ Inbox"}:
        await app.clear_state(db, uid)
        await _show_menu(token, chat_id)
        return True
    if text in {"📥 Capturar na Inbox", "➕ Capturar"}:
        await app.set_state(db, uid, "inbox_capture", {})
        await _send(token, chat_id, "O que quer guardar na Caixa de entrada?", CANCEL_KB)
        return True
    if text == "📋 Pendentes":
        await app.clear_state(db, uid)
        return await _show_list(db, token, chat_id, uid, archived=False)
    if text == "🗄️ Arquivados":
        await app.clear_state(db, uid)
        return await _show_list(db, token, chat_id, uid, archived=True)

    item_id = _item_id(text)
    if item_id is not None:
        return await _show_item(db, token, chat_id, uid, item_id)

    return False
