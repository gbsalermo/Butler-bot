import conversational_companion as legacy


def _exact_continuation(text):
    n = legacy._norm(text)
    exact = {legacy._norm(x) for x in legacy.CONTINUATION_MARKERS}
    return n in exact


def is_priority_farewell(text):
    """Despedidas explícitas podem escapar de qualquer wizard pendente."""
    return legacy._is_farewell(legacy._norm(text or ""))


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    if not text:
        return False
    n = legacy._norm(text)

    if legacy._is_farewell(n):
        return await legacy.handle_message(db, token, message)

    # Saudações e estados explícitos continuam usando o comportamento existente.
    if legacy._is_greeting(n):
        return await legacy.handle_message(db, token, message)
    if legacy._contains_any(n, legacy.NEGATIVE_MARKERS):
        return await legacy.handle_message(db, token, message)
    if legacy._contains_any(n, legacy.POSITIVE_MARKERS):
        return await legacy.handle_message(db, token, message)

    # Continuação curta precisa casar com a mensagem inteira. Isso impede que "é" -> "e"
    # capture praticamente qualquer frase contendo a letra e e recicle um estado emocional velho.
    if _exact_continuation(text):
        return await legacy.handle_message(db, token, message)

    return False
