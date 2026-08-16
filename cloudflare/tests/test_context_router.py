from context_router import classify
from action_policy import policy
from intent_parser import parse

CASES = [
    # acadêmico
    ("queria faltar essa aula de sistemas digitais 1","academic","core"),
    ("vou matar fisica amanha","academic","core"),
    ("nao vou para aula de calculo sexta","academic","core"),
    ("qual aula tenho segunda","academic","core"),
    ("que materia tenho amanha","academic","core"),
    ("tenho prova de fisica sexta","academic","core"),
    ("prova de calculo amanha","academic","core"),
    # tarefas
    ("me lembra de pagar a conta amanha","tasks","core"),
    ("me lembre de mandar email sexta","tasks","core"),
    ("nao posso esquecer de entregar o trabalho","tasks","core"),
    ("tenho que fazer o relatorio","tasks","core"),
    ("anota pra mim revisar o projeto","tasks","core"),
    ("cria uma tarefa para revisar swagger","tasks","core"),
    ("ja fiz o relatorio","tasks","core"),
    # mercado
    ("bota cafe na lista","grocery","core"),
    ("coloca na lista detergente","grocery","core"),
    ("preciso comprar arroz","grocery","core"),
    ("comprar feijao","grocery","core"),
    ("o que ta faltando em casa","grocery","core"),
    ("o que tem na lista","grocery","core"),
    # agenda
    ("o que tenho agendado segunda","appointments","core"),
    ("o que tenho marcado amanha","appointments","core"),
    ("marca dentista sexta as 15h","appointments","core"),
    ("agenda reuniao amanha","appointments","core"),
    ("tenho dentista sexta","appointments","core"),
    # musculação
    ("qual treino de hoje","workout","core"),
    ("treino de amanha","workout","core"),
    ("o que treino segunda","workout","core"),
    ("nao consigo treinar hoje","workout","core"),
    ("nao vou treinar amanha","workout","core"),
    ("vou faltar ao treino hoje","workout","core"),
    # finanças
    ("gastei 35 com lanche","finance","core"),
    ("paguei 80 de internet","finance","core"),
    ("recebi 500 de bolsa","finance","core"),
    ("entrou 1000 salario","finance","core"),
    ("quanto gastei esse mes","finance","core"),
    ("quanto entrou esse mes","finance","core"),
    ("saldo do mes","finance","core"),
    # rotina
    ("cria rotina de beber agua","routine","core"),
    ("monta uma rotina para estudar ingles","routine","core"),
    ("quero uma rotina de leitura","routine","core"),
    ("quero estudar ingles todo dia","routine","core"),
    ("quais minhas rotinas","routine","core"),
    ("como ta minha rotina","routine","core"),
    # culinária
    ("receita de carbonara","cooking","library"),
    ("como fazer feijao","cooking","library"),
    ("queria fazer moqueca","cooking","library"),
    ("o que posso fazer com carne moida","cooking","library"),
    ("sobrou arroz de ontem","cooking","library"),
    ("tenho batata e carne","cooking","library"),
    # jogos
    ("me indica um jogo leve pra pc","games","library"),
    ("recomenda um jogo de estrategia","games","library"),
    ("quero um jogo coop","games","library"),
    ("pokemon fire red","games","library"),
    # livros
    ("me indica um livro brasileiro","books","library"),
    ("recomenda uma leitura curta","books","library"),
    ("quero um livro existencial","books","library"),
    # filmes/séries/cultura
    ("me indica um filme de ficcao cientifica","movies_series","library"),
    ("recomenda uma serie curta","movies_series","library"),
    ("quero uma serie de misterio","movies_series","library"),
    ("quem e walter white","culture","library"),
    ("me fala sobre palpatine","culture","library"),
    # conversa
    ("oi butler","conversation","conversation"),
    ("to cansado hj","conversation","conversation"),
    ("kkkk","conversation","conversation"),
    ("valeu butler","conversation","conversation"),
    ("como voce ta","conversation","conversation"),
    ("to meio na merda hoje","conversation","conversation"),
]


def test_routes():
    assert len(CASES) >= 65
    for text,domain,tier in CASES:
        route=classify(text)
        assert route.domain==domain,(text,route)
        assert route.tier==tier,(text,route)


def test_action_policy():
    expected={
        "bota ração na lista":"action",
        "adiciona cafe":"action",
        "me lembra de pagar amanhã":"action",
        "cria uma rotina":"action",
        "acabou a ração do Jake":"help_suggest",
        "to sem cafe":"help_suggest",
        "não sei o que fazer":"help_suggest",
        "preciso organizar isso":"help_suggest",
        "to cansado pra caramba hoje":"conversation",
        "oi butler":"conversation",
        "kkkk":"conversation",
        "Jake aprontou de novo":"conversation",
    }
    for text,want in expected.items():
        assert policy(text)==want,(text,policy(text))


def test_structured_intents():
    cases={
        "quero faltar fisica segunda":("academic_absence","academic"),
        "me lembra de mandar email amanha":("task_reminder","tasks"),
        "bota cafe na lista":("grocery_add","grocery"),
        "o que tenho agendado sexta":("appointment_query","appointments"),
        "nao consigo treinar hoje":("workout_skip","workout"),
        "gastei 20 com almoço":("finance_expense","finance"),
        "cria rotina de beber agua":("routine_create","routine"),
        "como fazer moqueca":("cooking_request","cooking"),
        "me indica um jogo leve":("recommend_game","games"),
        "me indica um livro brasileiro":("recommend_book","books"),
        "me indica uma serie curta":("recommend_screen","movies_series"),
    }
    for text,(intent,domain) in cases.items():
        parsed=parse(text)
        assert parsed.intent==intent,(text,parsed)
        assert parsed.domain==domain,(text,parsed)


def test_time_hints():
    assert parse("quero faltar fisica segunda").time_hint=="segunda"
    assert parse("me lembra de pagar amanha").time_hint=="amanha"
    assert parse("marca dentista 18h").time_hint=="18h"
