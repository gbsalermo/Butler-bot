"""Analisador conservador de frases compostas — Etapa 1.5.

A decisão linguística usa texto normalizado; títulos, datas e previews usam o
segmento original quando ele pode ser reconstruído com segurança. Isso evita
perder acentos/capitalização no que será persistido.
"""

import re
from datetime import datetime, timedelta, timezone

import app
import language_primitives as language
import short_context
from colloquial_reminder_fastpath import _clean_title as _clean_reminder_title
from nlu import parse_date, parse_time, validate_future
from operational_informal_fastpath import _clean_title as _clean_operational_title
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
BATCH_STATE = "compound_batch_confirm"
CONFIRM_LABEL = "✅ Registrar tudo"
CANCEL_LABEL = "❌ Cancelar lote"
MAX_BATCH_ACTIONS = 5
BATCH_MAX_AGE_MINUTES = 10

RELATION_LABELS = {
    "addition": "adição",
    "contrast": "contraste",
    "cause": "causa/contexto",
    "consequence": "consequência",
    "condition": "condição",
    "simultaneity": "simultaneidade",
    "temporal": "relação temporal",
    "sequence": "sequência",
    "concession": "concessão",
    "alternative": "alternativa",
}

FAMILY_LABELS = {
    "reminder": "⏰ lembrete",
    "create_task": "✅ tarefa",
    "create_appointment": "📅 compromisso",
    "scheduled_event": "🎓 evento acadêmico",
    "create_routine": "🧘 rotina",
    "planned_activity": "📚 atividade planejada",
    "complete": "✅ conclusão",
    "cancel": "🚫 cancelamento",
    "reschedule": "↪️ reagendamento",
    "timer": "⏱️ temporizador",
}

CONTEXT_RELATIONS = {"cause", "condition", "concession"}
NON_AUTOMATIC_RELATIONS = CONTEXT_RELATIONS | {"alternative"}
BATCH_FAMILIES = {"reminder", "create_task", "create_appointment"}

_CONNECTOR_PATTERNS = {
    "alem disso": r"\bal[eé]m\s+disso\b",
    "porem": r"\bpor[eé]m\b",
    "entao": r"\bent[aã]o\b",
    "tambem": r"\btamb[eé]m\b",
    "ate": r"\bat[eé]\b",
}


def _now():
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


def _row(row, key, default=None):
    if row is None:
        return default
    try:
        return getattr(row, key)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


def _normalized(text):
    return language.normalize_text(language.strip_butler(text))


def _connector_regex(connector):
    if connector in _CONNECTOR_PATTERNS:
        return _CONNECTOR_PATTERNS[connector]
    words = [re.escape(word) for word in str(connector or "").split()]
    return r"\b" + r"\s+".join(words) + r"\b"


def _raw_segments(text, relations):
    """Reconstrói os mesmos blocos sobre o texto original, preservando grafia."""
    raw = language.strip_butler(text).strip()
    if not raw or not relations:
        return []

    parts = []
    cursor = 0
    for relation in relations:
        pattern = _connector_regex(relation.get("connector"))
        match = re.search(pattern, raw[cursor:], flags=re.I)
        if not match:
            return []
        start = cursor + match.start()
        end = cursor + match.end()
        piece = raw[cursor:start].strip(" ,.;:!?\n\t")
        if piece:
            parts.append(piece)
        cursor = end

    tail = raw[cursor:].strip(" ,.;:!?\n\t")
    if tail:
        parts.append(tail)
    return parts


def _strip_leading_temporal(segment):
    value = (segment or "").strip()
    previous = None
    while value and value != previous:
        previous = value
        value = re.sub(
            r"^(?:hoje|amanha|segunda(?: feira)?|terca(?: feira)?|quarta(?: feira)?|quinta(?: feira)?|sexta(?: feira)?|sabado|domingo)\b\s*",
            "",
            value,
        ).strip()
        value = re.sub(r"^(?:de\s+)?(?:manha|tarde|noite)\b\s*", "", value).strip()
        value = re.sub(r"^(?:as\s+)?\d{1,2}(?:\s+\d{2})?\b\s*", "", value).strip()
    return value


def _segment_families(segment):
    return language.detect_action_families(_strip_leading_temporal(segment))


