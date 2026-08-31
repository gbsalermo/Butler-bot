"""Analisador conservador de frases compostas — Etapa 1.5.

Esta versão substitui o roteador histórico que misturava acadêmico, receitas,
memória e pets. Aqui a camada é neutra: segmenta, classifica relações e reconhece
atos operacionais, mas não executa múltiplos CRUDs silenciosamente.
"""

import re

import language_primitives as language
from telegram_api import send_message


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

# Cláusulas causais/condicionais não viram uma segunda ação automaticamente.
CONTEXT_RELATIONS = {"cause", "condition", "concession"}
NON_AUTOMATIC_RELATIONS = CONTEXT_RELATIONS | {"alternative"}


def _normalized(text):
    return language.normalize_text(language.strip_butler(text))


def _strip_leading_temporal(segment):
    """Remove apenas moldura temporal inicial para revelar o verbo principal."""
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
    candidate = _strip_leading_temporal(segment)
    return language.detect_action_families(candidate)


def analyze_compound(text):
    """Retorna estrutura sem efeitos colaterais e sem acessar D1."""
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
            segments.append(
                {
                    "text": piece,
                    "relation": pending_relation,
                    "connector": pending_connector,
                }
            )
        pending_relation = relation["relation"]
        pending_connector = relation["connector"]
        cursor = end

    tail = normalized[cursor:].strip()
    if tail:
        segments.append({"text": tail, "relation": pending_relation, "connector": pending_connector})

    # Sem conector útil não existe estrutura composta para esta camada.
    if len(segments) < 2:
        return {"segments": segments, "action_segments": [], "is_compound_action": False}

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


def preview_text(analysis):
    actions = analysis.get("automatic_actions") or []
    out = ["🧩 Entendi mais de uma ação na mesma mensagem:"]
    for position, segment in enumerate(actions, 1):
        family = _primary_family(segment)
        label = FAMILY_LABELS.get(family, "• ação")
        relation = segment.get("relation")
        relation_text = ""
        if relation:
            relation_text = f" ({RELATION_LABELS.get(relation, relation)})"
        out.append(f"{position}. {label}{relation_text} — {segment['text']}")
    out.append("\nNão registrei tudo de uma vez para não transformar contexto em tarefa por engano. Por enquanto, manda essas ações separadas.")
    return "\n".join(out)


async def handle_message(db, token, message):
    """Preview seguro da primeira fatia da 1.5; não usa D1 nem executa CRUD."""
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if not text or chat_id is None or text.startswith("/"):
        return False

    analysis = analyze_compound(text)
    if not analysis.get("is_compound_action"):
        return False

    await send_message(token, int(chat_id), preview_text(analysis))
    return True
