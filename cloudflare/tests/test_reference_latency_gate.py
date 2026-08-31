import asyncio

import reference_patch


class _NoDB:
    def prepare(self, sql):
        raise AssertionError(f"mensagem irrelevante não deveria tocar D1: {sql}")


def test_unrelated_message_does_not_query_reference_context():
    async def scenario():
        return await reference_patch.handle_reference(
            _NoDB(),
            "token",
            {"chat": {"id": 123}, "text": "qual meu treino hoje?"},
        )

    assert asyncio.run(scenario()) is False


def test_unrelated_plain_conversation_does_not_query_reference_context():
    async def scenario():
        return await reference_patch.handle_reference(
            _NoDB(),
            "token",
            {"chat": {"id": 123}, "text": "hoje foi um dia puxado"},
        )

    assert asyncio.run(scenario()) is False


def test_reference_actions_still_pass_lexical_gate():
    assert reference_patch._needs_reference_runtime("muda ela pra sexta")
    assert reference_patch._needs_reference_runtime("conclui a segunda")
    assert reference_patch._needs_reference_runtime("cancela aquela de amanhã")
    assert reference_patch._needs_reference_runtime("essa não, a outra")


def test_non_reference_creation_is_rejected_before_d1():
    assert not reference_patch._needs_reference_runtime("cria uma tarefa revisar cálculo amanhã")
    assert not reference_patch._needs_reference_runtime("me lembra amanhã às 10 de comprar café")
    assert not reference_patch._needs_reference_runtime("tenho dentista amanhã às 15h")