def analyze_compound(text):
    normalized = _normalized(text)
    if not normalized:
        return {"segments": [], "action_segments": [], "is_compound_action": False}

    relations = [r for r in language.detect_relations(text) if r.get("relation") != "limit"]
    segments = []
    cursor = 0
    pending_relation = None
    pending_connector = None

    for relation in relations:
        start, end = int(relation["start"]), int(relation["end"])
        piece = normalized[cursor:start].strip()
        if piece:
            segments.append({"text": piece, "relation": pending_relation, "connector": pending_connector})
        pending_relation = relation["relation"]
        pending_connector = relation["connector"]
        cursor = end

    tail = normalized[cursor:].strip()
    if tail:
        segments.append({"text": tail, "relation": pending_relation, "connector": pending_connector})

    if len(segments) < 2:
        return {"segments": segments, "action_segments": [], "is_compound_action": False}

    raw_parts = _raw_segments(text, relations)
    if len(raw_parts) == len(segments):
        for segment, raw_text in zip(segments, raw_parts):
            segment["raw_text"] = raw_text

    action_segments = []
    for index, segment in enumerate(segments):
        families = _segment_families(segment["text"])
        relation = segment.get("relation")
        contextual = relation in CONTEXT_RELATIONS
        automatic = bool(families) and relation not in NON_AUTOMATIC_RELATIONS
        segment.update(
            {
                "index": index,
                "families": families,
                "contextual": contextual,
                "automatic_candidate": automatic,
            }
        )
        if families:
            action_segments.append(segment)

    automatic_actions = [s for s in action_segments if s["automatic_candidate"]]
    return {
        "segments": segments,
        "action_segments": action_segments,
        "automatic_actions": automatic_actions,
        "is_compound_action": len(automatic_actions) >= 2,
        "requires_choice": any(s.get("relation") == "alternative" for s in action_segments),
        "has_context_clause": any(s.get("contextual") for s in segments),
    }


def is_compound_action(text):
    return bool(analyze_compound(text).get("is_compound_action"))


def _primary_family(segment):
    families = segment.get("families") or []
    return families[0] if families else None


def _segment_source(segment):
    return segment.get("raw_text") or segment.get("text") or ""


def _plan_title(segment_text, family):
    if family == "reminder":
        return _clean_reminder_title(segment_text)
    kind = "tarefa" if family == "create_task" else "compromisso"
    return _clean_operational_title(segment_text, kind)


def build_batch_plan(analysis, *, now=None):
    actions = analysis.get("automatic_actions") or []
    if len(actions) < 2 or len(actions) > MAX_BATCH_ACTIONS:
        return None
    if analysis.get("requires_choice"):
        return None

    current = now or _now()
    today = current.date()
    plans = []
    for segment in actions:
        family = _primary_family(segment)
        if family not in BATCH_FAMILIES:
            return None

        text = _segment_source(segment)
        due = parse_date(text, today)
        tm = parse_time(text)
        if due is None or (family == "reminder" and tm is None):
            return None

        ok, _ = validate_future(due, tm, current.replace(tzinfo=None))
        if not ok:
            return None

        title = _plan_title(text, family).strip()
        if not title:
            return None

        if family == "reminder":
            plans.append(
                {
                    "family": family,
                    "kind": "tarefa",
                    "title": title[:160],
                    "details": "simple_reminder",
                    "due_date": due.isoformat(),
                    "due_time": tm,
                }
            )
        else:
            plans.append(
                {
                    "family": family,
                    "kind": "tarefa" if family == "create_task" else "compromisso",
                    "title": title[:160],
                    "details": None,
                    "due_date": due.isoformat(),
                    "due_time": tm,
                }
            )
    return plans


def _batch_is_fresh(payload, *, now=None):
    prepared_at = (payload or {}).get("prepared_at")
    if not prepared_at:
        return False
    try:
        prepared = datetime.fromisoformat(str(prepared_at))
    except Exception:
        return False
    if prepared.tzinfo is None:
        prepared = prepared.replace(tzinfo=LOCAL_TZ)
    current = now or _now()
    age = (current - prepared.astimezone(LOCAL_TZ)).total_seconds()
    return 0 <= age <= BATCH_MAX_AGE_MINUTES * 60


def _render_plan_line(plan, position):
    label = FAMILY_LABELS.get(plan.get("family"), "• ação")
    when = plan["due_date"][8:10] + "/" + plan["due_date"][5:7]
    if plan.get("due_time"):
        when += f" às {plan['due_time']}"
    return f"{position}. {label} — {plan['title']} — {when}"


