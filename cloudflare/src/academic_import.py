"""Importação acadêmica confiável para o primeiro cadastro de matérias.

Escopo deliberadamente estreito:
- preserva o modelo atual ``subjects`` + ``subject_sessions``;
- não cria migration nem novos campos;
- só assume o fluxo novo quando o usuário ainda não possui matérias;
- qualquer trecho acadêmico ambíguo bloqueia a persistência do lote inteiro.

O parser é puro. Persistência só acontece após prévia + confirmação explícita.
"""

from __future__ import annotations

import re
import unicodedata
from copy import deepcopy

import app
from telegram_api import send_message


DAYMAP = {
    "2": "segunda-feira",
    "3": "terça-feira",
    "4": "quarta-feira",
    "5": "quinta-feira",
    "6": "sexta-feira",
    "7": "sábado",
}

BLOCKS = {
    "M": {
        "1": ("07:00", "08:00"),
        "2": ("08:00", "09:00"),
        "3": ("09:00", "10:00"),
        "4": ("10:00", "11:00"),
        "5": ("11:00", "12:00"),
    },
    "T": {
        "1": ("13:00", "14:00"),
        "2": ("14:00", "15:00"),
        "3": ("15:00", "16:00"),
        "4": ("16:00", "17:00"),
        "5": ("17:00", "18:00"),
    },
    "N": {
        "1": ("18:00", "19:00"),
        "2": ("19:00", "20:00"),
        "3": ("20:00", "21:00"),
        "4": ("21:00", "22:00"),
    },
}

VALID_CODE_RE = re.compile(r"(?<![A-Za-z0-9])([2-7]{1,6})\s*([MTN])\s*([1-5]{1,5})(?![A-Za-z0-9])", re.I)
CODE_LIKE_RE = re.compile(r"(?<![A-Za-z0-9])([0-9]{1,6})\s*([MTN])\s*([0-9]{1,6})(?![A-Za-z0-9])", re.I)

_HEADER_WORDS = {
    "componente curricular",
    "componente",
    "curricular",
    "local",
    "horario",
    "horários",
    "horario local",
    "turma",
    "situacao",
    "situação",
    "docente",
    "professor",
    "codigo",
    "código",
}

_LOCATION_HINTS = (
    "sala", "pav", "pavilhao", "pavilhão", "lab", "laboratorio", "laboratório",
    "bloco", "auditorio", "auditório", "campus", "cetec", "cotec", "online",
    "remoto", "remota", "virtual",
)

_INSTALLED = False


