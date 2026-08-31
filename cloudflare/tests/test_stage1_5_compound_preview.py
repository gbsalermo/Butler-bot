import asyncio

import compound_router


def _families(analysis):
    return [segment["families"][0] for segment in analysis.get("automatic_actions", [])]


def test_three_action_sentence_is_segmented_with_relations():
    analysis = compound_router.analyze_compound(
        "Amanhã tenho aula às 8, depois quero estudar Java e às 18 tenho dentista."
    )
    assert analysis["is_compound_action"] is True
    assert _families(analysis) == ["scheduled_event", "planned_activity", "create_appointment"]
    assert analysis["automatic_actions"][1]["relation"] == "sequence"
    assert analysis["automatic_actions"][2]["relation"] == "addition"


def test_contrast_only_counts_when_both_sides_are_actions():
    simple = compound_router.analyze_compound("Tenho aula, mas estou cansado.")
    assert simple["is_compound_action"] is False

    compound = compound_router.analyze_compound("Tenho aula, mas às 18 tenho dentista.")
    assert compound["is_compound_action"] is True
    assert _families(compound) == ["scheduled_event", "create_appointment"]


def test_cause_is_context_not_second_automatic_action():
    analysis = compound_router.analyze_compound("Tenho aula porque tenho que trabalhar.")
    assert analysis["is_compound_action"] is False
    assert analysis["has_context_clause"] is True
    assert any(s["families"] == ["create_task"] and s["contextual"] for s in analysis["action_segments"])


def test_and_inside_reminder_content_does_not_split_into_two_actions():
    analysis = compound_router.analyze_compound("Me lembra de comprar pão e leite amanhã.")
    assert analysis["is_compound_action"] is False
    assert len(analysis["automatic_actions"]) == 1
    assert _families(analysis) == ["reminder"]


def test_and_inside_person_names_does_not_create_extra_appointment():
    analysis = compound_router.analyze_compound("Tenho reunião com João e Maria amanhã.")
    assert analysis["is_compound_action"] is False
    assert len(analysis["automatic_actions"]) == 1


def test_alternative_is_not_auto_executed_as_two_actions():
    analysis = compound_router.analyze_compound("Tenho aula ou tenho dentista às 18h.")
    assert analysis["is_compound_action"] is False
    assert analysis["requires_choice"] is True


def test_two_clear_actions_are_previewed_without_db_access(monkeypatch):
    sent = []

    async def fake_send(_token, chat_id, text, **_kwargs):
        sent.append((chat_id, text))

    monkeypatch.setattr(compound_router, "send_message", fake_send)

    class _NoDB:
        def prepare(self, sql):
            raise AssertionError(f"preview composto não deve tocar D1: {sql}")

    handled = asyncio.run(
        compound_router.handle_message(
            _NoDB(),
            "token",
            {"chat": {"id": 10}, "text": "Tenho aula e às 18 tenho dentista"},
        )
    )
    assert handled is True
    assert sent
    assert "mais de uma ação" in sent[0][1]
    assert "evento acadêmico" in sent[0][1]
    assert "compromisso" in sent[0][1]


def test_non_compound_message_returns_before_db_and_telegram(monkeypatch):
    async def forbidden_send(*_args, **_kwargs):
        raise AssertionError("mensagem simples não deveria gerar preview")

    monkeypatch.setattr(compound_router, "send_message", forbidden_send)

    class _NoDB:
        def prepare(self, sql):
            raise AssertionError(f"não deveria tocar D1: {sql}")

    handled = asyncio.run(
        compound_router.handle_message(
            _NoDB(), "token", {"chat": {"id": 10}, "text": "Tenho aula amanhã"}
        )
    )
    assert handled is False
