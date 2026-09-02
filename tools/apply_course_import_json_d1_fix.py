from pathlib import Path
import re

DOMAIN = Path('cloudflare/src/course_domain.py')
STAGE = Path('cloudflare/src/course_stage4.py')
TEST = Path('cloudflare/tests/test_stage4_5_course_import.py')

domain = DOMAIN.read_text(encoding='utf-8')
start = domain.index('async def import_course_plan(db, user_id, plan):')
new_func = '''async def import_course_plan(db, user_id, plan):
    """Persiste uma importação grande com poucas queries no D1 Free.

    Em vez de uma query por lote de linhas, o plano validado é enviado como JSON
    e expandido pelo SQLite/D1 com json_each(). Isso mantém a importação inteira
    muito abaixo do limite de subrequests da invocação do Worker.
    """
    if not isinstance(plan, dict):
        raise ValueError("invalid course import plan")
    mode = str(plan.get("mode") or "").strip()
    if mode not in COURSE_MODES:
        raise ValueError("invalid course mode")
    modules = plan.get("modules") or []
    if not modules:
        raise ValueError("course import requires modules")

    normalized_modules = []
    totals = {"modules": 0, "contents": 0, "materials": 0, "activities": 0}
    for module in modules:
        contents = module.get("contents") or []
        if not contents:
            raise ValueError("imported module has no contents")
        normalized_contents = []
        for content in contents:
            kind = str(content.get("kind") or "lesson").strip()
            if kind not in CONTENT_KINDS:
                raise ValueError("invalid content kind")
            normalized_materials = []
            for material in content.get("materials") or []:
                material_kind = str(material.get("kind") or "other").strip()
                if material_kind not in MATERIAL_KINDS:
                    raise ValueError("invalid material kind")
                normalized_materials.append({
                    "title": _clean_title(material.get("title")),
                    "kind": material_kind,
                    "reference": _clean_optional(material.get("reference"), max_len=4000),
                })
            normalized_activities = [
                {
                    "title": _clean_title(activity.get("title")),
                    "notes": _clean_optional(activity.get("notes")),
                }
                for activity in (content.get("activities") or [])
            ]
            normalized_contents.append({
                "title": _clean_title(content.get("title")),
                "kind": kind,
                "scheduled_at": _clean_optional(content.get("scheduled_at"), max_len=80),
                "notes": _clean_optional(content.get("notes")),
                "materials": normalized_materials,
                "activities": normalized_activities,
            })
            totals["contents"] += 1
            totals["materials"] += len(normalized_materials)
            totals["activities"] += len(normalized_activities)
        normalized_modules.append({
            "title": _clean_title(module.get("title")),
            "contents": normalized_contents,
        })
    totals["modules"] = len(normalized_modules)

    payload_json = json.dumps(normalized_modules, ensure_ascii=False, separators=(",", ":"))
    course_id = await create_course(
        db,
        user_id,
        _clean_title(plan.get("title")),
        mode=mode,
        description=_clean_optional(plan.get("description")),
    )

    try:
        await db.prepare(
            "INSERT INTO course_modules(course_id,position,title,description) "
            "SELECT ?,CAST(m.key AS INTEGER)+1,json_extract(m.value,'$.title'),NULL "
            "FROM json_each(?) AS m"
        ).bind(int(course_id), payload_json).run()

        await db.prepare(
            "INSERT INTO course_contents(module_id,position,title,kind,scheduled_at,notes) "
            "SELECT cm.id,CAST(c.key AS INTEGER)+1,json_extract(c.value,'$.title'),"
            "COALESCE(json_extract(c.value,'$.kind'),'lesson'),"
            "json_extract(c.value,'$.scheduled_at'),json_extract(c.value,'$.notes') "
            "FROM json_each(?) AS m "
            "JOIN course_modules cm ON cm.course_id=? AND cm.position=CAST(m.key AS INTEGER)+1 "
            "JOIN json_each(m.value,'$.contents') AS c"
        ).bind(payload_json, int(course_id)).run()

        await db.prepare(
            "INSERT INTO course_materials(content_id,position,title,kind,reference) "
            "SELECT ct.id,CAST(mat.key AS INTEGER)+1,json_extract(mat.value,'$.title'),"
            "COALESCE(json_extract(mat.value,'$.kind'),'other'),json_extract(mat.value,'$.reference') "
            "FROM json_each(?) AS m "
            "JOIN course_modules cm ON cm.course_id=? AND cm.position=CAST(m.key AS INTEGER)+1 "
            "JOIN json_each(m.value,'$.contents') AS c "
            "JOIN course_contents ct ON ct.module_id=cm.id AND ct.position=CAST(c.key AS INTEGER)+1 "
            "JOIN json_each(c.value,'$.materials') AS mat"
        ).bind(payload_json, int(course_id)).run()

        await db.prepare(
            "INSERT INTO course_activities(content_id,position,title,notes) "
            "SELECT ct.id,CAST(act.key AS INTEGER)+1,json_extract(act.value,'$.title'),"
            "json_extract(act.value,'$.notes') "
            "FROM json_each(?) AS m "
            "JOIN course_modules cm ON cm.course_id=? AND cm.position=CAST(m.key AS INTEGER)+1 "
            "JOIN json_each(m.value,'$.contents') AS c "
            "JOIN course_contents ct ON ct.module_id=cm.id AND ct.position=CAST(c.key AS INTEGER)+1 "
            "JOIN json_each(c.value,'$.activities') AS act"
        ).bind(payload_json, int(course_id)).run()

        await _event(db, course_id, "course_imported", detail=totals)
        return course_id
    except Exception:
        await db.prepare("DELETE FROM courses WHERE id=? AND user_id=?").bind(
            int(course_id), int(user_id)
        ).run()
        raise
'''
domain = domain[:start] + new_func + '\n'
DOMAIN.write_text(domain, encoding='utf-8')

stage = STAGE.read_text(encoding='utf-8')
old = '''    except Exception as exc:\n        print(f"[course-import] failed type={type(exc).__name__} message={str(exc)[:300]}")\n        await course_operational._send(\n            token,\n            chat_id,\n            "❌ Não consegui concluir a importação. Nada parcial deve ser mantido; você pode tentar confirmar novamente ou cancelar.",\n            [["✅ Confirmar importação"], ["❌ Cancelar ação"]],\n        )\n        return True\n'''
new = '''    except Exception as exc:\n        detail = " ".join(str(exc).split())[:240] or "sem detalhe adicional"\n        print(f"[course-import] failed type={type(exc).__name__} message={detail}")\n        await course_operational._send(\n            token,\n            chat_id,\n            "❌ Não consegui concluir a importação. Nada parcial foi mantido.\\n"\n            f"Diagnóstico: {type(exc).__name__}: {detail}\\n"\n            "A prévia continua disponível para uma nova tentativa ou cancelamento.",\n            [["✅ Confirmar importação"], ["❌ Cancelar ação"]],\n        )\n        return True\n'''
if old not in stage:
    raise SystemExit('exception block not found')
stage = stage.replace(old, new, 1)
STAGE.write_text(stage, encoding='utf-8')

test = TEST.read_text(encoding='utf-8')
test = test.replace('assert calls["prepare"] < 50  # D1 Free: máximo de 50 queries por invocação',
                    'assert calls["prepare"] < 15  # deixa ampla margem para o dispatcher e Telegram no Worker Free')
TEST.write_text(test, encoding='utf-8')
