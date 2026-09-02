"""Importação determinística de Cursos — Etapa 4.5.

O parser só aceita uma estrutura explícita e sempre produz uma prévia antes de
qualquer persistência. Quando a entrada é ambígua, falha pedindo correção em vez
de inventar módulos, tipos, datas ou vínculos.
"""
from __future__ import annotations

from datetime import datetime
import io
import re

from pypdf import PdfReader

import course_domain
from telegram_api import get_file_bytes

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TEXT_CHARS = 120_000
MAX_MODULES = 50
MAX_CONTENTS = 300
MAX_CHILDREN_PER_CONTENT = 100
MAX_PREVIEW_CHARS = 3500

MODE_MAP = {
    "autogerido": "self_paced",
    "auto gerido": "self_paced",
    "self_paced": "self_paced",
    "self-paced": "self_paced",
    "ao vivo": "live",
    "live": "live",
}
CONTENT_KIND_MAP = {
    "aula": "lesson",
    "lesson": "lesson",
    "leitura": "reading",
    "reading": "reading",
    "exercicio": "exercise",
    "exercício": "exercise",
    "exercise": "exercise",
    "projeto": "project",
    "project": "project",
    "revisao": "review",
    "revisão": "review",
    "review": "review",
    "outro": "other",
    "other": "other",
}
MATERIAL_KIND_MAP = {
    "link": "link",
    "arquivo": "file",
    "file": "file",
    "video": "video",
    "vídeo": "video",
    "text": "text",
    "texto": "text",
    "outro": "other",
    "other": "other",
}


class CourseImportError(ValueError):
    pass


def _clean(value, *, max_len=180):
    text = " ".join(str(value or "").split()).strip()
    if not text:
        raise CourseImportError("campo obrigatório vazio")
    if len(text) > max_len:
        raise CourseImportError(f"texto excede {max_len} caracteres")
    return text


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _schedule(value):
    raw = str(value or "").strip()
    if not raw or _norm(raw) in {"sem data", "sem data fixa", "-"}:
        return None
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %Hh%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%dT%H:%M")
        except ValueError:
            continue
    raise CourseImportError(
        f"data/horário inválido: {raw}. Use DD/MM/AAAA HH:MM ou deixe vazio"
    )


def _split_payload(line, marker):
    value = line[len(marker):].strip()
    if value.startswith(":"):
        value = value[1:].strip()
    return [part.strip() for part in value.split("|")]


def validate_plan(plan):
    """Valida o plano inteiro antes de qualquer escrita no banco."""
    if not isinstance(plan, dict):
        raise CourseImportError("plano de importação inválido")
    plan["title"] = _clean(plan.get("title"))
    mode = str(plan.get("mode") or "self_paced")
    if mode not in course_domain.COURSE_MODES:
        raise CourseImportError("tipo de curso inválido")
    plan["mode"] = mode
    description = str(plan.get("description") or "").strip()
    plan["description"] = description[:2000] or None

    modules = plan.get("modules") or []
    if not modules:
        raise CourseImportError("adicione pelo menos um [MÓDULO]")
    if len(modules) > MAX_MODULES:
        raise CourseImportError(f"limite de {MAX_MODULES} módulos por importação")

    total_contents = 0
    for module in modules:
        module["title"] = _clean(module.get("title"))
        contents = module.get("contents") or []
        if not contents:
            raise CourseImportError(f"módulo '{module['title']}' não possui [CONTEÚDO]")
        total_contents += len(contents)
        for content in contents:
            content["title"] = _clean(content.get("title"))
            kind = str(content.get("kind") or "lesson")
            if kind not in course_domain.CONTENT_KINDS:
                raise CourseImportError(f"tipo de conteúdo inválido em '{content['title']}'")
            content["kind"] = kind
            content["scheduled_at"] = content.get("scheduled_at") or None
            if len(content.get("materials") or []) > MAX_CHILDREN_PER_CONTENT:
                raise CourseImportError("materiais demais em um único conteúdo")
            if len(content.get("activities") or []) > MAX_CHILDREN_PER_CONTENT:
                raise CourseImportError("atividades demais em um único conteúdo")
            for material in content.get("materials") or []:
                material["title"] = _clean(material.get("title"))
                mkind = str(material.get("kind") or "other")
                if mkind not in course_domain.MATERIAL_KINDS:
                    raise CourseImportError(f"tipo de material inválido em '{material['title']}'")
                material["kind"] = mkind
                ref = str(material.get("reference") or "").strip()
                material["reference"] = ref[:4000] or None
            for activity in content.get("activities") or []:
                activity["title"] = _clean(activity.get("title"))
                notes = str(activity.get("notes") or "").strip()
                activity["notes"] = notes[:2000] or None

    if total_contents > MAX_CONTENTS:
        raise CourseImportError(f"limite de {MAX_CONTENTS} conteúdos por importação")
    return plan


