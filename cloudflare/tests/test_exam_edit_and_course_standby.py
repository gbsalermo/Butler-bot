from datetime import datetime, timezone

import exam_cancel_patch
import reliable_exam_reminders
import telegram_api


def test_exam_edit_actions_are_exposed():
    flat = [button for row in exam_cancel_patch.ACADEMIC_KB for button in row]
    assert "✏️ Editar prova" in flat
    assert "🚫 Cancelar prova" in flat
    edit = [button for row in exam_cancel_patch.EDIT_KB for button in row]
    assert {"🏷️ Nome", "📚 Matéria", "📅 Data", "⏰ Horário"}.issubset(set(edit))


def test_exam_reminder_recovers_after_nine_am():
    now = datetime(2026, 9, 1, 23, 18, tzinfo=timezone.utc)
    assert reliable_exam_reminders._at_or_after(now, 9, 0) is True
    assert reliable_exam_reminders._at_or_after(now, 23, 30) is False


def test_exam_last_hour_reports_real_remaining_minutes():
    now = datetime(2026, 9, 2, 13, 37, tzinfo=timezone.utc)
    target = datetime(2026, 9, 2, 14, 0, tzinfo=timezone.utc)
    assert reliable_exam_reminders._minutes_until(now, target) == 23


def test_courses_button_hidden_for_non_owner(monkeypatch):
    monkeypatch.setattr(telegram_api, "is_owner", lambda chat_id: False)
    markup = {
        "keyboard": [["🏠 Cotidiano", "📘 Cursos"], ["📖 Manual"], ["🌙 Day-off"]],
        "resize_keyboard": True,
    }
    cleaned = telegram_api._filter_reply_markup(999, markup)
    assert cleaned["keyboard"] == [["🏠 Cotidiano"], ["📖 Manual"], ["🌙 Day-off"]]
    assert markup["keyboard"][0] == ["🏠 Cotidiano", "📘 Cursos"]


def test_courses_button_kept_for_owner(monkeypatch):
    monkeypatch.setattr(telegram_api, "is_owner", lambda chat_id: True)
    markup = {"keyboard": [["📘 Cursos"]], "resize_keyboard": True}
    assert telegram_api._filter_reply_markup(123, markup) == markup
