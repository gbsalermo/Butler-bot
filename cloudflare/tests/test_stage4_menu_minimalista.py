import academic_intelligence
import app
import course_operational
import exam_cancel_patch
import operational_menu
import production_usability_patch
import runtime_guard
import telegram_api


def _flat(rows):
    return [button for row in rows for button in row]


def test_main_menu_is_the_approved_minimalist_layout():
    assert operational_menu.MAIN_KB == [
        ["➕ Adicionar", "🗓️ Hoje"],
        ["🎓 Faculdade", "📋 Minha vida"],
        ["🏋️ Treino", "⚙️ Mais"],
        ["🌙 Day-off"],
    ]
    assert operational_menu.MAIN_KB[-1] == ["🌙 Day-off"]


def test_areas_group_features_without_losing_fast_actions():
    assert operational_menu.FACULTY_KB == [
        ["📚 Matérias", "🍽️ RU"],
        ["🧠 Modo Estudo", "📘 Cursos"],
        ["⬅️ Início"],
    ]
    assert operational_menu.MY_LIFE_KB == [
        ["✅ Tarefas", "📅 Compromissos"],
        ["🧘 Rotinas", "🎯 Metas"],
        ["📥 Inbox"],
        ["🛒 Casa", "📌 Interesses"],
        ["⬅️ Início"],
    ]
    assert operational_menu.HOUSE_KB[-1] == ["⬅️ Minha vida"]
    assert operational_menu.MORE_KB == [
        ["👤 Como me chamar", "📖 Manual"],
        ["⬅️ Início"],
    ]


def test_courses_remain_owner_only_in_faculty_menu(monkeypatch):
    markup = {"keyboard": operational_menu.FACULTY_KB, "resize_keyboard": True}

    monkeypatch.setattr(telegram_api, "is_owner", lambda _chat_id: False)
    public = telegram_api._filter_reply_markup(100, markup)
    assert "📘 Cursos" not in _flat(public["keyboard"])
    assert "📚 Matérias" in _flat(public["keyboard"])
    assert "🧠 Modo Estudo" in _flat(public["keyboard"])

    monkeypatch.setattr(telegram_api, "is_owner", lambda _chat_id: True)
    owner = telegram_api._filter_reply_markup(100, markup)
    assert "📘 Cursos" in _flat(owner["keyboard"])


def test_local_domain_back_routes_follow_new_hierarchy():
    assert operational_menu.ACADEMIC_KB[-1] == ["⬅️ Faculdade"]
    assert operational_menu.TASK_KB[-1] == ["⬅️ Minha vida"]
    assert operational_menu.ROUTINE_KB[-1] == ["⬅️ Minha vida"]
    assert operational_menu.GOAL_KB[-1][-1] == "⬅️ Minha vida"
    assert operational_menu.COURSES_KB[-1] == ["⬅️ Faculdade"]
    assert operational_menu.RU_PUBLIC_KB[-1] == ["⬅️ Faculdade"]
    assert production_usability_patch.LATER_KB[-1] == ["⬅️ Minha vida"]


def test_academic_exam_actions_survive_menu_reorganization():
    buttons = set(_flat(operational_menu.ACADEMIC_KB))
    assert {"📝 Adicionar prova", "📋 Provas", "✏️ Editar prova", "🚫 Cancelar prova"}.issubset(buttons)
    assert {"📊 Ver faltas", "⚙️ Limite de faltas", "✏️ Editar limite", "🗑️ Excluir falta"}.issubset(buttons)


def test_install_synchronizes_runtime_navigation():
    operational_menu.install()
    production_usability_patch.install()
    assert app.MAIN_KB == operational_menu.MAIN_KB
    assert app.COTIDIANO_KB == operational_menu.MY_LIFE_KB
    assert app.GROCERY_KB == operational_menu.HOUSE_KB
    assert app.ACADEMIC_KB == operational_menu.ACADEMIC_KB
    assert runtime_guard.TASK_KB == operational_menu.TASK_KB
    assert runtime_guard.ROUTINE_KB == operational_menu.ROUTINE_KB
    assert academic_intelligence.ACADEMIC_KB == operational_menu.ACADEMIC_KB
    assert exam_cancel_patch.ACADEMIC_KB == operational_menu.ACADEMIC_KB
    assert course_operational.COURSES_KB == operational_menu.COURSES_KB


def test_interest_aliases_keep_old_keyboards_working_during_transition():
    assert "📌 Interesses" in production_usability_patch.LATER_ENTRY_TEXTS
    assert "📌 Ler/ver depois" in production_usability_patch.LATER_ENTRY_TEXTS
    assert "⬅️ Minha vida" in production_usability_patch.LATER_ENTRY_TEXTS
    assert "⬅️ Voltar ao cotidiano" in production_usability_patch.LATER_ENTRY_TEXTS
