# Continuidade do desenvolvimento

## Estado atual

- Desenvolvimento concentrado na `main`.
- Stack: Python, `python-telegram-bot[job-queue]`, SQLite, `python-dotenv` e `pypdf`.
- Execução local via polling; hospedagem planejada em Cloudflare com persistência migrada para D1.
- Bot pessoal: `Butler` / `@ButlerSal_BOT`.
- Prioridade: funcionalidade e experiência de uso antes de suíte de testes ampla.

## Filosofia

O Butler deve parecer um assistente presente, provocativo e útil, não um conjunto de formulários. O menu prioriza ações rápidas; histórico e comportamento devem refletir fatos realmente registrados.

## 👥 Multiusuário por chat_id

A versão genérica usa um único bot e isola dados por `chat_id`. No rolling local cada chat usa `data/butler_generic_users/<chat_id>.db`. Na Cloudflare, manter a mesma regra de identidade e trocar o armazenamento por D1/persistência apropriada.

## ⚡ Menu principal

- `🌙 Day-off`
- `➕ Adicionar`
- `🗓️ Hoje`
- `🛒 Item faltando`
- `📚 Matérias`
- `🏠 Cotidiano`
- `🏋️ Musculação`

Pendência não é tipo próprio: tarefa vencida e não concluída vira pendência automaticamente.

## 🗓️ Agenda e histórico

`src/assistant_views.py` oferece:

- `⏭️ Amanhã`;
- `📆 Outra data`;
- `🗓️ Próximos 7 dias`;
- `📚 Histórico`.

Novo arquivo: `src/history_handlers.py`.

Dentro de Histórico:

- `📖 Histórico diário`: aceita `ontem`, `hoje`, `DD/MM` ou `DD/MM/AAAA` e reconstrói aulas previstas, tarefas, compromissos, rotinas registradas e treino registrado naquele dia;
- `🗂️ Histórico de tarefas`: separa pendentes, concluídas e canceladas.

Aulas históricas são mostradas como **previstas**, nunca como presença confirmada sem registro específico.

### Cancelamento de tarefas

`daily_items` agora possui `cancelled_at`.

`Remover tarefa/compromisso` deixa de apagar fisicamente e passa a arquivar com `status = 'cancelado'`. Isso preserva histórico daqui para frente. Itens apagados antes desta mudança não podem ser reconstruídos.

## ⚡ Captura rápida

Tarefa/compromisso: título → Hoje/Outro dia/Sem data → horário → salvar. Datas/horas passadas são rejeitadas. Item faltando aceita vários itens e quantidade opcional via `item | quantidade`.

## 📥 Importação da grade

Aceita PDF com texto pesquisável e `.txt`, sem OCR. Códigos SIGAA são traduzidos em blocos de horas completas; correções manuais têm prioridade.

## 🕴️ Personality + Behavior Engine

Arquivos principais:

- `src/personality.py`;
- `src/behavior_engine.py`;
- `src/behavior_handlers.py`;
- `src/context_engine.py`;
- `src/scheduler.py`.

Sarcasmo contextual nasce de dados reais: adiamentos, atraso, streaks, faltas e evolução de carga. Emojis aparecem com moderação. Day-off e contextos sensíveis desligam cobrança/sarcasmo.

## 🔥 Sequências simples de metas

Novo arquivo: `src/streak_engine.py`.

Dentro de `🎯 Metas` existe `🔥 Sequências`.

O objetivo é visual e leve, no estilo Duolingo: mostrar progresso sem transformar o Butler em planilha de desempenho.

Categorias acompanhadas por padrão:

- 🇬🇧 Inglês;
- 💻 Programação;
- 💧 Água;
- 🥗 Alimentação;
- 🏋️ Musculação.

Para cada categoria o Butler mostra:

- sequência atual;
- melhor sequência;
- total de dias registrados;
- visão dos últimos 7 dias com `🟩` / `⬜`;
- comentário curto conforme a constância.

Os streaks usam registros reais já existentes:

- `goal_progress` para metas;
- `routine_logs` para rotinas;
- no Butler pessoal, musculação usa dias realmente concluídos do Protocol Mass, evitando registrar o treino duas vezes.

Se o usuário não registrar nada no dia, não conta. O cálculo considera hoje ou ontem como ponto de continuidade para não zerar artificialmente a sequência logo pela manhã antes de o dia acontecer.

## ☀️ Resumo automático da manhã

`src/summary_engine.py` gera resumo matinal por `chat_id`, padrão `07:30` (`BUTLER_MORNING_SUMMARY_TIME`).

Inclui:

- aulas do dia com horário e local;
- tarefas e compromissos;
- treino na academia somente quando aplicável;
- itens faltando;
- resumo do dia anterior quando houver registros relevantes;
- tarefas que ficaram pendentes de ontem.

Não há mais fechamento automático noturno, porque o dia pode continuar até tarde. O balanço do dia anterior é carregado para a manhã seguinte.

## 📊 Fechamento semanal

Continua automático no domingo às `20:00` por padrão:

- `BUTLER_WEEKLY_SUMMARY_TIME=20:00`;
- `BUTLER_WEEKLY_SUMMARY_WEEKDAY=6`.

Resume os últimos 7 dias: tarefas, compromissos, rotinas, pendências e academia quando o protocolo pessoal estiver ativo.

## 🏋️ Treino pessoal

O Protocol Mass continua interno ao Butler pessoal, mas a linguagem para o usuário usa apenas **treino na academia**. O treino só entra em resumos depois de `🚀 Começar os trabalhos`.

## Próxima sequência funcional

1. ✅ personalidade baseada em comportamento real;
2. ✅ resumo diário automático matinal;
3. ✅ fechamento semanal;
4. ✅ histórico diário + histórico de tarefas;
5. ✅ metas com streak simples/visual;
6. finanças persistentes;
7. linguagem natural para criar/alterar ações.

## Próximos testes

1. registrar progresso em uma meta com categoria `inglês`, `programação`, `água` ou `alimentação` e abrir `🎯 Metas → 🔥 Sequências`;
2. cumprir uma rotina dessas categorias e confirmar que o dia também conta no streak;
3. no Butler pessoal, concluir treino e conferir musculação sem registro duplicado manual;
4. validar sequência atual, recorde e últimos 7 dias;
5. confirmar isolamento por `chat_id` na versão genérica;
6. seguir para finanças persistentes.

## Regra de continuidade

Ao concluir nova etapa:

1. atualizar este arquivo;
2. atualizar README quando o fluxo público mudar significativamente;
3. registrar decisões que afetem etapas futuras;
4. deixar explícito o próximo passo técnico.
