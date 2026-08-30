import production_usability_patch as later


def _flatten(rows):
    return [label for row in rows for label in row]


def test_course_is_first_class_later_category():
    assert later.CATEGORY_CHOICES["🎓 Curso"] == "curso"
    assert later.CATEGORY_TITLES["curso"] == "🎓 Cursos"
    assert later.CATEGORY_EMPTY_LABELS["curso"] == "cursos"


def test_course_buttons_are_available_for_add_and_list():
    assert "🎓 Curso" in _flatten(later.CATEGORY_KB)
    assert "🎓 Cursos" in _flatten(later.LATER_KB)


def test_existing_categories_remain_available():
    assert later.CATEGORY_CHOICES["📚 Livro"] == "livro"
    assert later.CATEGORY_CHOICES["🎬 Filme"] == "filme"
    assert later.CATEGORY_CHOICES["🗂️ Outra"] == "outra"
