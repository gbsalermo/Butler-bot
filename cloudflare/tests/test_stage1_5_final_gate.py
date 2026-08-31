import asyncio
from datetime import datetime

import compound_router
import short_context


def _now():
    return datetime(2026, 8, 31, 19, 0, tzinfo=compound_router.LOCAL_TZ)


def test_three_actions_are_planned_in_display_order():
    text = (
        "tenho que pagar o boleto amanhã e "
        "tenho dentista quarta às 15h e "
        "me lembra de enviar o documento sexta às 9h"
    )
    analysis = compound_router.analyze_compound(text)
    plan = compound_router.build_batch_plan(analysis, now=_now())

    assert plan is not None
    assert len(plan) == 3
    assert [item["family"] for item in plan] == [
        "create_task",
        "create_appointment",
        "reminder",
    ]
    assert [item["title"] for item in plan] == [
        "pagar o boleto",
        "dentista",
        "enviar o documento",
    ]


def test_five_actions_are_supported_but_six_are_rejected():
    five = (
        "tenho que pagar o boleto amanhã e "
        "tenho dentista quarta às 15h e "
        "tenho que comprar café quinta e "
        "me lembra de enviar o documento sexta às 9h e "
        "tenho reunião sábado às 11h"
    )
    plan = compound_router.build_batch_plan(
        compound_router.analyze_compound(five),
        now=_now(),
    )
    assert plan is not None
    assert len(plan) == 5

    six = five + " e tenho que organizar a mesa domingo"
    analysis = compound_router.analyze_compound(six)
    assert len(analysis["automatic_actions"]) == 6
    assert compound_router.build_batch_plan(analysis, now=_now()) is None


def test_two_users_prepare_independent_batches(monkeypatch):
    stored = {}
    sent = []

    async def fake_uid(_db, chat_id):
        return {100: 1, 200: 2}[chat_id]

    async def fake_set_state(_db, uid, state, payload):
        stored[uid] = (state, payload)

    async def fake_send(_token, chat_id, text, **_kwargs):
        sent.append((chat_id, text))

    monkeypatch.setattr(compound_router, "_uid", fake_uid)
    monkeypatch.setattr(compound_router.app, "set_state", fake_set_state)
    monkeypatch.setattr(compound_router, "send_message", fake_send)
    monkeypatch.setattr(compound_router, "_now", _now)

    async def scenario():
        first = await compound_router.handle_message(
            object(),
            "token",
            {
                "chat": {"id": 100},
                "text": "tenho que pagar o boleto amanhã e tenho dentista quarta às 15h",
            },
        )
        second = await compound_router.handle_message(
            object(),
            "token",
            {
                "chat": {"id": 200},
                "text": "tenho que comprar café quinta e tenho reunião sábado às 11h",
            },
        )
        return first, second

    first, second = asyncio.run(scenario())
    assert first is True and second is True
    assert set(stored) == {1, 2}
    assert stored[1][0] == compound_router.BATCH_STATE
    assert stored[2][0] == compound_router.BATCH_STATE
    assert stored[1][1]["plans"][0]["title"] == "pagar o boleto"
    assert stored[2][1]["plans"][0]["title"] == "comprar café"
    assert len(sent) == 2


def test_post_batch_ordinal_reference_uses_displayed_order():
    payload = {
        "kind": "daily_item",
        "id": 41,
        "candidate_ids": [41, 42, 43],
        "history_ids": [41],
    }

    assert short_context.referenced_candidate_id(payload, "conclui a primeira") == 41
    assert short_context.referenced_candidate_id(payload, "cancela a segunda") == 42
    assert short_context.referenced_candidate_id(payload, "muda a terceira pra sexta") == 43


def test_contextual_clause_inside_large_sentence_is_not_promoted_to_batch_action():
    text = (
        "tenho que pagar o boleto amanhã e "
        "tenho dentista quarta às 15h porque tenho que buscar um documento e "
        "me lembra de enviar o relatório sexta às 9h"
    )
    analysis = compound_router.analyze_compound(text)

    # A ação dentro do `porque` pode ser reconhecida linguisticamente, mas não é
    # candidata automática. O lote, se existir, só pode conter ações independentes.
    contextual = [s for s in analysis["segments"] if s.get("contextual")]
    assert contextual
    assert all(s.get("automatic_candidate") is False for s in contextual)
