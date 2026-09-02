# Bugfix — prévia grande de importação no Telegram

## Sintoma

Ao importar um curso grande por `.txt`, o arquivo era lido e validado, mas o Butler aparentava não responder.

## Causa

`course_importer.preview_text()` renderizava todos os conteúdos do curso em uma única mensagem. Em cursos grandes, a prévia ultrapassava o limite de mensagem do Telegram. Como `course_operational._send()` não trata essa rejeição como erro visível ao usuário, o fluxo parecia silenciosamente travado.

## Correção

- a prévia agora é resumida;
- mostra curso, tipo, descrição abreviada, módulos e amostra dos primeiros conteúdos;
- mantém o resumo total de módulos, conteúdos, materiais e atividades;
- limita a mensagem a 3500 caracteres, abaixo do limite do Telegram;
- o arquivo/plano completo continua sendo usado quando o usuário confirma a importação;
- nada é persistido antes da confirmação explícita.

## Regressão

`cloudflare/tests/test_course_import_preview_limit.py` cobre uma importação grande e exige prévia abaixo de 4096 caracteres.
