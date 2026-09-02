import course_importer


def _large_plan():
    modules = []
    for module_index in range(1, 7):
        contents = []
        for content_index in range(1, 34):
            contents.append(
                {
                    "title": f"Conteúdo {module_index}.{content_index} com um nome suficientemente descritivo",
                    "kind": "lesson",
                    "scheduled_at": None,
                    "materials": [
                        {
                            "title": f"Material {module_index}.{content_index}",
                            "kind": "text",
                            "reference": f"material-{module_index}-{content_index}.pdf",
                        }
                    ],
                    "activities": [
                        {
                            "title": f"Atividade {module_index}.{content_index}",
                            "notes": "resolver exercícios",
                        }
                    ],
                }
            )
        modules.append({"title": f"Módulo {module_index}", "contents": contents})
    return {
        "title": "Curso grande para testar limite do Telegram",
        "mode": "self_paced",
        "description": "Descrição longa " * 80,
        "modules": modules,
    }


def test_large_import_preview_stays_within_telegram_message_limit():
    preview = course_importer.preview_text(_large_plan())

    assert len(preview) <= course_importer.MAX_PREVIEW_CHARS
    assert len(preview) < 4096
    assert "Prévia resumida para caber no Telegram" in preview
    assert "6 módulo(s), 198 conteúdo(s), 198 material(is), 198 atividade(s)" in preview
    assert "Nada foi salvo ainda" in preview
