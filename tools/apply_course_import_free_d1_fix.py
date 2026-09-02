from pathlib import Path

DOMAIN_PATH = Path("cloudflare/src/course_domain.py")
TEST_PATH = Path("cloudflare/tests/test_stage4_5_course_import.py")

NEW_BLOCK = r'''async def _bulk_insert_rows(db, sql_prefix, rows, width, *, chunk_rows=None):
    """Executa INSERTs multi-row respeitando o limite de 100 parâmetros do D1."""
    if not rows:
        return
    width = int(width)
    if width < 1:
        raise ValueError("bulk insert width must be positive")

    # D1 aceita no máximo 100 parâmetros vinculados por query. Usamos 96 para
    # manter margem e reduzir o número total de queries por invocação no plano Free.
    safe_chunk_rows = max(1, 96 // width)
    if chunk_rows is None:
        chunk_rows = safe_chunk_rows
    else:
        chunk_rows = max(1, min(int(chunk_rows), safe_chunk_rows))

    for start in range(0, len(rows), int(chunk_rows)):
        chunk = rows[start:start + int(chunk_rows)]
        placeholders = ",".join(
            "(" + ",".join("?" for _ in range(width)) + ")" for _ in chunk
        )
        params = []
        for row in chunk:
            if len(row) != width:
                raise ValueError("bulk insert row width mismatch")
            params.extend(row)
        await db.prepare(sql_prefix + placeholders).bind(*params).run()


async def import_course_plan(db, user_id, plan):
    """Persiste uma importação validada em lotes globais, inclusive no D1 Free."""
    if not isinstance(plan, dict):
        raise ValueError("invalid course import plan")
    mode = str(plan.get("mode") or "").strip()
    if mode not in COURSE_MODES:
        raise ValueError("invalid course mode")
    modules = plan.get("modules") or []
    if not modules:
        raise ValueError("course import requires modules")

    # Valida a estrutura mínima antes de criar qualquer registro.
    for module in modules:
        _clean_title(module.get("title"))
        contents = module.get("contents") or []
        if not contents:
            raise ValueError("imported module has no contents")
        for content in contents:
            _clean_title(content.get("title"))
            kind = str(content.get("kind") or "lesson").strip()
            if kind not in CONTENT_KINDS:
                raise ValueError("invalid content kind")
            for material in content.get("materials") or []:
                _clean_title(material.get("title"))
                material_kind = str(material.get("kind") or "other").strip()
                if material_kind not in MATERIAL_KINDS:
                    raise ValueError("invalid material kind")
            for activity in content.get("activities") or []:
                _clean_title(activity.get("title"))

    course_id = await create_course(
        db,
        user_id,
        _clean_title(plan.get("title")),
        mode=mode,
        description=_clean_optional(plan.get("description")),
    )
    totals = {"modules": 0, "contents": 0, "materials": 0, "activities": 0}

    try:
        # 1) Insere todos os módulos em uma única sequência de lotes.
        module_rows = [
            (
                int(course_id),
                int(module_pos),
                _clean_title(module.get("title")),
                None,
            )
            for module_pos, module in enumerate(modules, 1)
        ]
        await _bulk_insert_rows(
            db,
            "INSERT INTO course_modules(course_id,position,title,description) VALUES ",
            module_rows,
            4,
        )
        totals["modules"] = len(module_rows)

        inserted_modules = await _rows(
            db.prepare(
                "SELECT id,position FROM course_modules WHERE course_id=? ORDER BY position"
            ).bind(int(course_id))
        )
        module_ids = {
            int(_row(row, "position")): int(_row(row, "id"))
            for row in inserted_modules
        }
        if len(module_ids) != len(modules):
            raise RuntimeError("course module mapping is incomplete")

        # 2) Insere conteúdos de todos os módulos globalmente. Isso evita pagar o
        # overhead de uma consulta de mapeamento para cada módulo separadamente.
        content_rows = []
        for module_pos, module in enumerate(modules, 1):
            module_id = module_ids[int(module_pos)]
            for content_pos, content in enumerate(module.get("contents") or [], 1):
                kind = str(content.get("kind") or "lesson").strip()
                content_rows.append((
                    int(module_id),
                    int(content_pos),
                    _clean_title(content.get("title")),
                    kind,
                    _clean_optional(content.get("scheduled_at"), max_len=80),
                    _clean_optional(content.get("notes")),
                ))

        await _bulk_insert_rows(
            db,
            "INSERT INTO course_contents(module_id,position,title,kind,scheduled_at,notes) VALUES ",
            content_rows,
            6,
        )
        totals["contents"] = len(content_rows)

        inserted_contents = await _rows(
            db.prepare(
                "SELECT ct.id,m.position AS module_position,ct.position AS content_position "
                "FROM course_contents ct JOIN course_modules m ON m.id=ct.module_id "
                "WHERE m.course_id=? ORDER BY m.position,ct.position"
            ).bind(int(course_id))
        )
        content_ids = {
            (
                int(_row(row, "module_position")),
                int(_row(row, "content_position")),
            ): int(_row(row, "id"))
            for row in inserted_contents
        }
        if len(content_ids) != len(content_rows):
            raise RuntimeError("course content mapping is incomplete")

        # 3) Materiais e atividades também são agrupados globalmente.
        material_rows = []
        activity_rows = []
        for module_pos, module in enumerate(modules, 1):
            for content_pos, content in enumerate(module.get("contents") or [], 1):
                content_id = content_ids[(int(module_pos), int(content_pos))]
                for material_pos, material in enumerate(content.get("materials") or [], 1):
                    material_rows.append((
                        int(content_id),
                        int(material_pos),
                        _clean_title(material.get("title")),
                        str(material.get("kind") or "other").strip(),
                        _clean_optional(material.get("reference"), max_len=4000),
                    ))
                for activity_pos, activity in enumerate(content.get("activities") or [], 1):
                    activity_rows.append((
                        int(content_id),
                        int(activity_pos),
                        _clean_title(activity.get("title")),
                        _clean_optional(activity.get("notes")),
                    ))

        await _bulk_insert_rows(
            db,
            "INSERT INTO course_materials(content_id,position,title,kind,reference) VALUES ",
            material_rows,
            5,
        )
        await _bulk_insert_rows(
            db,
            "INSERT INTO course_activities(content_id,position,title,notes) VALUES ",
            activity_rows,
            4,
        )
        totals["materials"] = len(material_rows)
        totals["activities"] = len(activity_rows)

        await _event(db, course_id, "course_imported", detail=totals)
        return course_id
    except Exception:
        await db.prepare("DELETE FROM courses WHERE id=? AND user_id=?").bind(
            int(course_id), int(user_id)
        ).run()
        raise
'''

domain = DOMAIN_PATH.read_text(encoding="utf-8")
marker = "async def _bulk_insert_rows(db, sql_prefix, rows, width, *, chunk_rows=12):"
start = domain.index(marker)
DOMAIN_PATH.write_text(domain[:start] + NEW_BLOCK + "\n", encoding="utf-8")

tests = TEST_PATH.read_text(encoding="utf-8")
old = 'assert calls["prepare"] < 120'
if old not in tests:
    raise RuntimeError("expected prepare-count assertion not found")
tests = tests.replace(
    old,
    'assert calls["prepare"] < 50  # D1 Free: máximo de 50 queries por invocação',
    1,
)
TEST_PATH.write_text(tests, encoding="utf-8")
