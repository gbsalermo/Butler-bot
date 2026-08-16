import time

from llm_provider import build_provider
from settings import OWNER_CHAT_ID
from telegram_api import send_message


async def handle_message(db, token, message, env):
    chat_id = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip().lower()
    if chat_id is None or OWNER_CHAT_ID is None or int(chat_id) != int(OWNER_CHAT_ID):
        return False
    if text not in ("/debug_llm", "debug llm", "debug ia"):
        return False

    provider = build_provider(env)
    if not provider.available():
        await send_message(token, int(chat_id), "🧪 LLM debug\nBinding AI: AUSENTE\nResultado: o Butler está caindo direto na NLU/fallback.")
        return True

    started = time.time()
    try:
        raw = await provider.generate([
            {"role": "system", "content": "Responda somente a palavra OK."},
            {"role": "user", "content": "teste"},
        ], max_tokens=20, temperature=0.0)
        elapsed = round((time.time() - started) * 1000)
        model = getattr(provider, "last_model", None) or "desconhecido"
        preview = str(raw).replace("\n", " ")[:180]
        await send_message(token, int(chat_id), f"🧪 LLM debug\nBinding AI: OK\nProvider: {provider.name}\nModelo: {model}\nTempo: {elapsed} ms\nResposta: {preview}")
    except Exception as exc:
        elapsed = round((time.time() - started) * 1000)
        await send_message(token, int(chat_id), f"🧪 LLM debug\nBinding AI: OK\nInferência: FALHOU\nTempo: {elapsed} ms\nErro: {str(exc)[:700]}")
    return True