def _norm(value: str) -> str:
    text = unicodedata.normalize("NFKD", (value or "").lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _clean_line(value: str) -> str:
    value = (value or "").replace("\u00a0", " ")
    value = re.sub(r"[ \t]+", " ", value).strip()
    return value.strip(" |;–—-")


def _is_noise(line: str) -> bool:
    n = _norm(line).strip(" :|-_")
    if not n:
        return True
    if n in {_norm(x) for x in _HEADER_WORDS}:
        return True
    if re.fullmatch(r"pagina\s+\d+(?:\s+de\s+\d+)?", n):
        return True
    if re.fullmatch(r"\d+\s*/\s*\d+", n):
        return True
    if "universidade federal do reconcavo" in n or n == "sigaa":
        return True
    if n.startswith("emitido em ") or n.startswith("gerado em "):
        return True
    return False


def _looks_location(text: str) -> bool:
    n = _norm(text)
    return any(hint in n for hint in _LOCATION_HINTS)


def _valid_subject_name(name: str) -> bool:
    n = _norm(name)
    if len(n) < 3 or n in {_norm(x) for x in _HEADER_WORDS}:
        return False
    if CODE_LIKE_RE.search(name):
        return False
    if re.fullmatch(r"[\d\W_]+", name):
        return False
    return any(ch.isalpha() for ch in name)


def _canonical_code(days: str, period: str, slots: str) -> str:
    return f"{days}{period.upper()}{slots}"


def _validate_code(days: str, period: str, slots: str):
    period = period.upper()
    if not days or any(day not in DAYMAP for day in days) or len(set(days)) != len(days):
        return None, "dias inválidos ou repetidos no código SIGAA"
    allowed = BLOCKS.get(period)
    if not allowed:
        return None, "turno inválido no código SIGAA"
    if not slots or any(slot not in allowed for slot in slots):
        return None, "bloco de horário inválido no código SIGAA"
    values = [int(slot) for slot in slots]
    if len(set(values)) != len(values):
        return None, "blocos de horário repetidos no código SIGAA"
    if values != sorted(values):
        return None, "blocos de horário fora de ordem no código SIGAA"
    if len(values) > 1 and any(b != a + 1 for a, b in zip(values, values[1:])):
        return None, "blocos de horário não contíguos; prefiro revisão manual"
    start = allowed[slots[0]][0]
    end = allowed[slots[-1]][1]
    return (start, end), None


def _split_name_location(before: str, after: str, pending: list[str]):
    before = _clean_line(before)
    after = _clean_line(after)

    # PDFs/TXT exportados com separadores explícitos.
    if "|" in before or "\t" in before:
        pieces = [_clean_line(x) for x in re.split(r"\||\t+", before) if _clean_line(x)]
        if pieces:
            name = pieces[0]
            loc_parts = pieces[1:]
            if after:
                loc_parts.append(after)
            return name, " | ".join(loc_parts) or None

    if before:
        # Nome quebrado em duas linhas: "Introdução à" / "Programação 35M45".
        if len(pending) == 1 and not _looks_location(pending[0]) and not _looks_location(before):
            joined = f"{pending[0]} {before}".strip()
            if len(joined) <= 180:
                return joined, after or None

        # Ordem vertical comum: nome / local / horário.
        if pending and _looks_location(before) and not _looks_location(pending[-1]):
            return pending[-1], " ".join(x for x in (before, after) if x) or None
        return before, after or None

    clean_pending = [x for x in pending if not _is_noise(x)]
    if not clean_pending:
        return None, after or None
    if len(clean_pending) >= 2 and _looks_location(clean_pending[-1]):
        name = " ".join(clean_pending[:-1]).strip()
        location = " ".join(x for x in (clean_pending[-1], after) if x).strip()
        return name, location or None
    return " ".join(clean_pending).strip(), after or None


def _issue(raw: str, reason: str, code: str | None = None):
    return {
        "raw": _clean_line(raw)[:240] or "(trecho vazio)",
        "reason": reason,
        "code": code,
    }


def parse_schedule_report(text: str):
    """Extrai uma grade SIGAA com relatório de confiança.

    ``items`` contém apenas sessões completamente validadas. Se ``issues`` não
    estiver vazio, o fluxo de primeiro acesso não persiste item algum.
    """
    items: list[dict] = []
    issues: list[dict] = []
    pending: list[str] = []
    seen = set()
    last_group: list[int] = []

    lines = [_clean_line(raw) for raw in (text or "").splitlines()]
    for line in lines:
        if _is_noise(line):
            continue

        valid_matches = list(VALID_CODE_RE.finditer(line))
        code_like = list(CODE_LIKE_RE.finditer(line))

        if not valid_matches:
            # Algo com formato de código existe, mas não passou nem pela forma
            # básica. Não silencie: é exatamente o tipo de trecho que precisa de revisão.
            if code_like:
                issues.append(_issue(line, "código de horário SIGAA inválido", code_like[0].group(0)))
                pending.clear()
                last_group = []
                continue

            # Alguns PDFs colocam o local na linha seguinte ao horário.
            if last_group and _looks_location(line):
                for idx in last_group:
                    if not items[idx].get("location"):
                        items[idx]["location"] = line
                last_group = []
                continue

            pending.append(line)
            pending = pending[-3:]
            continue

        # Detecta tokens parecidos que ficaram fora do conjunto aceito na mesma linha.
        valid_spans = {(m.start(), m.end()) for m in valid_matches}
        malformed = [m for m in code_like if (m.start(), m.end()) not in valid_spans]
        if malformed:
            issues.append(_issue(line, "há um código de horário ambíguo na mesma linha", malformed[0].group(0)))
            pending.clear()
            last_group = []
            continue

        first = valid_matches[0]
        last = valid_matches[-1]
        before = line[: first.start()]
        after = line[last.end() :]
        name, location = _split_name_location(before, after, pending)
        raw_context = " | ".join([*pending, line])
        pending.clear()
        last_group = []

        if not name or not _valid_subject_name(name):
            issues.append(_issue(raw_context, "não consegui identificar com segurança o nome da matéria"))
            continue

        local_group: list[int] = []
        group_failed = False
        expanded: list[dict] = []
        for match in valid_matches:
            days, period, slots = match.group(1), match.group(2).upper(), match.group(3)
            bounds, error = _validate_code(days, period, slots)
            code = _canonical_code(days, period, slots)
            if error:
                issues.append(_issue(raw_context, error, code))
                group_failed = True
                break
            start, end = bounds
            for day in days:
                expanded.append({
                    "name": name,
                    "weekday": DAYMAP[day],
                    "start": start,
                    "end": end,
                    "location": location,
                    "code": code,
                })

        if group_failed:
            continue

        for item in expanded:
            key = (
                _norm(item["name"]),
                item["weekday"],
                item["start"],
                item["end"],
                _norm(item.get("location") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            local_group.append(len(items))
            items.append(item)
        last_group = local_group

    # Texto acadêmico restante no fim costuma indicar uma linha quebrada que não
    # encontrou horário. Cabeçalhos/rodapés conhecidos já foram eliminados acima.
    tail = [x for x in pending if not _is_noise(x)]
    if tail and any(any(ch.isalpha() for ch in x) for x in tail):
        issues.append(_issue(" | ".join(tail), "trecho sem código de horário reconhecível"))

    subject_count = len({_norm(item["name"]) for item in items})
    if items and not issues:
        confidence = "high"
    elif items:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "items": items,
        "issues": issues,
        "subject_count": subject_count,
        "session_count": len(items),
        "confidence": confidence,
    }


def _subject_preview(items: list[dict]):
    groups: dict[str, dict] = {}
    order: list[str] = []
    for item in items:
        key = _norm(item["name"])
        if key not in groups:
            groups[key] = {"name": item["name"], "sessions": []}
            order.append(key)
        groups[key]["sessions"].append(item)

    out = []
    for pos, key in enumerate(order, 1):
        group = groups[key]
        out.append(f"{pos}. 📘 {group['name']}")
        for session in group["sessions"]:
            loc = f" — {session['location']}" if session.get("location") else " — local não informado"
            out.append(
                f"   • {session['weekday'].capitalize()} {session['start']}–{session['end']}{loc}"
            )
    return "\n".join(out)


def preview_text(report: dict):
    items = report.get("items") or []
    issues = report.get("issues") or []
    out = [
        "📥 Prévia da sua grade",
        "",
        f"✅ {report.get('subject_count', 0)} matéria(s) / {report.get('session_count', 0)} aula(s) reconhecida(s).",
    ]
    if items:
        out.extend(["", _subject_preview(items)])

    if issues:
        out.extend(["", "⚠️ Não vou cadastrar ainda. Preciso que estes trechos sejam conferidos:"])
        for issue in issues[:8]:
            out.append(f"• {issue['raw']}\n  ↳ {issue['reason']}")
        if len(issues) > 8:
            out.append(f"• ... e mais {len(issues) - 8} trecho(s).")
        out.extend([
            "",
            "Envie outro PDF/TXT corrigido ou use o cadastro manual para o que não estiver claro. Nada foi salvo.",
        ])
    else:
        out.extend([
            "",
            "Tudo bateu com o formato esperado. Confere a prévia e confirme para cadastrar.",
        ])
    return "\n".join(out)


async def _subject_count(db, uid: int) -> int:
    row = await db.prepare("SELECT COUNT(*) n FROM subjects WHERE user_id=?").bind(uid).first()
    try:
        return int(app.rowget(row, "n", 0) or 0)
    except Exception:
        return 0


async def _persist_first_import(db, uid: int, items: list[dict]):
    """Persiste a primeira grade e faz rollback best-effort em erro.

    Como o gate exige zero matérias prévias, remover os ``subject_id`` criados
    nesta tentativa é seguro e não toca histórico anterior do usuário.
    """
    created_ids: list[int] = []
    by_name: dict[str, int] = {}
    try:
        for item in items:
            key = _norm(item["name"])
            sid = by_name.get(key)
            if sid is None:
                await db.prepare("INSERT INTO subjects(user_id,name,active) VALUES(?,?,1)").bind(uid, item["name"]).run()
                row = await db.prepare(
                    "SELECT id FROM subjects WHERE user_id=? AND lower(name)=lower(?) ORDER BY id DESC LIMIT 1"
                ).bind(uid, item["name"]).first()
                sid = int(app.rowget(row, "id"))
                by_name[key] = sid
                created_ids.append(sid)
            await db.prepare(
                "INSERT INTO subject_sessions(subject_id,weekday,start_time,end_time,location) VALUES(?,?,?,?,?)"
            ).bind(
                sid,
                item["weekday"],
                item["start"],
                item["end"],
                item.get("location"),
            ).run()
        return len(by_name), len(items)
    except Exception:
        for sid in reversed(created_ids):
            try:
                await db.prepare("DELETE FROM subjects WHERE id=? AND user_id=?").bind(sid, uid).run()
            except Exception:
                pass
        raise


async def _handle_first_import_state(db, token, chat, uid, state, payload, message):
    if state == "import_schedule":
        # O fluxo endurecido é exclusivo do primeiro cadastro. Usuário com grade
        # existente continua no comportamento anterior, conforme decisão de produto.
        if await _subject_count(db, uid) > 0:
            return False

        doc = message.get("document")
        if not doc:
            await send_message(
                token,
                chat,
                "Estou esperando sua grade em PDF textual/pesquisável ou `.txt`. Imagem/scan não entra direto.",
                reply_markup={"keyboard": app.CANCEL_KB, "resize_keyboard": True},
            )
            return True

        filename = doc.get("file_name") or "arquivo"
        mime = doc.get("mime_type") or ""
        if not (filename.lower().endswith((".pdf", ".txt")) or mime in ("application/pdf", "text/plain")):
            await send_message(token, chat, "Formato aceito: PDF com texto pesquisável ou `.txt`.")
            return True

        try:
            data = await app.get_file_bytes(token, doc["file_id"])
            content = await app.parse_text_file(data, filename)
        except Exception as exc:
            await send_message(
                token,
                chat,
                f"Não consegui ler o arquivo ({type(exc).__name__}). Se for scan/imagem, gere um PDF com texto selecionável.",
            )
            return True

        report = parse_schedule_report(content)
        if report["confidence"] == "low":
            await send_message(
                token,
                chat,
                "📥 Li o arquivo, mas não encontrei uma grade SIGAA com confiança suficiente.\n\n"
                "Use de preferência a tabela `Componente Curricular | Local | Horário` do painel principal do SIGAA e gere PDF com texto selecionável, ou envie `.txt`.\n\nNada foi salvo.",
                reply_markup={"keyboard": app.CANCEL_KB, "resize_keyboard": True},
            )
            return True

        if report["issues"]:
            # Mantém import_schedule para permitir mandar um arquivo corrigido logo em seguida.
            await app.set_state(db, uid, "import_schedule", {})
            await send_message(
                token,
                chat,
                preview_text(report),
                reply_markup={"keyboard": [["❌ Cancelar ação"]], "resize_keyboard": True},
            )
            return True

        await app.set_state(db, uid, "academic_import_confirm", {
            "items": deepcopy(report["items"]),
            "subject_count": report["subject_count"],
            "session_count": report["session_count"],
        })
        await send_message(
            token,
            chat,
            preview_text(report),
            reply_markup={
                "keyboard": [["✅ Confirmar importação"], ["🔁 Enviar outro arquivo", "❌ Cancelar ação"]],
                "resize_keyboard": True,
            },
        )
        return True

    if state != "academic_import_confirm":
        return False

    text = (message.get("text") or "").strip()
    n = _norm(text)
    if text == "🔁 Enviar outro arquivo" or n in {"enviar outro arquivo", "trocar arquivo", "outro arquivo"}:
        await app.set_state(db, uid, "import_schedule", {})
        await send_message(
            token,
            chat,
            "Certo. Envie o novo PDF textual ou `.txt`; a prévia anterior foi descartada.",
            reply_markup={"keyboard": app.CANCEL_KB, "resize_keyboard": True},
        )
        return True

    if text == "❌ Cancelar ação" or n in {"cancelar", "cancelar acao"}:
        await app.clear_state(db, uid)
        await send_message(token, chat, "Importação cancelada. Nada foi cadastrado.", reply_markup={"keyboard": app.ACADEMIC_KB, "resize_keyboard": True})
        return True

    if text != "✅ Confirmar importação" and n not in {"confirmar importacao", "confirmar", "sim"}:
        await send_message(token, chat, "Confira a prévia e use `✅ Confirmar importação`, envie outro arquivo ou cancele.")
        return True

    # Protege duplo envio/concorrência: este fluxo só é válido enquanto a grade está vazia.
    if await _subject_count(db, uid) > 0:
        await app.clear_state(db, uid)
        await send_message(
            token,
            chat,
            "Sua grade já deixou de estar vazia desde a prévia. Não vou importar por cima dela automaticamente.",
            reply_markup={"keyboard": app.ACADEMIC_KB, "resize_keyboard": True},
        )
        return True

    items = payload.get("items") or []
    # Revalidação estrutural antes da escrita.
    if not items:
        await app.clear_state(db, uid)
        await send_message(token, chat, "A prévia perdeu os dados da grade. Envie o arquivo novamente.")
        return True
    for item in items:
        if not _valid_subject_name(item.get("name") or ""):
            await app.clear_state(db, uid)
            await send_message(token, chat, "A prévia contém uma matéria inválida. Envie o arquivo novamente; nada foi salvo.")
            return True
        if item.get("weekday") not in DAYMAP.values():
            await app.clear_state(db, uid)
            await send_message(token, chat, "A prévia contém um dia inválido. Envie o arquivo novamente; nada foi salvo.")
            return True
        if not re.fullmatch(r"\d{2}:\d{2}", item.get("start") or "") or not re.fullmatch(r"\d{2}:\d{2}", item.get("end") or ""):
            await app.clear_state(db, uid)
            await send_message(token, chat, "A prévia contém um horário inválido. Envie o arquivo novamente; nada foi salvo.")
            return True

    try:
        subjects, sessions = await _persist_first_import(db, uid, items)
    except Exception as exc:
        # Mantém a prévia para retry consciente; rollback best-effort remove o que esta tentativa criou.
        await send_message(
            token,
            chat,
            f"Não consegui concluir o cadastro ({type(exc).__name__}). A tentativa foi revertida; a prévia continua disponível.",
        )
        return True

    await app.clear_state(db, uid)
    await send_message(
        token,
        chat,
        f"✅ Grade cadastrada com segurança: {subjects} matéria(s), {sessions} aula(s).\n\n"
        "Agora sua agenda acadêmica já pode usar esses horários.",
        reply_markup={"keyboard": app.ACADEMIC_KB, "resize_keyboard": True},
    )
    return True


def install():
    """Instala o fluxo sobre ``app.handle_state`` sem alterar o modelo acadêmico."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    original_handle_state = app.handle_state

    async def handle_state_with_safe_first_import(db, token, chat, uid, owner, state, payload, message):
        if state in {"import_schedule", "academic_import_confirm"}:
            handled = await _handle_first_import_state(db, token, chat, uid, state, payload or {}, message)
            if handled:
                return True
        return await original_handle_state(db, token, chat, uid, owner, state, payload, message)

    app.handle_state = handle_state_with_safe_first_import
