from compound_router import _split, _domain, _social_reason


def test_full_stress_sentence_is_split_into_domains():
    text=(
        "Butler, segunda tenho sistemas certo? "
        "Tava pensando em faltar porque domingo vou sair com jessica. "
        "Me fala uma receita de vaca atolada e lembra que acabou a ração de jake"
    )
    parts=_split(text)
    assert len(parts)==4,parts
    assert [_domain(p) for p in parts]==["academic","academic","cooking","pet_supply"]


def test_social_reason_keeps_context_without_inferring_relation():
    assert _social_reason("Tava pensando em faltar porque domingo vou sair com jessica")== ("domingo","Jessica")


def test_compound_academic_keeps_both_signals():
    text="Segunda eu queria faltar sistemas digitais 1 quantas faltas eu tenho nela?"
    parts=_split(text)
    assert len(parts)==1
    assert _domain(parts[0])=="academic"


def test_simple_message_is_not_artificially_split():
    assert _split("receita de carbonara")==["receita de carbonara"]
