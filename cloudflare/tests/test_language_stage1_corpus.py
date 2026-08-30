import json
from pathlib import Path

import pytest

from language_primitives import (
    detect_action_families,
    detect_corrections,
    detect_references,
    detect_relations,
    negation_scope,
    normalize_text,
    strip_butler,
)


CORPUS_PATH = Path(__file__).parent / "fixtures" / "language_stage1_corpus.json"
CORPUS = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CORPUS["normalization"], ids=lambda c: c["text"][:45])
def test_language_normalization_contract(case):
    assert normalize_text(strip_butler(case["text"])) == case["normalized"]


@pytest.mark.parametrize("case", CORPUS["actions"], ids=lambda c: c["text"][:45])
def test_action_family_contract(case):
    assert detect_action_families(case["text"]) == case["actions"]


@pytest.mark.parametrize("case", CORPUS["relations"], ids=lambda c: c["text"][:45])
def test_relation_contract(case):
    relations = [item["relation"] for item in detect_relations(case["text"])]
    assert relations == case["relations"]


@pytest.mark.parametrize("case", CORPUS["references"], ids=lambda c: c["text"][:45])
def test_reference_signal_contract(case):
    values = [item["value"] for item in detect_references(case["text"])]
    assert values == case["values"]


@pytest.mark.parametrize("case", CORPUS["corrections"], ids=lambda c: c["text"][:45])
def test_correction_signal_contract(case):
    markers = [item["marker"] for item in detect_corrections(case["text"])]
    assert markers == case["markers"]


@pytest.mark.parametrize("case", CORPUS["negation"], ids=lambda c: c["text"][:45])
def test_negation_scope_contract(case):
    assert negation_scope(case["text"]) == case["scope"]


@pytest.mark.parametrize("text", CORPUS["false_positives"])
def test_non_action_sentences_do_not_gain_operational_action(text):
    assert detect_action_families(text) == []


def test_initial_corpus_has_meaningful_breadth():
    total = sum(len(value) for value in CORPUS.values())
    assert total >= 100
    assert len(CORPUS["actions"]) >= 50
    assert len(CORPUS["relations"]) >= 15
    assert len(CORPUS["false_positives"]) >= 10
