from datetime import datetime, timedelta, timezone

import short_context
import temporal_language


def test_context_expires_after_short_window():
    now = datetime(2026, 8, 30, 23, 0, tzinfo=timezone.utc)
    fresh = (now - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    stale = (now - timedelta(minutes=31)).strftime("%Y-%m-%d %H:%M:%S")

    assert short_context.context_is_fresh(fresh, now=now)
    assert not short_context.context_is_fresh(stale, now=now)


def test_reference_opens_context_but_new_creation_is_barrier():
    assert short_context.should_consume_context("conclui essa")
    assert short_context.should_consume_context("muda ela pra sexta")
    assert short_context.should_consume_context("cancela a segunda")
    assert not short_context.should_consume_context("cria uma tarefa revisar calculo")
    assert not short_context.should_consume_context("tenho dentista amanha")
    assert not short_context.should_consume_context("qual meu treino hoje?")


def test_ordinal_uses_candidates_user_actually_saw():
    payload = {
        "kind": "tarefa",
        "id": 41,
        "candidate_ids": [41, 77, 88],
        "history_ids": [41, 30],
    }
    assert short_context.referenced_candidate_id(payload, "conclui a primeira") == 41
    assert short_context.referenced_candidate_id(payload, "conclui a segunda") == 77
    assert short_context.referenced_candidate_id(payload, "cancela a terceira") == 88
    assert short_context.referenced_candidate_id(payload, "muda ela pra sexta") == 41


def test_alternative_only_resolves_when_unambiguous():
    one_other = {"id": 10, "candidate_ids": [10, 20], "history_ids": [10]}
    many_others = {"id": 10, "candidate_ids": [10, 20, 30], "history_ids": [10]}
    assert short_context.referenced_candidate_id(one_other, "nao essa, a outra") == 20
    assert short_context.referenced_candidate_id(many_others, "nao essa, a outra") is None


def test_relative_time_language_prepares_future_quick_alerts():
    assert temporal_language.classify_quick_time_intent(
        "me lembra de desligar o ovo daqui a 5 minutos"
    ) == {"kind": "relative_alert", "delay_seconds": 300}

    assert temporal_language.classify_quick_time_intent(
        "tenho que ligar para alguem daqui a 10 minutos"
    ) == {"kind": "relative_alert", "delay_seconds": 600}

    assert temporal_language.classify_quick_time_intent(
        "me lembra daqui a 1 hora de tirar a roupa do varal"
    ) == {"kind": "relative_alert", "delay_seconds": 3600}


def test_explicit_timer_language_is_separate_from_task_language():
    assert temporal_language.classify_quick_time_intent(
        "cronometra o tempo de 30 minutos pra mim"
    ) == {"kind": "timer", "delay_seconds": 1800}
    assert temporal_language.classify_quick_time_intent(
        "inicia um timer de 45 segundos"
    ) == {"kind": "timer", "delay_seconds": 45}
    assert temporal_language.classify_quick_time_intent(
        "fiquei 30 minutos estudando"
    )["kind"] is None
