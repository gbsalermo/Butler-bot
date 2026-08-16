import json
from js import Object, Uint8Array, fetch
from pyodide.ffi import to_js as _to_js


def _js(value):
    return _to_js(value, dict_converter=Object.fromEntries)


async def _post_telegram(token: str, method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    response = await fetch(url, _js({"method":"POST","headers":{"Content-Type":"application/json"},"body":json.dumps(payload, ensure_ascii=False)}))
    text = await response.text()
    try: data = json.loads(text)
    except Exception: data = {"raw": text}
    return {"ok_http": bool(response.ok), "status": int(response.status), "telegram": data}


def delivery_ok(result: dict | None) -> bool:
    """Confirma que HTTP e Telegram aceitaram a operação.

    Schedulers devem gravar notification_log somente quando isto retornar True.
    """
    if not isinstance(result, dict):
        return False
    telegram = result.get("telegram") or {}
    return bool(result.get("ok_http")) and bool(telegram.get("ok"))


def delivery_error(result: dict | None) -> str:
    if not isinstance(result, dict):
        return "resposta ausente/inválida"
    telegram = result.get("telegram") or {}
    description = telegram.get("description") or telegram.get("error_code") or telegram.get("raw")
    return f"http={result.get('status')} telegram={description or 'ok=false'}"


async def send_message(token: str, chat_id: int, text: str, reply_markup=None, parse_mode=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup is not None: payload["reply_markup"] = reply_markup
    if parse_mode is not None: payload["parse_mode"] = parse_mode
    return await _post_telegram(token, "sendMessage", payload)


async def answer_callback(token: str, callback_query_id: str, text: str | None = None):
    payload={"callback_query_id": callback_query_id}
    if text: payload["text"]=text
    return await _post_telegram(token, "answerCallbackQuery", payload)


async def get_file_bytes(token: str, file_id: str) -> bytes:
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
    return await _post_telegram(token, "setWebhook", {"url": webhook_url, "allowed_updates": ["message", "callback_query"], "drop_pending_updates": True})


async def delete_webhook(token: str):
    return await _post_telegram(token, "deleteWebhook", {"drop_pending_updates": True})
