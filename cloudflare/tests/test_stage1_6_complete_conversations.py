import asyncio
import json
from datetime import datetime, timedelta, timezone

import compound_router
import correction_patch
import language_primitives as language
import short_context
import temporal_language


class _Result:
    def __init__(self, rows=None):
        self.results = rows or []


class _Stmt:
    def __init__(self, db, sql):
        self.db = db
        self.sql = " ".join(sql.split())
        self.args = ()

    def bind(self, *args):
        self.args = args
        return self

    async def first(self):
        if "FROM natural_events" in self.sql:
            uid = int(self.args[0])
            rows = [event for event in self.db.events if event["user_id"] == uid]
            if not rows:
                return None
            event = rows[-1]
            return {"detail": event["detail"], "created_at": event["created_at"]}

        if "FROM daily_items" in self.sql:
            item_id, uid = int(self.args[0]), int(self.args[1])
            return self.db.items.get((uid, item_id))
        return None

    async def run(self):
        if self.sql.startswith("INSERT INTO natural_events"):
            uid, target_id, detail = self.args
            self.db.sequence += 1
            self.db.events.append(
                {
                    "id": self.db.sequence,
                    "user_id": int(uid),
                    "target_id": int(target_id) if target_id is not None else None,
                    "detail": detail,
                    "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        return _Result()


class _ContextDB:
    def __init__(self):
        self.sequence = 0
        self.events = []
        self.items = {
            (1, 11): {"id": 11, "kind": "tarefa", "title": "Pagar boleto", "due_date": "2026-09-01"},
            (1, 12): {"id": 12, "kind": "compromisso", "title": "Dentista", "due_date": "2026-09-02"},
            (1, 13): {"id": 13, "kind": "tarefa", "title": "Enviar relatório", "due_date": "2026-09-04"},
            (1, 99): {"id": 99, "kind": "tarefa", "title": "Item novo", "due_date": "2026-09-06"},
            (2, 21): {"id": 21, "kind": "tarefa", "title": "Comprar café", "due_date": "2026-09-03"},
            (2, 22): {"id": 22, "kind": "compromisso", "title": "Reunião", "due_date": "2026-09-05"},
        }

    def prepare(self, sql):
        return _Stmt(self, sql)


def test_batch_then_first_then_second_keeps_original_list_context():
    async def scenario():
        db = _ContextDB()
        await short_context.remember_list(db, 1, "daily_item", [11, 12, 13], source="compound_created")

        first = await short_context.resolve_daily_item(db, 1, "conclui a primeira")
        assert first["id"] == 11

        # Simula o foco gravado pelo handler após agir sobre a primeira.
        focused = await short_context.remember(db, 1, "tarefa", 11)
        assert focused["candidate_ids"] == [11, 12, 13]

        second = await short_context.resolve_daily_item(db, 1, "cancela a segunda")
        assert second["id"] == 12

        await short_context.remember(db, 1, "compromisso", 12)
        third = await short_context.resolve_daily_item(db, 1, "muda a terceira pra sexta")
        assert third["id"] == 13

    asyncio.run(scenario())


def test_new_item_outside_previous_list_does_not_inherit_candidates():
    async def scenario():
        db = _ContextDB()
        await short_context.remember_list(db, 1, "daily_item", [11, 12, 13], source="list")
        payload = await short_context.remember(db, 1, "tarefa", 99, {"source": "created"})
        assert payload["candidate_ids"] == []
        assert short_context.referenced_candidate_id(payload, "a segunda") is None

    asyncio.run(scenario())


def test_two_users_keep_independent_context_through_multiple_turns():
    async def scenario():
        db = _ContextDB()
        await short_context.remember_list(db, 1, "daily_item", [11, 12, 13], source="list")
        await short_context.remember_list(db, 2, "daily_item", [21, 22], source="list")

        user1 = await short_context.resolve_daily_item(db, 1, "cancela a segunda")
        user2 = await short_context.resolve_daily_item(db, 2, "cancela a segunda")
        assert user1["id"] == 12
        assert user2["id"] == 22

        await short_context.remember(db, 1, "compromisso", 12)
        user2_again = await short_context.resolve_daily_item(db, 2, "conclui a primeira")
        assert user2_again["id"] == 21

    asyncio.run(scenario())


def test_stale_context_dies_instead_of_resurrecting_old_reference():
    async def scenario():
        db = _ContextDB()
        await short_context.remember_list(db, 1, "daily_item", [11, 12], source="list")
        stale = datetime.now(timezone.utc) - timedelta(minutes=31)
        db.events[-1]["created_at"] = stale.strftime("%Y-%m-%d %H:%M:%S")
        assert await short_context.latest(db, 1) is None
        assert await short_context.resolve_daily_item(db, 1, "cancela a segunda") is None

    asyncio.run(scenario())


def test_new_topic_is_a_context_barrier_and_not_a_correction():
    assert short_context.should_consume_context("qual meu treino hoje?") is False
    assert short_context.should_consume_context("tempo hoje") is False
    assert correction_patch.temporal_correction("qual meu treino hoje?") is None
    assert correction_patch.temporal_correction("tempo amanhã") is None


def test_negation_scope_survives_longer_conversation_contract():
    assert language.action_polarity("não me lembra de estudar amanhã", "reminder") == "negative"
    assert language.action_polarity("me lembra de não faltar amanhã", "reminder") == "positive"
    assert language.action_polarity("não deixa eu esquecer de pagar amanhã", "reminder") == "positive"


def test_compound_context_and_alternative_are_still_non_automatic():
    cause = compound_router.analyze_compound(
        "tenho que pagar o boleto amanhã porque preciso organizar as contas"
    )
    assert cause["is_compound_action"] is False

    alternative = compound_router.analyze_compound(
        "tenho dentista amanhã ou tenho reunião sexta às 15h"
    )
    assert compound_router.build_batch_plan(alternative) is None


def test_quick_time_phrases_are_reserved_for_future_time_assistant():
    cases = {
        "me lembra de desligar o ovo daqui a 5 minutos": ("relative_alert", 300),
        "tenho que ligar para João daqui a 10 minutos": ("relative_alert", 600),
        "me lembra daqui a 1 hora de tirar a roupa do varal": ("relative_alert", 3600),
        "cronometra 30 minutos pra mim": ("timer", 1800),
    }
    for text, expected in cases.items():
        result = temporal_language.classify_quick_time_intent(text)
        assert (result["kind"], result["delay_seconds"]) == expected

    for text in (
        "fiquei 30 minutos estudando",
        "o filme tem 2 horas",
        "corri por 20 minutos",
    ):
        assert temporal_language.classify_quick_time_intent(text)["kind"] is None


def test_compound_batch_keeps_original_accents_in_saved_plan():
    analysis = compound_router.analyze_compound(
        "tenho que comprar café amanhã e tenho reunião quarta às 15h"
    )
    now = datetime(2026, 8, 31, 19, 0, tzinfo=compound_router.LOCAL_TZ)
    plan = compound_router.build_batch_plan(analysis, now=now)
    assert plan is not None
    assert plan[0]["title"] == "comprar café"
    assert plan[1]["title"] == "reunião"
