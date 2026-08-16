"""Política transversal: conversar, agir ou sugerir.

A camada de linguagem pode sugerir. Escrita continua pertencendo ao Core e deve
ser confirmada quando derivada de comentário/problema, não de comando explícito.
"""
from language_context import conversation_shape

ACTION_WORDS=("adiciona","adicionar","marca","marcar","cria","criar","remove","remover","apaga","apagar","concluir","conclui","registra","registrar","bota","coloca","salva","salvar","me lembra")
PROBLEM_WORDS=("acabou","to sem","estou sem","nao tenho","não tenho","nao sei","não sei","preciso","esqueci","dificuldade","problema")

def policy(text):
    low=(text or "").lower()
    if any(x in low for x in ACTION_WORDS):return "action"
    if any(x in low for x in PROBLEM_WORDS):return "help_suggest"
    shape=conversation_shape(text)
    if shape=="request":return "help_suggest"
    return "conversation"

def requires_confirmation(text, write=False):
    if not write:return False
    return policy(text)!="action"