def preview_text(analysis, plan=None):
    actions = analysis.get("automatic_actions") or []
    out = ["🧩 Entendi mais de uma ação na mesma mensagem:"]
    if plan:
        out.extend(_render_plan_line(item, position) for position, item in enumerate(plan, 1))
        out.append("\nEstá tudo definido. Confirma que eu registre o lote inteiro?")
        return "\n".join(out)

    for position, segment in enumerate(actions, 1):
        family = _primary_family(segment)
        label = FAMILY_LABELS.get(family, "• ação")
        relation = segment.get("relation")
        relation_text = f" ({RELATION_LABELS.get(relation, relation)})" if relation else ""
        out.append(f"{position}. {label}{relation_text} — {_segment_source(segment)}")
    out.append(
        "\nReconheci mais de uma ação, mas pelo menos uma ainda precisa de informação "
        "ou confirmação específica. Não registrei nada parcialmente; manda essas ações separadas."
    )
    return "\n".join(out)


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(int(chat_id)).first()
    return int(_row(row, "id")) if row else None


async def _confirm_batch(db, token, chat_id):
    uid = await _uid(db, chat_id)
    if uid is None:
        return False
    state, payload = await app.get_state(db, uid)
    if state != BATCH_STATE:
        await send_message(token, chat_id, "Não tenho nenhum lote pendente para registrar.")
        return True
    if not _batch_is_fresh(payload):
        await app.clear_state(db, uid)
        await send_message(
            token,
            chat_id,
            "Esse lote expirou. Manda a mensagem de novo para eu recalcular tudo.",
            reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
        )
        return True

    plans = (payload or {}).get("plans") or []
    if len(plans) < 2 or len(plans) > MAX_BATCH_ACTIONS:
        await app.clear_state(db, uid)
        await send_message(token, chat_id, "Esse lote perdeu a validade. Manda a mensagem de novo.")
        return True

    current = _now()
    for plan in plans:
        try:
            due = datetime.fromisoformat(plan["due_date"]).date()
        except Exception:
            await app.clear_state(db, uid)
            await send_message(token, chat_id, "Esse lote ficou inválido. Manda a mensagem de novo.")
            return True
        ok, _ = validate_future(due, plan.get("due_time"), current.replace(tzinfo=None))
        if not ok:
            await app.clear_state(db, uid)
            await send_message(token, chat_id, "O horário de uma das ações já passou. Manda o lote de novo para eu recalcular.")
            return True

    groups = []
    bind_values = []
    for plan in plans:
        groups.append("(?,?,?,?,?,?,'pendente')")
        bind_values.extend(
            [uid, plan["kind"], plan["title"], plan.get("details"), plan["due_date"], plan.get("due_time")]
        )

    sql = (
        "INSERT INTO daily_items(user_id,kind,title,details,due_date,due_time,status) VALUES "
        + ",".join(groups)
        + " RETURNING id"
    )
    result = await db.prepare(sql).bind(*bind_values).all()
    rows = getattr(result, "results", None) or []
    try:
        rows = list(rows)
    except Exception:
        rows = rows.to_py() if hasattr(rows, "to_py") else []
    ids = [int(_row(row, "id")) for row in rows if _row(row, "id") is not None]

    await app.clear_state(db, uid)
    if ids:
        await short_context.remember_list(db, uid, "daily_item", ids, source="compound_created")

    out = [f"✅ Fechado. Registrei {len(plans)} ações de uma vez:"]
    out.extend(_render_plan_line(item, position) for position, item in enumerate(plans, 1))
    await send_message(
        token,
        chat_id,
        "\n".join(out),
        reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
    )
    return True


async def _cancel_batch(db, token, chat_id):
    uid = await _uid(db, chat_id)
    if uid is not None:
        state, _ = await app.get_state(db, uid)
        if state == BATCH_STATE:
            await app.clear_state(db, uid)
    await send_message(
        token,
        chat_id,
        "Beleza. Não registrei nada desse lote.",
        reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
    )
    return True


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if not text or chat_id is None or text.startswith("/"):
        return False
    chat_id = int(chat_id)

    if text == CONFIRM_LABEL:
        return await _confirm_batch(db, token, chat_id)
    if text == CANCEL_LABEL:
        return await _cancel_batch(db, token, chat_id)

    analysis = analyze_compound(text)
    if not analysis.get("is_compound_action"):
        return False

    plan = build_batch_plan(analysis)
    if plan is None:
        await send_message(token, chat_id, preview_text(analysis))
        return True

    uid = await _uid(db, chat_id)
    if uid is None:
        return False
    await app.set_state(
        db,
        uid,
        BATCH_STATE,
        {"plans": plan, "prepared_at": _now().isoformat()},
    )
    await send_message(
        token,
        chat_id,
        preview_text(analysis, plan),
        reply_markup={"keyboard": [[CONFIRM_LABEL, CANCEL_LABEL]], "resize_keyboard": True},
    )
    return True
