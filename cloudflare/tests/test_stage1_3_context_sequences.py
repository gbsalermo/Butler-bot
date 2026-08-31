import asyncio
from datetime import datetime, timezone

import conversation_layer
import language_primitives as language
import short_context


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
            rows = [row for row in self.db.events if row["user_id"] == uid and row["event_type"] == "context"]
            if not rows:
                return None
            row = rows[-1]
            return {"detail": row["detail"], "created_at": row["created_at"]}

        if "FROM daily_items" in self.sql:
            item_id = int(self.args[0])
            uid = int(self.args[1])
            row = self.db.items.get((uid, item_id))
            if not row:
                return None
            if "AND kind=?" in self.sql and row.get("kind") != self.args[2]:
                return None
            return row
        return None

    async def run(self):
        if "INSERT INTO natural_events" in self.sql:
            uid, target_id, detail = self.args
            self.db.events.append(
                {
                    "user_id": int(uid),
                    "event_type": "context",
                    "target_id": target_id,
                    "detail": detail,
                    "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        return _Result([])

    async def all(self):
        return _Result([])


class _DB:
    def __init__(self):
        self.events = []
        self.items = {}

    def prepare(self, sql):
        return _Stmt(self, sql)

    def add_item(self, uid, item_id, title, kind="tarefa", due_date="2026-08-31"):
        self.items[(uid, item_id)] = {
            "id": item_id,
            "user_id": uid,
            "title": title,
            "kind": kind,
            "status": "pendente",
            "due_date": due_date,
            "due_time": "12:00",
        }


def test_five_turn_sequence_tracks_current_and_previous_target():
    async def scenario():
        db = _DB()
        db.add_item(1, 10, "Terminar relatório")
        db.add_item(1, 20, "Dentista", kind="compromisso")

        # turno 1: Butler acabou de criar/mostrar a tarefa 10
        await short_context.remember(db, 1, "tarefa", 10)

        # turno 2: "muda ela pra sexta" aponta para a tarefa atual
        current_a = await short_context.resolve_daily_item(db, 1, "muda ela pra sexta")

        # turno 3: conversa muda explicitamente para um novo compromisso
        await short_context.remember(db, 1, "compromisso", 20)

        # turno 4: "cancela esse" aponta para o novo foco
        current_b = await short_context.resolve_daily_item(db, 1, "cancela esse")

        # turno 5: "a anterior" recupera o foco imediatamente anterior
        payload = await short_context.latest(db, 1)
        previous_id = short_context.referenced_candidate_id(payload, "cancela a anterior")
        return current_a, current_b, previous_id, payload

    current_a, current_b, previous_id, payload = asyncio.run(scenario())
    assert current_a["id"] == 10
    assert current_b["id"] == 20
    assert previous_id == 10
    assert payload["history_ids"][:2] == [20, 10]


def test_visible_list_then_second_item_uses_same_order_user_saw():
    async def scenario():
        db = _DB()
        for item_id, title in ((31, "A"), (44, "B"), (58, "C")):
            db.add_item(1, item_id, title)
        await short_context.remember_list(db, 1, "tarefa", [31, 44, 58], source="task_list")
        return await short_context.resolve_daily_item(db, 1, "conclui a segunda", kind="tarefa")

    item = asyncio.run(scenario())
    assert item["id"] == 44


def test_third_item_is_visible_to_common_reference_detector_and_resolver():
    refs = language.detect_references("cancela a terceira")
    assert any(ref["kind"] == "ordinal" and ref["value"] == "a terceira" for ref in refs)
    assert short_context.ordinal_index("cancela a terceira") == 2
    assert short_context.referenced_candidate_id(
        {"id": 31, "candidate_ids": [31, 44, 58]},
        "cancela a terceira",
    ) == 58


def test_two_users_keep_independent_recent_context():
    async def scenario():
        db = _DB()
        db.add_item(1, 11, "Usuário um")
        db.add_item(2, 22, "Usuário dois")
        await short_context.remember(db, 1, "tarefa", 11)
        await short_context.remember(db, 2, "tarefa", 22)
        one = await short_context.resolve_daily_item(db, 1, "conclui ela")
        two = await short_context.resolve_daily_item(db, 2, "conclui ela")
        return one, two

    one, two = asyncio.run(scenario())
    assert one["id"] == 11
    assert two["id"] == 22


def test_new_creation_is_a_context_barrier_for_resolution():
    assert not short_context.should_consume_context("cria uma tarefa comprar café amanhã")
    assert not short_context.should_consume_context("tenho dentista amanhã às 15h")
    assert not short_context.should_consume_context("me lembra amanhã de levar documento")


def test_legacy_conversation_layer_context_is_redirected_to_v2():
    async def scenario():
        db = _DB()
        short_context.install()
        await conversation_layer._remember(db, 1, "tarefa", 90, {"source": "legacy-caller"})
        return await short_context.latest(db, 1)

    payload = asyncio.run(scenario())
    assert payload["id"] == 90
    assert payload["context_version"] == 2
    assert payload["detail"]["source"] == "legacy-caller"
