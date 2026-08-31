import json
from pathlib import Path

import temporal_language


CORPUS = json.loads(
    (Path(__file__).parent / "fixtures" / "stage1_relative_time_corpus.json").read_text(encoding="utf-8")
)


def test_relative_alert_corpus():
    for case in CORPUS["relative_alerts"]:
        result = temporal_language.classify_quick_time_intent(case["text"])
        assert result == {"kind": "relative_alert", "delay_seconds": case["seconds"]}, case["text"]


def test_timer_corpus():
    for case in CORPUS["timers"]:
        result = temporal_language.classify_quick_time_intent(case["text"])
        assert result == {"kind": "timer", "delay_seconds": case["seconds"]}, case["text"]


def test_relative_time_false_positives_do_not_become_quick_actions():
    for text in CORPUS["false_positives"]:
        assert temporal_language.classify_quick_time_intent(text)["kind"] is None, text
