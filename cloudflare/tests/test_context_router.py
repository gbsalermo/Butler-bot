from context_router import classify
from action_policy import policy

CASES = [
    ("queria faltar essa aula de sistemas digitais 1","academic","core"),
    ("segunda tenho prova de fisica?","academic","core"),
    ("me lembra de entregar o trabalho amanhã","tasks","core"),
    ("bota ração na lista","grocery","core"),
    ("qual treino de hoje?","workout","core"),
    ("quanto gastei esse mes?","finance","core"),
    ("receita de carbonara","cooking","library"),
    ("queria fazer um macarrao","cooking","library"),
    ("me indica um jogo leve pra pc","games","library"),
    ("me indica um livro brasileiro","books","library"),
    ("oi butler","conversation","conversation"),
]

def test_routes():
    for text,domain,tier in CASES:
        route=classify(text)
        assert route.domain==domain,(text,route)
        assert route.tier==tier,(text,route)

def test_action_policy():
    assert policy("bota ração na lista")=="action"
    assert policy("acabou a ração do Jake")=="help_suggest"
    assert policy("to cansado pra caramba hoje")=="conversation"
