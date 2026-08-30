"""Primitivas determinísticas de linguagem para a Etapa 1 do Butler.

Este módulo NÃO acessa D1, NÃO envia mensagens e NÃO executa ações. Ele apenas
produz sinais linguísticos reaproveitáveis pelos parsers de domínio.

A intenção é reduzir regex/normalizações divergentes sem reativar a NLU histórica
como roteador central.
"""

from __future__ import annotations

import re
import unicodedata


NEGATIONS = ("nao", "nunca", "nem")

# A ordem privilegia expressões compostas antes das formas curtas.
RELATION_PATTERNS = (
    ("addition", r"\balem disso\b", "alem disso"),
    ("contrast", r"\bso que\b", "so que"),
    ("contrast", r"\bporem\b", "porem"),
    ("contrast", r"\bmas\b", "mas"),
    ("cause", r"\bporque\b", "porque"),
    ("cause", r"\bpois\b", "pois"),
    ("consequence", r"\bpor isso\b", "por isso"),
    ("consequence", r"\bentao\b", "entao"),
    ("condition", r"\bcaso\b", "caso"),
    ("condition", r"\bse\b", "se"),
    ("simultaneity", r"\benquanto\b", "enquanto"),
    ("temporal", r"\bquando\b", "quando"),
    ("sequence", r"\bassim que\b", "assim que"),
    ("sequence", r"\bem seguida\b", "em seguida"),
    ("sequence", r"\bdepois\b", "depois"),
    ("sequence", r"\bantes\b", "antes"),
    ("concession", r"\bembora\b", "embora"),
    ("alternative", r"\bou\b", "ou"),
    ("addition", r"\btambem\b", "tambem"),
    ("addition", r"\be\b", "e"),
    ("limit", r"\bate\b", "ate"),
)

REFERENCE_PATTERNS = (
    ("previous", r"\ba anterior\b", "a anterior"),
    ("previous", r"\bo anterior\b", "o anterior"),
    ("previous", r"\ba ultima\b", "a ultima"),
    ("previous", r"\bo ultimo\b", "o ultimo"),
    ("alternative", r"\ba outra\b", "a outra"),
    ("alternative", r"\bo outro\b", "o outro"),
    ("ordinal", r"\ba primeira\b", "a primeira"),
    ("ordinal", r"\bo primeiro\b", "o primeiro"),
    ("ordinal", r"\ba segunda\b", "a segunda"),
    ("ordinal", r"\bo segundo\b", "o segundo"),
    ("deictic", r"\bessa\b", "essa"),
    ("deictic", r"\besse\b", "esse"),
    ("deictic", r"\bisso\b", "isso"),
    ("pronoun", r"\bela\b", "ela"),
    ("pronoun", r"\bele\b", "ele"),
    ("deictic", r"\baquela\b", "aquela"),
    ("deictic", r"\baquele\b", "aquele"),
)

CORRECTION_PATTERNS = (
    ("explicit", r"\bna verdade\b", "na verdade"),
    ("explicit", r"\bquis dizer\b", "quis dizer"),
    ("explicit", r"\bcorrigindo\b", "corrigindo"),
    ("replacement", r"\bou melhor\b", "ou melhor"),
    ("replacement", r"\bmelhor\b", "melhor"),
    ("rejection", r"^nao[, ]+", "nao"),
)

