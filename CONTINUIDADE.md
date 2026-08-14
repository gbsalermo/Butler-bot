# Continuidade do desenvolvimento

## Estado atual

- Desenvolvimento concentrado na `main`.
- Stack local: Python, `python-telegram-bot[job-queue]`, SQLite, `python-dotenv` e `pypdf`.
- Execução atual via polling; próxima grande etapa = preparação/migração para Cloudflare + D1.
- Bot pessoal: `Butler` / `@ButlerSal_BOT`.
- Existe também `src.main_generic`, multiusuário e isolado por `chat_id`.

## Filosofia

O Butler deve parecer um assistente presente, provocativo e útil, não um conjunto de formulários. O menu continua disponível, mas texto natural deve ser o caminho mais confortável para ações comuns. Toda personalidade contextual deve nascer de fatos reais registrados; quando houver ambiguidade, confirmar em vez de inventar.

## 👥 Multiusuário por chat_id

A versão genérica usa um único bot e isola dados por `chat_id`. No rolling local cada chat usa `data/butler_generic_users/<chat_id>.db`; `user_scope.py` seleciona o banco antes de mensagens e callbacks. Na Cloudflare, preservar essa regra e migrar persistência para D1/armazenamento persistente apropriado.

A inicialização por chat agora inclui matérias, tarefas, cotidiano, finanças e eventos de linguagem natural.

## ⚡ Menu principal

- `🌙 Day-off`
- `➕ Adicionar`
- `🗓️ Hoje`
- `🛒 Item faltando`
- `📚 Matérias`
- `🏠 Cotidiano`
- `🏋️ Musculação`

Pendência não é tipo: tarefa vencida e não concluída vira pendência automaticamente.

## 🗓️ Agenda e histórico

`🗓️ Hoje` oferece amanhã, outra data, próximos 7 dias e histórico. `src/history_handlers.py` permite histórico diário e histórico de tarefas, separando pendentes, concluídas e canceladas. Remover tarefa/compromisso arquiva como `cancelado` em vez de apagar.

## 📥 Grade

Aceita PDF com texto pesquisável e `.txt`, sem OCR/Tesseract. Códigos SIGAA são traduzidos em blocos completos (`M23=08–10`, `M45=10–12`, `T23=14–16`, `T2345=14–18`). Correções manuais têm prioridade.

## 🕴️ Personalidade + comportamento

- `personality.py` + `behavior_engine.py` usam adiamentos, atrasos, streaks, faltas e evolução de carga.
- sarcasmo é provocativo sem humilhar;
- emojis aparecem com moderação;
- Day-off/contextos sensíveis desligam cobrança.

`natural_events` registra eventos úteis para personalidade. Ex.: avisos de atraso. A primeira ocorrência não é tratada como padrão; reincidências permitem provocações baseadas no histórico real.

## ☀️ Resumo matinal + semanal

Resumo matinal padrão 07:30 (`BUTLER_MORNING_SUMMARY_TIME`): aulas com horário/local, tarefas, compromissos, academia quando aplicável, mercado e pendências do dia anterior. Não há fechamento automático noturno. Fechamento semanal permanece domingo 20:00 por padrão.

## 🔥 Sequências

`🎯 Metas → 🔥 Sequências` mostra streak atual, recorde, total e últimos 7 dias para inglês, programação, água, alimentação e musculação. Usa `goal_progress`, `routine_logs` e, no Butler pessoal, treinos realmente concluídos.

## 💰 Finanças simples

Arquivos: `finance_store.py` e `finance_handlers.py`.

Escopo propositalmente pequeno:

- entrada/saída;
- categorias;
- relatório mensal;
- comparação simples com mês anterior;
- limites predefinidos e alertas de excesso.

Não adicionar ainda cartões, parcelas, contas bancárias, investimentos ou orçamento complexo. O Butler deixa claro que relatório só é confiável conforme o usuário registra movimentos.

## 🗣️ Integração natural por texto — concluída v1

Arquivos principais:

- `src/natural_language.py`: interpretação determinística de intenção/data/hora;
- `src/natural_handlers.py`: executa ações usando os stores existentes;
- `src/natural_store.py`: eventos comportamentais auxiliares.

