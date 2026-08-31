import asyncio

import operational_menu


def test_public_ru_keyboard_hides_import_action():
    flat = [item for row in operational_menu.RU_PUBLIC_KB for item in row]
    assert "📤 Atualizar cardápio RU" not in flat
    assert "🍽️ Cardápio de hoje" in flat
    assert "📅 Cardápio da semana" in flat


def test_owner_ru_keyboard_keeps_import_action(monkeypatch):
    monkeypatch.setattr(operational_menu, "is_owner", lambda _chat_id: True)
    flat = [item for row in operational_menu._ru_keyboard(123) for item in row]
    assert "📤 Atualizar cardápio RU" in flat


def test_ru_import_phrase_is_recognized_for_access_guard():
    assert operational_menu._is_ru_import_request("📤 Atualizar cardápio RU")
    assert operational_menu._is_ru_import_request("quero importar cardapio ru")
    assert not operational_menu._is_ru_import_request("qual o almoço hoje?")


def test_non_owner_cannot_start_ru_import(monkeypatch):
    sent = []

    async def fake_uid(_db, _chat_id):
        return 99

    async def fake_state(_db, _uid):
        return None, {}

    async def fake_send(_token, chat_id, text, reply_markup=None, **_kwargs):
        sent.append((chat_id, text, reply_markup))

    async def must_not_reach_ru(*_args, **_kwargs):
        raise AssertionError("usuário comum não pode alcançar o importador do RU")

    monkeypatch.setattr(operational_menu, "_uid", fake_uid)
    monkeypatch.setattr(operational_menu.runtime_guard, "_state", fake_state)
    monkeypatch.setattr(operational_menu, "is_owner", lambda _chat_id: False)
    monkeypatch.setattr(operational_menu, "send_message", fake_send)
    monkeypatch.setattr(operational_menu.ru_menu, "handle_message", must_not_reach_ru)

    handled = asyncio.run(
        operational_menu.handle_message(
            object(),
            "token",
            {"text": "📤 Atualizar cardápio RU", "chat": {"id": 555}},
        )
    )

    assert handled is True
    assert sent
    assert "restrita ao administrador" in sent[0][1]
    keyboard = sent[0][2]["keyboard"]
    assert "📤 Atualizar cardápio RU" not in [item for row in keyboard for item in row]


def test_non_owner_reads_owner_ru_source(monkeypatch):
    captured = {}

    async def fake_uid(_db, _chat_id):
        return 99

    async def fake_state(_db, _uid):
        return None, {}

    async def fake_source(_db, fallback_uid):
        assert fallback_uid == 99
        return 1

    async def fake_ru(_db, _token, _message, uid=None, state=None, payload=None):
        captured.update(uid=uid, state=state, payload=payload)
        return True

    monkeypatch.setattr(operational_menu, "_uid", fake_uid)
    monkeypatch.setattr(operational_menu.runtime_guard, "_state", fake_state)
    monkeypatch.setattr(operational_menu, "_ru_source_uid", fake_source)
    monkeypatch.setattr(operational_menu, "is_owner", lambda _chat_id: False)
    monkeypatch.setattr(operational_menu.ru_menu, "handle_message", fake_ru)

    handled = asyncio.run(
        operational_menu.handle_message(
            object(),
            "token",
            {"text": "qual o almoço hoje?", "chat": {"id": 555}},
        )
    )

    assert handled is True
    assert captured == {"uid": 1, "state": None, "payload": {}}