# Famílias de ato linguístico. Elas NÃO escolhem domínio nem autorizam escrita.
# A mesma frase pode produzir mais de uma família; o parser do domínio decide.
ACTION_PATTERNS = (
    (
        "reminder",
        (
            r"^(?:por favor\s+)?(?:(?:nao|nunca|nem)\s+)?(?:me\s+)?(?:lembra|lembre|avisa|avise|recorda|recorde)\b",
            r"^(?:por favor\s+)?(?:(?:nao|nunca|nem)\s+)?(?:deixa|deixe)\s+(?:eu\s+)?(?:esquecer|vacilar)\b",
            r"^(?:por favor\s+)?(?:(?:nao|nunca|nem)\s+)?(?:me\s+)?(?:da|dá)\s+(?:um\s+)?(?:toque|aviso|alo)\b",
            r"^(?:cria|crie|faz|faca|anota|anote|coloca|coloque|adiciona|adicione|bota|marca|marque)\b.*\blembrete\b",
        ),
    ),
    (
        "create_task",
        (
            r"^(?:cria|crie|faz|faca|anota|anote|coloca|coloque|adiciona|adicione|bota|marca|marque)\b.*\btarefa\b",
            r"^(?:eu\s+)?(?:tenho que|tenho de|devo)\b",
            r"^(?:nova tarefa|tarefa)\b.+",
        ),
    ),
    (
        "create_appointment",
        (
            r"^(?:cria|crie|faz|faca|marca|marque|anota|anote|agenda|agende|adiciona|adicione)\b.*\bcompromisso\b",
            r"^(?:eu\s+)?tenho\s+(?:consulta|dentista|reuniao|entrevista|medico|medica)\b",
            r"^(?:eu\s+)?vou ter\s+(?:consulta|dentista|reuniao|entrevista|compromisso)\b",
            r"^(?:consulta|dentista|reuniao|entrevista)\b",
        ),
    ),
    (
        "scheduled_event",
        (
            r"^(?:eu\s+)?tenho\s+aula\b",
            r"^(?:eu\s+)?tenho\s+prova\b",
            r"^(?:eu\s+)?vou ter\s+aula\b",
        ),
    ),
    (
        "complete",
        (
            r"^(?:ja\s+)?(?:fiz|terminei|conclui|finalizei|resolvi)\b",
            r"^(?:ta|esta)\s+(?:feito|feita|pronto|pronta)\b",
            r"^(?:pode\s+)?(?:marcar|marca)\s+como\s+(?:feito|feita|concluido|concluida)\b",
        ),
    ),
    (
        "cancel",
        (
            r"^(?:cancela|cancelar|cancele|remove|remover|remova|exclui|excluir|exclua|apaga|apagar|apague)\b",
            r"^(?:tira|tirar|tire)\b.*\b(?:lista|agenda|tarefa|compromisso|lembrete)\b",
        ),
    ),
    (
        "reschedule",
        (
            r"^(?:adia|adiar|adie|muda|mudar|mude|troca|trocar|troque|passa|passar|passe|joga|jogar|jogue)\b",
            r"^(?:deixa|deixar|deixe)\b.*\b(?:pra|para)\b",
        ),
    ),
    (
        "create_routine",
        (
            r"^(?:cria|crie|faz|faca|adiciona|adicione|cadastra|cadastre)\b.*\brotina\b",
            r"^(?:nova rotina|rotina)\b.+",
        ),
    ),
    (
        "planned_activity",
        (
            r"^(?:eu\s+)?quero\s+(?:estudar|trabalhar|mexer|treinar|fazer|revisar|ler|assistir)\b",
            r"^(?:eu\s+)?pretendo\s+(?:estudar|trabalhar|mexer|treinar|fazer|revisar|ler|assistir)\b",
        ),
    ),
)


def normalize_text(text: str | None, *, keep_temporal: bool = False) -> str:
    """Normaliza caixa, acentos, pontuação e espaços.

    `keep_temporal=True` preserva `:` e `/` para consumidores que ainda precisam
    reconhecer horário/data na representação normalizada.
    """
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    pattern = r"[^a-z0-9:/ ]+" if keep_temporal else r"[^a-z0-9 ]+"
    value = re.sub(pattern, " ", value)
    return re.sub(r"\s+", " ", value).strip()


def strip_butler(text: str | None) -> str:
    """Remove apenas o vocativo inicial `Butler`, sem alterar o restante."""
    return re.sub(r"^\s*butler[,!:\-]?\s*", "", text or "", flags=re.I).strip()


