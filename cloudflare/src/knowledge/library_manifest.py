"""Manifesto dos acervos opcionais.

Separa conteúdo de mecanismo e deixa explícito como novos acervos devem crescer.
O motor não deve ganhar um novo dispatcher para cada exemplo.
"""
LIBRARY_MANIFEST = {
    "cooking": {"source":"knowledge/cooking_books.py + knowledge/meat_cuts.py + knowledge/brazilian_cooking.py","mode":"structured","optional":True},
    "games": {"source":"knowledge/games.py","mode":"structured","optional":True},
    "movies_series": {"source":"knowledge/pop_culture.py","mode":"structured","optional":True},
    "books": {"source":"knowledge/books.py","mode":"structured","optional":True},
    "philosophy": {"source":"knowledge/philosophy.py","mode":"structured","optional":True},
    "language": {"source":"knowledge/portuguese_conversation.py","mode":"background-only","optional":True,"responds_directly":False},
}

LIBRARY_RULES = (
    "Core funcional sempre tem prioridade.",
    "Acervo pode responder ou sugerir, nunca escrever silenciosamente no Core.",
    "Conhecimento novo entra como dados/tags/aliases, não como if específico.",
    "Background linguístico auxilia roteamento e conversa, não vira domínio de perguntas.",
)
