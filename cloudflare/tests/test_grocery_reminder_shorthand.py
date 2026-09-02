import asyncio

import colloquial_reminder_fastpath
import grocery_phrase_patch


def test_unscheduled_purchase_reminder_extracts_items_but_timed_one_does_not():
    assert grocery_phrase_patch.unscheduled_purchase_reminder_items("me lembra de comprar café") == ["cafe"]
    assert grocery_phrase_patch.unscheduled_purchase_reminder_items("me lembre de comprar arroz e feijão") == ["arroz", "feijao"]
    assert grocery_phrase_patch.unscheduled_purchase_reminder_items("não deixa eu esquecer de comprar detergente") == ["detergente"]

    assert grocery_phrase_patch.unscheduled_purchase_reminder_items("me lembra de comprar café amanhã às 18h") == []
    assert grocery_phrase_patch.unscheduled_purchase_reminder_items("me avisa de comprar pão sexta 10h") == []


def test_reminder_handler_yields_unscheduled_purchase_to_grocery(monkeypatch):
    async def scenario():
        async def fake_uid(_db, _chat_id):
            return 7

        async def fake_get_state(_db, _uid):
            return None, {}

        async def fail_send(*_args, **_kwargs):
            raise AssertionError("lembrete sem data/hora não deve abrir wizard temporal")

        monkeypatch.setattr(colloquial_reminder_fastpath, "_uid", fake_uid)
        monkeypatch.setattr(colloquial_reminder_fastpath.app, "get_state", fake_get_state)
        monkeypatch.setattr(colloquial_reminder_fastpath, "send_message", fail_send)

        consumed = await colloquial_reminder_fastpath.handle_message(
            object(),
            "token",
            {"chat": {"id": 123}, "text": "me lembra de comprar café"},
        )
        assert consumed is False

    asyncio.run(scenario())


def test_grocery_handler_persists_unscheduled_purchase_reminder(monkeypatch):
    async def scenario():
        saved_calls = []
        sent = []

        async def fake_uid(_db, _chat_id):
            return 7

        async def fake_add(_db, uid, items):
            saved_calls.append((uid, items))
            return items

        async def fake_send(_token, chat_id, text, reply_markup=None):
            sent.append((chat_id, text, reply_markup))
            return {"ok": True}

        monkeypatch.setattr(grocery_phrase_patch, "_uid", fake_uid)
        monkeypatch.setattr(grocery_phrase_patch, "add_grocery_items", fake_add)
        monkeypatch.setattr(grocery_phrase_patch, "send_message", fake_send)

        consumed = await grocery_phrase_patch.handle_message(
            object(),
            "token",
            {"chat": {"id": 123}, "text": "me lembra de comprar café e detergente"},
        )

        assert consumed is True
        assert saved_calls == [(7, ["cafe", "detergente"])]
        assert "lista de compras" in sent[-1][1]

    asyncio.run(scenario())
