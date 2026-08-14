import json
from js import Object, fetch
from pyodide.ffi import to_js as _to_js


def _js(value):
    return _to_js(value, dict_converter=Object.fromEntries)


async def _post_telegram(token: str, method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    response = await fetch(
        url,
        _js({
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload, ensure_ascii=False),
        }),
    )
    text = await response.text()
    try:
        data = json.loads(text)
    except Exception:
        data = {"raw": text}
    return {"ok_http": bool(response.ok), "status": int(response.status), "telegram": data}


async def send_message(token: str, chat_id: int, text: str, reply_markup=None, parse_mode=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    if parse_mode is not None:
        payload["parse_mode"] = parse_mode
    return await _post_telegram(token, "sendMessage", payload)


async def answer_callback(token: str, callback_query_id: str):
    return await _post_telegram(token, "answerCallbackQuery", {"callback_query_id": callback_query_id})


async def set_webhook(token: str, webhook_url: str):
    # Nesta implantação o token do bot é o único secret obrigatório.
    # Telegram webhook secret pode ser adicionado futuramente sem alterar a regra de domínio.
    return await _post_telegram(token, "setWebhook", {
        "url": webhook_url,
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": True,
    })


async def delete_webhook(token: str):
    return await _post_telegram(token, "deleteWebhook", {"drop_pending_updates": True})