def parse_course_text(text):
    """Converte o formato explícito em plano validado e sem inferências ocultas."""
    raw = str(text or "").replace("\ufeff", "").strip()
    if not raw:
        raise CourseImportError("arquivo vazio")
    if len(raw) > MAX_TEXT_CHARS:
        raise CourseImportError("arquivo textual grande demais para uma importação segura")

    plan = {"title": None, "mode": "self_paced", "description": None, "modules": []}
    current_module = None
    current_content = None
    unknown = []

    for line_no, original in enumerate(raw.splitlines(), 1):
        line = original.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        upper = line.upper()

        if upper.startswith("CURSO:"):
            plan["title"] = line.split(":", 1)[1].strip()
            continue
        if upper.startswith("TIPO:"):
            value = _norm(line.split(":", 1)[1])
            if value not in MODE_MAP:
                raise CourseImportError(
                    f"linha {line_no}: TIPO deve ser AUTOGERIDO ou AO VIVO"
                )
            plan["mode"] = MODE_MAP[value]
            continue
        if upper.startswith("DESCRICAO:") or upper.startswith("DESCRIÇÃO:"):
            plan["description"] = line.split(":", 1)[1].strip() or None
            continue

        module_marker = next(
            (marker for marker in ("[MÓDULO]", "[MODULO]") if upper.startswith(marker)),
            None,
        )
        if module_marker:
            parts = _split_payload(line, line[: len(module_marker)])
            title = parts[0] if parts else ""
            current_module = {"title": title, "contents": []}
            plan["modules"].append(current_module)
            current_content = None
            continue

        content_marker = next(
            (marker for marker in ("[CONTEÚDO]", "[CONTEUDO]") if upper.startswith(marker)),
            None,
        )
        if content_marker:
            if current_module is None:
                raise CourseImportError(f"linha {line_no}: [CONTEÚDO] precisa estar dentro de um [MÓDULO]")
            parts = _split_payload(line, line[: len(content_marker)])
            title = parts[0] if parts else ""
            kind_raw = _norm(parts[1]) if len(parts) > 1 and parts[1] else "aula"
            if kind_raw not in CONTENT_KIND_MAP:
                raise CourseImportError(f"linha {line_no}: tipo de conteúdo desconhecido '{parts[1]}'")
            scheduled_at = _schedule(parts[2]) if len(parts) > 2 else None
            current_content = {
                "title": title,
                "kind": CONTENT_KIND_MAP[kind_raw],
                "scheduled_at": scheduled_at,
                "materials": [],
                "activities": [],
            }
            current_module["contents"].append(current_content)
            continue

        material_marker = "[MATERIAL]"
        if upper.startswith(material_marker):
            if current_content is None:
                raise CourseImportError(f"linha {line_no}: [MATERIAL] precisa vir depois de um [CONTEÚDO]")
            parts = _split_payload(line, line[: len(material_marker)])
            title = parts[0] if parts else ""
            kind_raw = _norm(parts[1]) if len(parts) > 1 and parts[1] else "outro"
            if kind_raw not in MATERIAL_KIND_MAP:
                raise CourseImportError(f"linha {line_no}: tipo de material desconhecido '{parts[1]}'")
            current_content["materials"].append(
                {
                    "title": title,
                    "kind": MATERIAL_KIND_MAP[kind_raw],
                    "reference": parts[2] if len(parts) > 2 else None,
                }
            )
            continue

        activity_marker = next(
            (marker for marker in ("[ATIVIDADE]", "[ACTIVITY]") if upper.startswith(marker)),
            None,
        )
        if activity_marker:
            if current_content is None:
                raise CourseImportError(f"linha {line_no}: [ATIVIDADE] precisa vir depois de um [CONTEÚDO]")
            parts = _split_payload(line, line[: len(activity_marker)])
            current_content["activities"].append(
                {"title": parts[0] if parts else "", "notes": parts[1] if len(parts) > 1 else None}
            )
            continue

        unknown.append((line_no, line[:100]))

    if unknown:
        sample = "; ".join(f"linha {n}: {value}" for n, value in unknown[:3])
        raise CourseImportError(
            "há linhas que não consigo associar com segurança. " + sample
        )
    if plan["mode"] != "live":
        scheduled = [
            content
            for module in plan["modules"]
            for content in module["contents"]
            if content.get("scheduled_at")
        ]
        if scheduled:
            raise CourseImportError("datas fixas em [CONTEÚDO] exigem TIPO: AO VIVO")
    return validate_plan(plan)


