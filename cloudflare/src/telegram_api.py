"""Fronteira entre o Butler e a Telegram Bot API no runtime Cloudflare.

Produção roda em Pyodide: ``js.fetch`` e ``pyodide.ffi.to_js`` são fornecidos
pelo runtime do Worker. Por isso este módulo não é importável em CPython puro
sem os stubs de ``cloudflare/tests/conftest.py``.

Regra importante para schedulers: receber HTTP 200 não basta. Use
``delivery_ok`` para confirmar que a própria resposta do Telegram trouxe
``ok=true`` antes de registrar uma notificação como entregue.
"""

import json
from js import Object, Uint8Array, fetch
from pyodide.ffi import to_js as _to_js

from owner_profile import is_owner


OWNER_ONLY_REPLY_BUTTONS = {"📘 Cursos"}


def _js(value):
    """Converte dict Python para objeto JS aceito por ``fetch`` no Pyodide."""
    return _to_js(value, dict_converter=Object.fromEntries)


def _button_label(button):
    if isinstance(button, str):
        return button
    if isinstance(button, dict):
        return button.get("text")
    return None


def _filter_reply_markup(chat_id: int, reply_markup):
    """Esconde recursos em standby do teclado de usuários comuns.

    A filtragem fica na fronteira do Telegram para cobrir qualquer módulo que
    reutilize ``app.MAIN_KB``. O proprietário continua vendo o teclado completo.
    """
    if reply_markup is None or is_owner(int(chat_id)) or not isinstance(reply_markup, dict):
        return reply_markup
    keyboard = reply_markup.get("keyboard")
    if not isinstance(keyboard, list):
        return reply_markup

    rows = []
    for row in keyboard:
        if not isinstance(row, list):
            rows.append(row)
            continue
        filtered = [button for button in row if _button_label(button) not in OWNER_ONLY_REPLY_BUTTONS]
        if filtered:
            rows.append(filtered)

    cleaned = dict(reply_markup)
    cleaned["keyboard"] = rows
    return cleaned


async def _post_telegram(token: str, method: str, payload: dict) -> dict:
    """Executa uma chamada POST e preserva status HTTP + payload do Telegram."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    response = await fetch(
        url,
        _js(
            {
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(payload, ensure_ascii=False),
            }
        ),
    )
    text = await response.text()
    try:
        data = json.loads(text)
    except Exception:
        # Mantém a resposta bruta para diagnóstico sem mascarar falha de parsing.
        data = {"raw": text}
    return {"ok_http": bool(response.ok), "status": int(response.status), "telegram": data}


def delivery_ok(result: dict | None) -> bool:
    """Retorna True somente quando HTTP e Telegram aceitaram a operação."""
    if not isinstance(result, dict):
        return False
    telegram = result.get("telegram") or {}
    return bool(result.get("ok_http")) and bool(telegram.get("ok"))


def delivery_error(result: dict | None) -> str:
    """Produz diagnóstico curto; nunca inclua o token da chamada."""
    if not isinstance(result, dict):
        return "resposta ausente/inválida"
    telegram = result.get("telegram") or {}
    description = telegram.get("description") or telegram.get("error_code") or telegram.get("raw")
    return f"http={result.get('status')} telegram={description or 'ok=false'}"


async def send_message(token: str, chat_id: int, text: str, reply_markup=None, parse_mode=None):
    """Envia mensagem. Chamadores críticos devem validar o retorno com delivery_ok."""
    payload = {"chat_id": chat_id, "text": text}
    filtered_markup = _filter_reply_markup(int(chat_id), reply_markup)
    if filtered_markup is not None:
        payload["reply_markup"] = filtered_markup
    if parse_mode is not None:
        payload["parse_mode"] = parse_mode
    return await _post_telegram(token, "sendMessage", payload)


async def answer_callback(token: str, callback_query_id: str, text: str | None = None):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    return await _post_telegram(token, "answerCallbackQuery", payload)


async def get_file_bytes(token: str, file_id: str) -> bytes:
    """Resolve um file_id do Telegram e baixa os bytes no runtime JS."""
    meta = await _post_telegram(token, "getFile", {"file_id": file_id})
    result = (meta.get("telegram") or {}).get("result") or {}
    path = result.get("file_path")
    if not path:
        raise ValueError("Telegram não retornou o caminho do arquivo")

    response = await fetch(f"https://api.telegram.org/file/bot{token}/{path}")
    if not response.ok:
        raise ValueError(f"Falha ao baixar arquivo: HTTP {int(response.status)}")

    buffer = await response.arrayBuffer()
    arr = Uint8Array.new(buffer)
    return bytes(arr.to_py())


async def set_webhook(token: str, webhook_url: str):
    """Configura webhook; usado por fluxos explícitos de implantação/teste."""
    return await _post_telegram(
        token,
        "setWebhook",
        {
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"],
            "drop_pending_updates": True,
        },
    )


async def delete_webhook(token: str):
    """Remove webhook e descarta updates pendentes."""
    return await _post_telegram(token, "deleteWebhook", {"drop_pending_updates": True})
