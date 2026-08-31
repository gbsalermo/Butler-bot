import asyncio
from datetime import datetime, timezone

import correction_patch


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
        if "FROM users" in self.sql:
            chat_id = int(self.args[0])
            uid = self.db.users.get(chat_id)
            return {"id": uid} if uid else None
        if "FROM natural_events" in self.sql:
            uid = int(self.args[0])
            rows = [r for r in self.db.events if r["user_id"] == uid]
            if not rows:
                return None
            return {"detail": rows[-1]["detail"], "created_at": rows[-1]["created_at"]}
        if "FROM daily_items" in self.sql:
            item_id, uid = map(int, self.args[:2])
            return self.db.items.get((uid, item_id))
        return None

    async def run(self):
        if self.sql.startswith("UPDATE daily_items"):
            new_title, new_date, new_time, item_id, uid = self.args
            item = self.db.items[(int(uid), int(item_id))]
            item["title"] = new_title
            item["due_date"] = new_date
            item["due_time"] = new_time
            item["status"] = "pendente"
        elif "INSERT INTO natural_events" in self.sql:
            uid, target_id, detail = self.args
            self.db.events.append(
                {
                    "user_id": int(uid),
                    "target_id": int(target_id),
                    "detail": detail,
                    "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        return _Result([])


class _DB:
    def __init__(self):
        import json

        fresh = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self.users = {100: 1, 200: 2}
        self.items = {
            (1, 10): {
                "id": 10,
                "kind": "compromisso",
                "title": "Dentista",
                "details": None,
                "due_date": "2026-08-31",
                "due_time": "15:00",
                "status": "pendente",
            },
            (2, 20): {
                "id": 20,
                "kind": "tarefa",
                "title": "Relatório",
                "details": None,
                "due_date": "2026-09-04",
                "due_time": "18:00",
                "status": "pendente",
            },
        }
        self.events = [
            {
                "user_id": 1,
                "target_id": 10,
                "detail": json.dumps(
                    {"kind": "compromisso", "id": 10, "detail": {"source": "created"}, "context_version": 2}
                ),
                "created_at": fresh,
            },
            {
                "user_id": 2,
                "target_id": 20,
                "detail": json.dumps(
                    {"kind": "tarefa", "id": 20, "detail": {"source": "task_list"}, "context_version": 2}
                ),
                "created_at": fresh,
            },
        ]

    def prepare(self, sql):
        return _Stmt(self, sql)


def _fixed_now():
    return datetime(2026, 8, 30, 21, 30, tzinfo=correction_patch.LOCAL_TZ)


def _patch_send(monkeypatch):
    sent = []

    async def fake_send(_token, chat, text, **_kwargs):
        sent.append((chat, text))

    monkeypatch.setattr(correction_patch, "send_message", fake_send)
    return sent


def test_temporal_correction_understands_short_repair_phrases(monkeypatch):
    monkeypatch.setattr(correction_patch, "_now", _fixed_now)
    assert correction_patch.temporal_correction("não, 16h") == {"date": None, "time": "16:00"}
    assert correction_patch.temporal_correction("quis dizer terça")["date"].isoformat() == "2026-09-01"
    result = correction_patch.temporal_correction("na verdade quarta às 14:30")
    assert result["date"].isoformat() == "2026-09-02"
    assert result["time"] == "14:30"


def test_elliptical_temporal_replacement_uses_new_side(monkeypatch):
    monkeypatch.setattr(correction_patch, "_now", _fixed_now)
    result = correction_patch.temporal_correction("quinta não, sexta")
    assert result["date"].isoformat() == "2026-09-04"
    assert correction_patch.temporal_correction("15h não, 16h") == {"date": None, "time": "16:00"}


def test_title_correction_is_explicit_and_temporal_has_priority(monkeypatch):
    monkeypatch.setattr(correction_patch, "_now", _fixed_now)
    assert correction_patch.title_correction("não é dentista, é oftalmo") == {
        "expected_old": "dentista",
        "new_title": "oftalmo",
    }
    assert correction_patch.title_correction("dentista não, oftalmo") == {
        "expected_old": "dentista",
        "new_title": "oftalmo",
    }
    assert correction_patch.title_correction("quis dizer oftalmo") == {
        "expected_old": None,
        "new_title": "oftalmo",
    }
    assert correction_patch.title_correction("quis dizer terça") is None


def test_negated_new_reminder_is_not_previous_turn_correction(monkeypatch):
    monkeypatch.setattr(correction_patch, "_now", _fixed_now)
    assert correction_patch.temporal_correction("não me lembra de estudar hoje às 20h") is None
    assert correction_patch.temporal_correction("não essa, a outra") is None
    assert correction_patch.is_undo_phrase("deixa como tava") is True


def test_time_only_correction_updates_recent_created_item_without_duplicate(monkeypatch):
    monkeypatch.setattr(correction_patch, "_now", _fixed_now)
    sent = _patch_send(monkeypatch)

    async def scenario():
        db = _DB()
        handled = await correction_patch.handle_message(
            db,
            "token",
            {"chat": {"id": 100}, "text": "não, 16h"},
        )
        return handled, db

    handled, db = asyncio.run(scenario())
    assert handled is True
    assert db.items[(1, 10)]["due_date"] == "2026-08-31"
    assert db.items[(1, 10)]["due_time"] == "16:00"
    assert len(db.items) == 2
    assert sent and "Corrigido" in sent[-1][1]


def test_title_correction_updates_same_item(monkeypatch):
    monkeypatch.setattr(correction_patch, "_now", _fixed_now)
    sent = _patch_send(monkeypatch)

    async def scenario():
        db = _DB()
        handled = await correction_patch.handle_message(
            db,
            "token",
            {"chat": {"id": 100}, "text": "não é dentista, é oftalmo"},
        )
        return handled, db

    handled, db = asyncio.run(scenario())
    assert handled is True
    assert db.items[(1, 10)]["title"] == "oftalmo"
    assert db.items[(1, 10)]["due_date"] == "2026-08-31"
    assert len(db.items) == 2
    assert "Dentista virou oftalmo" in sent[-1][1]


def test_mismatched_title_correction_is_not_applied(monkeypatch):
    monkeypatch.setattr(correction_patch, "_now", _fixed_now)
    sent = _patch_send(monkeypatch)

    async def scenario():
        db = _DB()
        handled = await correction_patch.handle_message(
            db,
            "token",
            {"chat": {"id": 100}, "text": "não é relatório, é consulta"},
        )
        return handled, db

    handled, db = asyncio.run(scenario())
    assert handled is True
    assert db.items[(1, 10)]["title"] == "Dentista"
    assert "não alterei nada" in sent[-1][1]


def test_undo_restores_immediately_previous_values(monkeypatch):
    monkeypatch.setattr(correction_patch, "_now", _fixed_now)
    sent = _patch_send(monkeypatch)

    async def scenario():
        db = _DB()
        assert await correction_patch.handle_message(
            db, "token", {"chat": {"id": 100}, "text": "não, 16h"}
        )
        assert db.items[(1, 10)]["due_time"] == "16:00"
        assert await correction_patch.handle_message(
            db, "token", {"chat": {"id": 100}, "text": "deixa como tava"}
        )
        return db

    db = asyncio.run(scenario())
    assert db.items[(1, 10)]["title"] == "Dentista"
    assert db.items[(1, 10)]["due_date"] == "2026-08-31"
    assert db.items[(1, 10)]["due_time"] == "15:00"
    assert "Voltei como estava" in sent[-1][1]


def test_multi_turn_correction_keeps_only_last_step_for_undo(monkeypatch):
    monkeypatch.setattr(correction_patch, "_now", _fixed_now)
    _patch_send(monkeypatch)

    async def scenario():
        db = _DB()
        assert await correction_patch.handle_message(
            db, "token", {"chat": {"id": 100}, "text": "não, 16h"}
        )
        assert await correction_patch.handle_message(
            db, "token", {"chat": {"id": 100}, "text": "15h não, 17h"}
        )
        assert db.items[(1, 10)]["due_time"] == "17:00"
        assert await correction_patch.handle_message(
            db, "token", {"chat": {"id": 100}, "text": "desfaz"}
        )
        return db

    db = asyncio.run(scenario())
    assert db.items[(1, 10)]["due_time"] == "16:00"


def test_list_context_cannot_be_silently_corrected_or_undone(monkeypatch):
    monkeypatch.setattr(correction_patch, "_now", _fixed_now)

    async def scenario():
        db = _DB()
        corrected = await correction_patch.handle_message(
            db,
            "token",
            {"chat": {"id": 200}, "text": "melhor quinta"},
        )
        undone = await correction_patch.handle_message(
            db,
            "token",
            {"chat": {"id": 200}, "text": "deixa como tava"},
        )
        return corrected, undone, db

    corrected, undone, db = asyncio.run(scenario())
    assert corrected is False
    assert undone is False
    assert db.items[(2, 20)]["due_date"] == "2026-09-04"
    assert db.items[(2, 20)]["due_time"] == "18:00"


def test_plain_message_is_rejected_before_any_db_access():
    class _NoDB:
        def prepare(self, sql):
            raise AssertionError(f"mensagem comum não deveria tocar D1: {sql}")

    handled = asyncio.run(
        correction_patch.handle_message(
            _NoDB(),
            "token",
            {"chat": {"id": 100}, "text": "como tá meu dia?"},
        )
    )
    assert handled is False