def preview_text(plan):
    """Gera prévia curta o bastante para uma única mensagem do Telegram."""
    plan = validate_plan(plan)
    mode = "Autogerido" if plan["mode"] == "self_paced" else "Ao vivo"

    total_contents = sum(len(module.get("contents") or []) for module in plan["modules"])
    total_materials = sum(
        len(content.get("materials") or [])
        for module in plan["modules"]
        for content in module.get("contents") or []
    )
    total_activities = sum(
        len(content.get("activities") or [])
        for module in plan["modules"]
        for content in module.get("contents") or []
    )

    lines = [
        "📥 Prévia da importação",
        f"Curso: {plan['title']}",
        f"Tipo: {mode}",
    ]
    if plan.get("description"):
        description = str(plan["description"])
        if len(description) > 700:
            description = description[:697].rstrip() + "..."
        lines.append(f"Descrição: {description}")

    shown_contents = 0
    truncated = False
    for module in plan["modules"]:
        module_line = f"\n🧩 {module['title']} — {len(module.get('contents') or [])} conteúdo(s)"
        candidate = "\n".join(lines + [module_line])
        if len(candidate) > MAX_PREVIEW_CHARS - 500:
            truncated = True
            break
        lines.append(module_line)

        for content in (module.get("contents") or [])[:3]:
            schedule = (
                f" — {content['scheduled_at'].replace('T', ' ')}"
                if content.get("scheduled_at")
                else ""
            )
            content_line = f"  • {content['title']} ({content['kind']}){schedule}"
            candidate = "\n".join(lines + [content_line])
            if len(candidate) > MAX_PREVIEW_CHARS - 500:
                truncated = True
                break
            lines.append(content_line)
            shown_contents += 1
        if len(module.get("contents") or []) > 3:
            lines.append(f"  … +{len(module['contents']) - 3} conteúdo(s) neste módulo")
        if truncated:
            break

    if shown_contents < total_contents:
        lines.append(
            "\nℹ️ Prévia resumida para caber no Telegram. O arquivo completo será usado na importação."
        )

    lines.append(
        f"\nResumo: {len(plan['modules'])} módulo(s), {total_contents} conteúdo(s), "
        f"{total_materials} material(is), {total_activities} atividade(s)."
    )
    lines.append("Nada foi salvo ainda. Confira o resumo e confirme explicitamente.")
    preview = "\n".join(lines)
    if len(preview) > MAX_PREVIEW_CHARS:
        preview = preview[: MAX_PREVIEW_CHARS - 3].rstrip() + "..."
    return preview


async def document_text(token, document):
    """Lê .txt ou PDF textual. OCR não é usado nesta etapa."""
    if not isinstance(document, dict) or not document.get("file_id"):
        raise CourseImportError("envie um arquivo .txt ou PDF textual")
    filename = str(document.get("file_name") or "arquivo")
    mime = str(document.get("mime_type") or "")
    lower = filename.lower()
    if not (lower.endswith(".txt") or lower.endswith(".pdf") or mime in {"text/plain", "application/pdf"}):
        raise CourseImportError("formato não suportado; use .txt ou PDF textual")
    data = await get_file_bytes(token, document["file_id"])
    if len(data) > MAX_FILE_BYTES:
        raise CourseImportError("arquivo maior que 2 MB; reduza antes de importar")
    if lower.endswith(".pdf") or mime == "application/pdf":
        try:
            reader = PdfReader(io.BytesIO(data))
            if len(reader.pages) > 60:
                raise CourseImportError("PDF com páginas demais para uma importação segura")
            text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        except CourseImportError:
            raise
        except Exception as exc:
            raise CourseImportError("não consegui ler esse PDF textual") from exc
        if not text:
            raise CourseImportError("o PDF não possui texto pesquisável; OCR não é usado nesta importação")
        return text[:MAX_TEXT_CHARS]
    return data.decode("utf-8", errors="replace")[:MAX_TEXT_CHARS]


async def persist_plan(db, user_id, plan):
    """Orquestra apenas funções da autoridade course_domain após validação total."""
    plan = validate_plan(plan)
    course_id = await course_domain.create_course(
        db,
        user_id,
        plan["title"],
        mode=plan["mode"],
        description=plan.get("description"),
    )
    for module_pos, module in enumerate(plan["modules"], 1):
        module_id = await course_domain.add_module(
            db,
            user_id,
            course_id,
            module["title"],
            position=module_pos,
        )
        for content_pos, content in enumerate(module["contents"], 1):
            content_id = await course_domain.add_content(
                db,
                user_id,
                course_id,
                module_id,
                content["title"],
                kind=content["kind"],
                position=content_pos,
                scheduled_at=content.get("scheduled_at"),
            )
            for material_pos, material in enumerate(content.get("materials") or [], 1):
                await course_domain.add_material(
                    db,
                    user_id,
                    course_id,
                    content_id,
                    material["title"],
                    kind=material["kind"],
                    reference=material.get("reference"),
                    position=material_pos,
                )
            for activity_pos, activity in enumerate(content.get("activities") or [], 1):
                await course_domain.add_activity(
                    db,
                    user_id,
                    course_id,
                    content_id,
                    activity["title"],
                    notes=activity.get("notes"),
                    position=activity_pos,
                )
    await course_domain._event(db, course_id, "course_imported")
    return course_id