### Princípios

1. ação direta quando intenção/alvo são claros;
2. confirmação curta quando existem vários candidatos;
3. nunca inventar presença, compromisso, tarefa, gasto ou treino;
4. datas/horas passadas continuam bloqueadas;
5. linguagem natural não substitui os stores: apenas traduz fala para as mesmas regras de negócio;
6. sem dependência de LLM/API externa nessa etapa, importante para simplicidade do deploy.

### Frases cobertas

Criação:

- `Butler, amanhã tenho dentista às 15h`;
- `sexta tenho reunião 10h`;
- `dentista amanhã 15h`;
- `me lembra de comprar café`;
- `amanhã preciso entregar o relatório às 18h`.

Agenda/pendências:

- `o que tenho amanhã?`;
- `o que tenho daqui a 3 dias?`;
- `como está minha agenda sexta?`;
- `quais tarefas estão atrasadas?`.

Mercado:

- `falta sal, açúcar e café`;
- `bota café na lista de mercado`;
- `o que falta em casa?`;
- `comprei o café` (marca comprado, com confirmação se ambíguo).

Tarefas:

- `já fiz o relatório` / `terminei X` — busca tarefa pendente por similaridade e confirma quando necessário.

Academia:

- `hoje não vou treinar porque estou cansado`;
- `não vai dar pra treinar hoje`.

No Butler pessoal registra falta somente se `Começar os trabalhos` já ativou o protocolo.

Atraso:

- `vou me atrasar para o dentista`;
- `estou atrasado para a reunião`.

O Butler encontra o compromisso, não altera o horário e registra `late_notice`. Reincidência muda o sarcasmo. Se houver mais de um compromisso plausível, pergunta qual.

Finanças:

- `gastei 35 com lanche`;
- `paguei 20 de uber`;
- `recebi 540 de bolsa`;
- `quanto gastei esse mês?` / `quanto sobrou?`.

Categorias financeiras são inferidas somente para casos simples; desconhecido vira `outros`.

### Follow-up natural

Se a pessoa disser `tenho dentista amanhã` sem hora, o Butler mantém o contexto e pergunta apenas o que falta (`15h`). Esse contexto é temporário em `context.user_data`; reinício do processo não deve persistir uma conversa incompleta.

## 🏋️ Treino pessoal

Protocol Mass permanece interno ao Butler pessoal. Linguagem externa usa “treino na academia”. Ele só aparece em resumos e aceita faltas depois de `🚀 Começar os trabalhos`.

## Sequência funcional concluída

1. ✅ personalidade baseada em comportamento real;
2. ✅ resumo matinal automático;
3. ✅ fechamento semanal;
4. ✅ histórico diário/tarefas;
5. ✅ streaks simples;
6. ✅ finanças simples;
7. ✅ integração natural v1.

## Próxima grande etapa

**Preparar produção Cloudflare.** Antes do deploy:

1. revisar o que depende de polling/JobQueue e adaptar para o modelo do Cloudflare;
2. migrar persistência SQLite para D1 sem quebrar isolamento por `chat_id`;
3. definir webhook do Telegram;
4. tratar scheduler/resumos/lembretes com mecanismo compatível com Cloudflare;
5. revisar secrets/env;
6. smoke test do fluxo pessoal e de dois `chat_id` genéricos.

## Pente-fino recomendado antes da migração

Testar manualmente pelo Telegram:

- criação em ordem `amanhã tenho...` e `tenho... amanhã`;
- horários `15h`, `15h30`, `15:30`;
- data passada e horário passado;
- compromisso sem hora + follow-up;
- duas tarefas com nomes parecidos + `já fiz...`;
- dois compromissos parecidos + `vou me atrasar...`;
- mercado adicionar/listar/comprado;
- falta de treino antes e depois de `Começar os trabalhos`;
- gasto/entrada natural;
- isolamento das mesmas frases em dois `chat_id`.

## Regra de continuidade

Ao concluir nova etapa: atualizar este arquivo, atualizar README quando o fluxo público mudar e deixar explícito o próximo passo técnico.
