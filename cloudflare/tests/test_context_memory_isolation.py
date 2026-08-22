import asyncio

import context_memory


class FakeStatement:
    def __init__(self, db, sql):
        self.db = db
        self.sql = " ".join(sql.split())
        self.args = ()

    def bind(self, *args):
        self.args = args
        return self

    async def first(self):
        if self.sql.startswith("SELECT topics_json FROM conversation_context"):
            user_id = self.args[0]
            payload = self.db.context.get(user_id)
            return {"topics_json": payload} if payload is not None else None
        raise AssertionError(f"SELECT não suportado no fake: {self.sql}")

    async def run(self):
        if self.sql.startswith("CREATE TABLE IF NOT EXISTS conversation_context"):
            return None
        if self.sql.startswith("INSERT INTO conversation_context"):
            user_id, payload, _updated_at = self.args
            self.db.context[user_id] = payload
            return None
        if self.sql.startswith("UPDATE conversation_context SET topics_json"):
            payload, _updated_at, user_id = self.args
            if user_id in self.db.context:
                self.db.context[user_id] = payload
            return None
        raise AssertionError(f"SQL não suportado no fake: {self.sql}")


class FakeDB:
    def __init__(self):
        self.context = {}

    def prepare(self, sql):
        return FakeStatement(self, sql)


def test_recent_context_is_isolated_by_user_id():
    async def scenario():
        context_memory._SCHEMA_READY = False
        db = FakeDB()

        await context_memory.remember_topic(db, 101, "cooking", "carbonara")
        await context_memory.remember_topic(db, 202, "games", "pokemon fire red")
        await context_memory.remember_topic(db, 101, "academic", "Sistemas Digitais I")

        user_a = await context_memory.get_topics(db, 101)
        user_b = await context_memory.get_topics(db, 202)

        assert [item["domain"] for item in user_a] == ["academic", "cooking"]
        assert [item["domain"] for item in user_b] == ["games"]
        assert all(item.get("target") != "pokemon fire red" for item in user_a)
        assert all(item.get("target") != "carbonara" for item in user_b)

        await context_memory.clear_domain(db, 101, "cooking")
        assert [item["domain"] for item in await context_memory.get_topics(db, 101)] == ["academic"]
        assert [item["domain"] for item in await context_memory.get_topics(db, 202)] == ["games"]

    asyncio.run(scenario())


def test_recent_context_keeps_only_three_topics_per_user():
    async def scenario():
        context_memory._SCHEMA_READY = False
        db = FakeDB()
        for domain in ("cooking", "games", "books", "academic"):
            await context_memory.remember_topic(db, 303, domain, domain)

        topics = await context_memory.get_topics(db, 303)
        assert len(topics) == context_memory.MAX_TOPICS == 3
        assert [item["domain"] for item in topics] == ["academic", "books", "games"]

    asyncio.run(scenario())
