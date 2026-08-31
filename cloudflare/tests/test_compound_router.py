from compound_router import analyze_compound, is_compound_action


def test_legacy_cross_domain_router_is_not_reactivated():
    text = (
        "Butler, segunda tenho sistemas certo? "
        "Tava pensando em faltar porque domingo vou sair com jessica. "
        "Me fala uma receita de vaca atolada e lembra que acabou a ração de jake"
    )
    analysis = analyze_compound(text)

    # A Etapa 1.5 não reativa o roteador antigo que classificava culinária,
    # pets e memória pessoal dentro do Core operacional.
    assert "segments" in analysis
    assert is_compound_action(text) is False


def test_social_context_does_not_become_automatic_action():
    analysis = analyze_compound(
        "Tava pensando em faltar porque domingo vou sair com Jessica"
    )
    assert analysis["is_compound_action"] is False


def test_academic_question_is_not_artificially_converted_into_multi_action():
    analysis = analyze_compound(
        "Segunda eu queria faltar sistemas digitais 1 quantas faltas eu tenho nela?"
    )
    assert analysis["is_compound_action"] is False


def test_simple_legacy_domain_message_is_not_compound():
    assert is_compound_action("receita de carbonara") is False
