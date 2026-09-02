import asyncio

import course_operational


def test_dynamic_course_buttons_accept_telegram_unicode_variants():
    assert course_operational._course_id_from_text("📘\ufe0f\u00a0#7 Curso") == 7
    assert course_operational._course_id_from_text("🗄️\u00a0#8 Arquivado") == 8
    assert course_operational._module_id_from_text("🧩\ufe0f\u00a0#2 Módulo") == 2
    assert course_operational._content_id_from_text("📄\ufe0f\u00a0#31 Aula") == 31


def test_top_level_course_navigation_works_from_nested_state(monkeypatch):
    async def scenario():
        calls = []

        async def fake_clear(db, uid):
            calls.append(("clear", uid))

        async def fake_list(db, token, chat_id, uid, archived=False):
            calls.append(("list", uid, archived))

        monkeypatch.setattr(course_operational.app, "clear_state", fake_clear)
        monkeypatch.setattr(course_operational, "_show_course_list", fake_list)

        handled = await course_operational._handle_state(
            object(), "token", 123, 10, "📚 Meus cursos", "course_modules", {"course_id": 99}
        )
        assert handled is True
        assert calls == [("clear", 10), ("list", 10, False)]

    asyncio.run(scenario())
