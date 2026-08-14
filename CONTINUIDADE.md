# Continuidade do desenvolvimento

## Estado atual

- Desenvolvimento concentrado na `main`.
- Stack: Python, `python-telegram-bot[job-queue]`, SQLite, `python-dotenv` e `pypdf`.
- Execução local via polling.
- Bot pessoal: `Butler` / `@ButlerSal_BOT`.
- Prioridade continua sendo funcionalidade e experiência de uso antes de suíte de testes.

## Filosofia

O Butler deve parecer um assistente presente, não um conjunto de formulários. A tela inicial prioriza ações rápidas e recorrentes; módulos menos urgentes ficam em `🏠 Cotidiano`.

## 👥 Multiusuário por chat_id — etapa 0 concluída

A versão genérica é um único Butler para poucas pessoas, mas cada `chat_id` possui dados isolados. No rolling local cada chat usa `data/butler_generic_users/<chat_id>.db`; o registry central existe apenas para o scheduler. Na futura hospedagem Cloudflare, preservar o isolamento por `chat_id` e trocar SQLite local por armazenamento persistente/D1.

## ⚡ Menu principal orientado a ação

Menu principal atual:

- `🌙 Day-off`
- `➕ Adicionar`
- `🗓️ Hoje`
- `🛒 Item faltando`
- `📚 Matérias`
- `🏠 Cotidiano`
- `🏋️ Musculação`

`➕ Adicionar` abre tarefa/compromisso. `🛒 Item faltando` abre adicionar/listar. Tarefas e compromissos ficam em Cotidiano para gerenciamento completo. Pendência não é tipo: é tarefa vencida e não concluída.

## 🗓️ Agenda

`src/assistant_views.py` reúne aulas, tarefas, compromissos, pendências e treino. Ao abrir `🗓️ Hoje`, oferece também:

- `⏭️ Amanhã`;
- `📆 Outra data` (`DD/MM` ou `DD/MM/AAAA`);
- `🗓️ Próximos 7 dias`.

## ⚡ Captura rápida

Tarefa/compromisso: título → Hoje/Outro dia/Sem data → horário → salvar. Datas/horas passadas são rejeitadas. Item faltando aceita um ou vários itens e quantidade opcional via `item | quantidade`.

## 👤 Nome preferido

`src/onboarding.py` registra `chat_id` e `preferred_name`; respostas e lembretes usam o nome quando possível.

## 📥 Importação da grade

Aceita PDF com texto pesquisável e `.txt`. Sem OCR. Códigos SIGAA são traduzidos em blocos de horas completas; correções manuais têm prioridade.

## 🕴️ Personality + Behavior Engine

Arquivos principais:

- `src/personality.py`;
- `src/behavior_engine.py`;
- `src/behavior_handlers.py`;
- `src/context_engine.py`;
- `src/scheduler.py`.

O Butler é competente, provocativo, levemente cínico e claramente torce pelo usuário sem admitir. Sarcasmo contextual nasce de dados reais: adiamentos, atraso, streaks, faltas e evolução de carga. Emojis aparecem com moderação. Day-off e contextos sensíveis desligam cobrança/sarcasmo.

`daily_items.postpone_count` registra adiamentos reais. Rotinas usam `routine_logs`, metas usam `goal_progress`, e Protocol Mass usa sessões/séries existentes.

## ☀️🌙 Resumos automáticos — etapas 2 e 3 concluídas

Novo arquivo: `src/summary_engine.py`.

O scheduler gera três resumos por `chat_id`, sempre respeitando Day-off e o timezone configurado:

### Resumo da manhã

Padrão: `07:30`, configurável por `BUTLER_MORNING_SUMMARY_TIME`.

Inclui:

- aulas do dia com horário/local;
- tarefas e compromissos;
- tarefas já atrasadas;
- treino previsto/manual ou Protocol Mass quando aplicável;
- itens faltando em casa;
- comentário contextual do Butler.

### Fechamento noturno

Padrão: `21:30`, configurável por `BUTLER_NIGHT_SUMMARY_TIME`.

Inclui:

- tarefas concluídas x previstas no dia;
- compromissos previstos;
- rotinas registradas;
- situação do treino/Protocol Mass;
- tarefas que ficaram abertas;
- melhor sequência ativa quando houver;
- comentário contextual conforme o resultado do dia.

### Fechamento semanal

Padrão: domingo às `20:00`.

Configuração:

- `BUTLER_WEEKLY_SUMMARY_TIME=20:00`;
- `BUTLER_WEEKLY_SUMMARY_WEEKDAY=6` (`0=segunda ... 6=domingo`).

Usa os últimos 7 dias e resume:

- tarefas concluídas/previstas;
- compromissos;
- registros de rotinas;
- pendências vencidas ainda abertas;
- estado da semana atual do Protocol Mass no Butler pessoal;
- destaque de constância;
- comentário final conforme o desempenho real.

As chaves de deduplicação incluem `chat_id` + tipo de resumo + data, evitando envio duplicado no tick de 30 segundos.

## 🏋️ Protocol Mass — somente Butler pessoal

- 12 semanas;
- início único por `🚀 Começar os trabalhos`;
- treino do dia;
- falta com motivo;
- substitutos oficiais;
- registro série por série;
- carga/repetições;
- histórico;
- progresso semanal;
- reinício temporário para testes.

## Próxima sequência funcional

1. ✅ personalidade baseada em comportamento real;
2. ✅ resumo diário automático;
3. ✅ resumo noturno/semanal;
4. aprofundar metas com streak/histórico;
5. finanças persistentes;
6. linguagem natural para criar/alterar ações.

## Próximos testes

1. validar resumo matinal com aula/tarefa/mercado cadastrados;
2. validar fechamento noturno com uma tarefa concluída e outra aberta;
3. validar fechamento semanal no horário de teste alterando temporariamente o `.env`;
4. confirmar que Day-off silencia os três resumos;
5. confirmar isolamento dos resumos entre dois `chat_id` na versão genérica.

## Regra de continuidade

Ao concluir nova etapa:

1. atualizar este arquivo;
2. atualizar README quando o fluxo público mudar significativamente;
3. registrar decisões que afetem etapas futuras;
4. deixar explícito o próximo passo técnico.