def _normalized_without_butler(text: str | None) -> str:
    return normalize_text(strip_butler(text))


def detect_action_families(text: str | None) -> list[str]:
    """Retorna famílias linguísticas em ordem estável, sem executar nada."""
    normalized = _normalized_without_butler(text)
    if not normalized:
        return []

    found: list[str] = []
    for family, patterns in ACTION_PATTERNS:
        if any(re.search(pattern, normalized) for pattern in patterns):
            found.append(family)
    return found


def has_explicit_action(text: str | None) -> bool:
    return bool(detect_action_families(text))


def detect_relations(text: str | None) -> list[dict]:
    """Identifica conectores/relações em ordem textual.

    Relação é apenas sinal estrutural. `porque` ou `mas`, por si só, jamais
    representam uma segunda ação.
    """
    normalized = _normalized_without_butler(text)
    matches: list[dict] = []
    occupied: list[tuple[int, int]] = []

    # Expressões mais longas vêm primeiro em RELATION_PATTERNS. Evitamos que o
    # `e` de `alem disso`, por exemplo, apareça como relação separada.
    for relation, pattern, connector in RELATION_PATTERNS:
        for match in re.finditer(pattern, normalized):
            span = match.span()
            if any(not (span[1] <= start or span[0] >= end) for start, end in occupied):
                continue
            occupied.append(span)
            matches.append(
                {
                    "relation": relation,
                    "connector": connector,
                    "start": span[0],
                    "end": span[1],
                }
            )

    return sorted(matches, key=lambda item: (item["start"], -(item["end"] - item["start"])))


def detect_references(text: str | None) -> list[dict]:
    normalized = _normalized_without_butler(text)
    found: list[dict] = []
    occupied: list[tuple[int, int]] = []
    for kind, pattern, value in REFERENCE_PATTERNS:
        for match in re.finditer(pattern, normalized):
            span = match.span()
            if any(not (span[1] <= start or span[0] >= end) for start, end in occupied):
                continue
            occupied.append(span)
            found.append({"kind": kind, "value": value, "start": span[0], "end": span[1]})
    return sorted(found, key=lambda item: item["start"])


def detect_corrections(text: str | None) -> list[dict]:
    normalized = _normalized_without_butler(text)
    found: list[dict] = []
    for kind, pattern, marker in CORRECTION_PATTERNS:
        for match in re.finditer(pattern, normalized):
            found.append(
                {
                    "kind": kind,
                    "marker": marker,
                    "start": match.start(),
                    "end": match.end(),
                }
            )
    return sorted(found, key=lambda item: item["start"])


def negation_scope(text: str | None) -> str | None:
    """Estima se a primeira negação atinge a ação ou o conteúdo.

    O retorno é deliberadamente simples: `action`, `target` ou `None`. Casos
    ambíguos devem continuar sendo resolvidos pelo parser de domínio/confirmados.
    """
    normalized = _normalized_without_butler(text)
    if not normalized:
        return None

    action_spans: list[tuple[int, int]] = []
    for _, patterns in ACTION_PATTERNS:
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                action_spans.append(match.span())
    if not action_spans:
        return None

    first_action = min(action_spans, key=lambda span: span[0])
    negations = [m for m in re.finditer(r"\b(?:nao|nunca|nem)\b", normalized)]
    if not negations:
        return None

    first_neg = negations[0]
    if first_neg.start() <= first_action[0]:
        return "action"
    return "target"


def analyze_language(text: str | None) -> dict:
    """Snapshot estrutural sem efeitos colaterais para testes e parsers futuros."""
    return {
        "raw": text or "",
        "normalized": _normalized_without_butler(text),
        "actions": detect_action_families(text),
        "relations": detect_relations(text),
        "references": detect_references(text),
        "corrections": detect_corrections(text),
        "negation_scope": negation_scope(text),
    }
