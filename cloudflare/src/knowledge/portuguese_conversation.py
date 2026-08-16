"""Acervo linguístico auxiliar para NLU e roteamento.

Não responde perguntas por conta própria. Serve para normalizar fala informal, reconhecer
formas coloquiais e detectar mudanças de domínio sem transformar cada frase em um if.
"""

INFORMAL_EQUIVALENTS = {
    "oq": "o que", "q": "que", "pq": "porque", "porq": "porque",
    "vc": "voce", "vcs": "voces", "tb": "tambem", "tbm": "tambem",
    "hj": "hoje", "amanha": "amanha", "dps": "depois", "agr": "agora",
    "to": "estou", "tô": "estou", "ta": "esta", "tá": "esta",
    "num": "nao", "n": "nao", "blz": "beleza", "vlw": "valeu",
    "fds": "fim de semana", "facul": "faculdade", "trampo": "trabalho",
    "busu": "onibus", "mano": "mano", "vei": "cara", "véi": "cara",
}

CONVERSATION_MARKERS = {
    "greeting": ["oi", "ola", "opa", "e ai", "fala ai", "fala dai", "bom dia", "boa tarde", "boa noite"],
    "agreement": ["sim", "pode", "bora", "fechado", "demorou", "show", "blz", "beleza"],
    "disagreement": ["nao", "deixa", "melhor nao", "nem", "esquece"],
    "uncertainty": ["acho que", "talvez", "sei la", "nao sei", "to pensando", "queria", "tava pensando"],
    "problem": ["deu ruim", "to na merda", "ta osso", "complicou", "ferrou", "me lasquei", "nao vai dar"],
    "fatigue": ["to morto", "to cansado", "sem energia", "morrendo de sono", "capotando"],
    "humor": ["kkkk", "kkk", "rsrs", "haha", "pqp", "slk", "miseravel", "desgracado"],
}

CORE_DOMAIN_TERMS = {
    "academic": ["aula", "materia", "disciplina", "prova", "faculdade", "universidade", "professor", "professora", "semestre", "laboratorio", "faltas", "presenca", "grade"],
    "tasks": ["tarefa", "tarefas", "pendencia", "pendencias", "lembrar", "lembrete", "fazer depois", "prazo"],
    "appointments": ["compromisso", "compromissos", "agenda", "agendado", "agendada", "marcado", "marcada", "horario"],
    "grocery": ["lista", "item faltando", "mercado", "comprar", "compras", "faltando em casa"],
    "workout": ["treino", "treinar", "musculacao", "academia", "exercicio", "exercicios", "serie", "series", "repeticoes", "carga"],
    "finance": ["dinheiro", "gasto", "gastos", "entrada", "saida", "salario", "pix", "financas", "economia", "meta financeira"],
    "routine": ["rotina", "rotinas", "meta", "metas", "agua", "ingles", "programacao"],
}

CORE_PATTERNS = {
    "academic": ["vou faltar", "queria faltar", "nao vou pra aula", "nao vou para aula", "tenho aula", "qual aula", "minha materia"],
    "tasks": ["me lembra", "me lembre", "anota pra mim", "anote pra mim", "tenho que fazer", "preciso fazer"],
    "appointments": ["o que tenho", "oq tenho", "tenho marcado", "tenho agendado", "marca pra", "marca para"],
    "grocery": ["bota na lista", "coloca na lista", "adiciona na lista", "ta faltando em casa"],
    "workout": ["começar os trabalhos", "comecar os trabalhos", "qual treino", "treino de hoje", "nao consigo treinar"],
    "finance": ["quanto gastei", "quanto entrou", "quanto saiu", "gastei", "recebi"],
}
