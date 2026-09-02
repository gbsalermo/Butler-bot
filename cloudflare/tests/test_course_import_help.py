import asyncio

import app
import course_operational
import course_stage4


def test_import_help_explains_ai_conversion_and_format(monkeypatch):
    async def scenario():
        states = []
        sent = []

        async def fake_set_state(db, uid, state, payload):
            states.append((uid, state, payload))

        async def fake_send(token, chat_id, text, reply_markup=None):
            sent.append((text, reply_markup))
            return {"ok": True}

        monkeypatch.setattr(app, "set_state", fake_set_state)
        monkeypatch.setattr(course_operational, "_send", fake_send)

        assert await course_stage4._start_import(object(), "token", 1010, 10) is True
        assert states == [(10, "course_import_wait", {})]
        assert len(sent) == 1

        text, keyboard = sent[0]
        assert "imagem, print, PDF escaneado" in text
        assert "PROMPT PARA PEDIR A UMA IA" in text
        assert "CURSO: Nome do curso" in text
        assert "TIPO: AUTOGERIDO" in text
        assert "[MÓDULO] Nome do módulo" in text
        assert "[CONTEÚDO] Nome do conteúdo | aula" in text
        assert "[MATERIAL] Nome do material | arquivo | referência" in text
        assert "[ATIVIDADE] Nome da atividade | observação" in text
        assert "Não invente nomes, datas, links, materiais ou atividades" in text
        assert "Retorne SOMENTE o texto final no formato Butler" in text
        assert "✅ Confirmar importação" in text
        assert keyboard == [["❌ Cancelar ação"]]
        # Telegram limita mensagens de texto a 4096 caracteres.
        assert len(text) <= 4096

    asyncio.run(scenario())
