import re
import unicodedata

import conversational_companion as legacy

NEW_TOPIC_MARKERS = (
    "gato", "gata", "cachorro", "cachorra", "pet", "racao", "ração",
    "menina", "menino", "garota", "garoto", "ela", "ele", "pessoa",
    "prova", "faculdade", "trabalho", "estagio", "estágio", "dinheiro",
    "comprar", "mercado", "cafe", "café", "treino", "academia",
)


def _norm(text):
    value=unicodedata.normalize("NFKD",(text or "").lower())
    value="".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+"," ",value).strip()


def _is_short_continuation(n):
    exact={_norm(x) for x in legacy.CONTINUATION_MARKERS}
    return n in exact


async def handle_message(db,token,message):
    text=(message.get("text") or "").strip()
    n=_norm(text)
    if not n:
        return False

    # Corrige o bug antigo em que "é" normalizava para "e" e virava substring
    # de praticamente qualquer frase. Continuação curta só vale se a mensagem
    # inteira for uma das expressões conhecidas.
    if _is_short_continuation(n):
        mood=await legacy._last_state(db,await legacy._uid(db,int((message.get("chat") or {}).get("id"))))
        if mood in ("down","up"):
            await legacy._reply_continuation(db,token,int((message.get("chat") or {}).get("id")),await legacy._uid(db,int((message.get("chat") or {}).get("id"))),mood)
            return True
        return False

    # Tema novo não pode ser sequestrado por estado emocional antigo.
    if any(re.search(rf"\b{re.escape(_norm(marker))}\b",n) for marker in NEW_TOPIC_MARKERS):
        return False

    # Para saudações e marcadores emocionais longos, o legado ainda serve de fallback.
    if legacy._is_greeting(n) or legacy._contains_any(n,legacy.NEGATIVE_MARKERS) or legacy._contains_any(n,legacy.POSITIVE_MARKERS):
        return await legacy.handle_message(db,token,message)
    return False
