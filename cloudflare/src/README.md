# Mapa de módulos — `cloudflare/src`

Este diretório contém o runtime de produção do Butler e também algumas camadas preservadas de experimentos anteriores.

Legenda:

- **ATIVO/DIRETO** — importado por `entry.py` ou `worker.py`;
- **ATIVO/TRANSITIVO** — chamado por um módulo ativo;
- **BASE** — núcleo legado do Worker ainda usado como fallback/fonte de funções;
- **PRESERVADO** — existe para testes, referência ou evolução futura, mas não é parte central do dispatcher atual.

> Em dúvida, confira `entry.py`. Presença no repositório não significa presença no fluxo de produção.

## Entrypoint e infraestrutura

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `worker.py` | ATIVO/DIRETO | entrypoint do Wrangler; sincroniza Durable Objects e delega ao dispatcher |
| `entry.py` | ATIVO/DIRETO | HTTP, `/health`, webhook, ordem de handlers e cron |
| `app.py` | BASE | núcleo-base: D1, estados, menus-base, operações e scheduler legado |
| `settings.py` | ATIVO/TRANSITIVO | constantes do deploy pessoal, timezone e horários de resumos |
| `telegram_api.py` | ATIVO/TRANSITIVO | Bot API, callback, arquivo e verificação de entrega |
| `scheduler_runtime.py` | ATIVO/DIRETO | isola subsistemas agendados para um erro não bloquear os demais |
| `runtime_schema.py` | PRESERVADO/HELPER | helper de schema; não é bootstrap automático atual |
| `maintenance.py` | ATIVO/TRANSITIVO | manutenção acionada pelo scheduler de lembretes |
| `performance_patch.py` | ATIVO/DIRETO | otimiza `app.ensure_user` para usuário já conhecido |

## Dispatcher operacional e navegação

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `core_fast_path.py` | ATIVO/DIRETO | detecta ações operacionais claras antes de fallbacks amplos |
| `operational_informal_fastpath.py` | ATIVO/TRANSITIVO | tarefas/compromissos informais conservadores |
| `colloquial_reminder_fastpath.py` | ATIVO/TRANSITIVO | linguagem coloquial de lembrete e follow-up de data/hora |
| `operational_menu.py` | ATIVO/DIRETO | menus autoritativos e atalho para metas/tarefas/compromissos |
| `runtime_guard.py` | ATIVO/DIRETO | operações seguras de tarefa/rotina e perfil genérico |
| `ux_bugfixes.py` | ATIVO/DIRETO | navegação global/cancelamento e correções de UX |
| `production_usability_patch.py` | ATIVO/DIRETO | Ler/Ver Depois, follow-ups e ajustes de menus-base |
| `start_reset.py` | ATIVO/DIRETO | reset seguro no `/start` |
| `reference_patch.py` | ATIVO/DIRETO | referências curtas a entidades/ações recentes |
| `conversation_layer.py` | ATIVO/DIRETO | contexto operacional em `natural_events`, agenda inteligente e callbacks |
| `quality_patch.py` | ATIVO/DIRETO | melhorias de rotina/mercado e patches históricos de scheduler |
| `companion_safe_fallback.py` | ATIVO/DIRETO | fallback social estreito, especialmente despedidas |

## Tarefas, compromissos e lembretes

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `task_context_patch.py` | ATIVO/DIRETO | listagem, conclusão, adiamento e contexto de tarefas |
| `task_emoji_patch.py` | ATIVO/DIRETO | padronização visual de tarefas |
| `natural_behavior_patch.py` | ATIVO/DIRETO | lembrete simples explícito, recorrência e memória pós-mensagem |
| `reliable_reminders.py` | ATIVO/DIRETO | autoridade temporal de tarefas, compromissos e lembretes simples |
| `reminder_policy.py` | ATIVO/DIRETO | desliga item scheduler antigo da `conversation_layer` |
| `scheduled_delivery_guard.py` | ATIVO/DIRETO | exige confirmação real do Telegram antes de aceitar entrega |
| `alert_diagnostics.py` | ATIVO/DIRETO | diagnóstico operacional de alertas |
| `scheduler_patch.py` | ATIVO/DIRETO/COMPAT | patch do resumo legado de `app`; scheduler confiável é separado |
| `reliable_summaries.py` | ATIVO/DIRETO | resumo da manhã e fechamento semanal com idempotência |

## Mercado

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `grocery_phrase_patch.py` | ATIVO/DIRETO | frases informais de falta/compra e atualização da lista |
| `core_actions.py` | ATIVO/TRANSITIVO | gateway reutilizável para gravações simples do Core |

Observação: no comportamento atual, frases claras como `acabou café`, `falta açúcar` e `tô sem detergente` são tratadas como atualização direta da lista. A arquitetura antiga de “sugerir e confirmar” está preservada em outros módulos, mas não governa este fast path.

## Acadêmico, provas e presença

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `academic_intelligence.py` | ATIVO/DIRETO | matérias, consultas acadêmicas, provas e regras auxiliares |
| `academic_polish.py` | ATIVO/DIRETO | refinamentos do comportamento acadêmico |
| `exam_phrase_patch.py` | ATIVO/DIRETO | formas naturais de registrar/consultar provas |
| `exam_cancel_patch.py` | ATIVO/DIRETO | cancelamento seguro dos fluxos de prova |
| `reliable_exam_reminders.py` | ATIVO/TRANSITIVO | política confiável de lembretes de prova |
| `attendance_patch.py` | ATIVO/DIRETO | presença/faltas e integração base |
| `attendance_enhancement.py` | ATIVO/DIRETO | schema/callbacks e extensões de presença |
| `attendance_management.py` | ATIVO/DIRETO | edição/gestão de faltas e limites |
| `attendance_production_fix.py` | ATIVO/DIRETO | UI/dispatch autoritativos e scheduler confiável de aula |
| `attendance_alarm.py` | ATIVO/DIRETO via `worker.py` | Durable Object de eventos rígidos de presença |

## Rotinas e metas

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `routine_integration.py` | ATIVO/DIRETO | rotinas na agenda, checkpoints e lembretes |
| `routine_editing.py` | ATIVO/DIRETO | edição por linguagem/estado |
| `routine_ui_patch.py` | ATIVO/DIRETO | interface especializada de rotina |
| `routine_natural_fastpath.py` | ATIVO/TRANSITIVO | criação explícita de rotina por texto |
| `goal_operational.py` | ATIVO/TRANSITIVO | núcleo operacional de metas |
| `goal_polish.py` | ATIVO/TRANSITIVO | UX/regras complementares de metas |
| `goal_deadline_patch.py` | ATIVO/TRANSITIVO | prazos/metas temporais |
| `goal_routine_bridge.py` | ATIVO/TRANSITIVO | integração rotina ↔ meta |
| `goal_natural_patch.py` | ATIVO/TRANSITIVO | frases naturais de meta |

A família `goal_*` é instalada por `operational_menu.install()`.

## Musculação

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `workout_progress_patch.py` | ATIVO/DIRETO | progresso, carga anterior, conclusão e atualização do treino |
| `protocol_mass_data.py` | ATIVO/TRANSITIVO | plano pessoal estático de 12 semanas e substituições |

Parte do fluxo genérico também permanece em `app.py`/`runtime_guard.py`.

## Alarmes pessoais

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `personal_alarm.py` | ATIVO/DIRETO via `worker.py` | Durable Object para alarmes pessoais pontuais |

## Personalidade

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `personality_variants.py` | ATIVO/DIRETO | variações controladas de tom/sarcasmo com base em contexto real |

## NLU-base usada por operações

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `nlu.py` | ATIVO/TRANSITIVO | parse de datas/horas e interpretação determinística herdada |

A “NLU ampla” está bloqueada no dispatcher atual; funções utilitárias de `nlu.py` continuam sendo usadas.

## Arquitetura preservada de roteamento/contexto

Os arquivos abaixo representam uma arquitetura estruturada que foi desenvolvida/testada, mas hoje não é o centro do dispatcher de produção:

| Arquivo | Status | Papel preservado |
|---|---|---|
| `context_router.py` | PRESERVADO | classificação domínio/tier |
| `intent_parser.py` | PRESERVADO | intenção/alvo/pista temporal |
| `action_policy.py` | PRESERVADO | conversa × ação × sugestão |
| `context_memory.py` | PRESERVADO | memória curta por usuário |
| `context_sync.py` | PRESERVADO | sincronização/invalidação de contexto |
| `compound_router.py` | PRESERVADO | divisão/roteamento de mensagens compostas |
| `add_intent_patch.py` | PRESERVADO | experimento de intenção de adição |
| `suggestion_engine.py` | PRESERVADO | sugestões confirmáveis transversais |
| `study_plan_flow.py` | PRESERVADO/TRANSITIVO DA SUGESTÃO | plano de estudo derivado de provas |

Testes desses módulos continuam úteis para não perder o trabalho, mas não substituem testes do dispatcher de `entry.py`.

## Memória/companion preservados

| Arquivo | Status | Papel preservado |
|---|---|---|
| `deterministic_memory.py` | PRESERVADO | entidades/fatos pessoais estruturados |
| `personal_profile.py` | PRESERVADO | preferências/fatos explícitos |
| `general_memory.py` | PRESERVADO | memória genérica experimental |
| `companion_life_context.py` | PRESERVADO | contexto de vida/sugestões |
| `companion_nlu_v2.py` | PRESERVADO | NLU de companion |
| `companion_language_patch.py` | PRESERVADO | linguagem do companion |
| `conversational_background.py` | PRESERVADO | background conversacional |
| `conversational_companion.py` | PRESERVADO | companion genérico |
| `cultural_background.py` | PRESERVADO | conhecimento cultural/background |
| `language_context.py` | PRESERVADO | normalização usada pela arquitetura antiga |

## Butler Library preservada

| Arquivo | Status | Papel preservado |
|---|---|---|
| `butler_library.py` | PRESERVADO | dispatcher/integração antiga da Library |
| `cooking_library.py` | PRESERVADO | respostas culinárias estruturadas |
| `library_catalog_handler.py` | PRESERVADO | fallback de catálogo |
| `library_context_bridge.py` | PRESERVADO | contexto curto de consultas da Library |
| `library_index.py` | PRESERVADO/TESTADO | índice comum de registros |
| `library_recipe_queries.py` | PRESERVADO | consultas de receita |

### `knowledge/`

Acervo de dados/metadata preservado:

- `books.py` — livros/literatura;
- `brazilian_traditional_foods.py` — cozinha brasileira;
- `cooking.py` — culinária geral;
- `cooking_books.py` — catálogo culinário estruturado;
- `cooking_pasta.py` — massas;
- `games.py` — jogos;
- `library_manifest.py` — manifesto dos acervos;
- `meat_cuts.py` — cortes/preparo de carnes;
- `philosophy.py` — filosofia;
- `pop_culture.py` — filmes/séries/personagens;
- `portuguese_conversation.py` — português informal;
- `__init__.py` — pacote.

O `/health` atual declara o dispatcher genérico da Library como desabilitado.

## Arquivos que parecem duplicados mas têm papéis distintos

- `runtime_schema.py` × `runtime_guard.ensure_runtime_schema`: o primeiro é helper; o segundo é `noop` de compatibilidade;
- `quality_patch` × `reliable_reminders`: a política final de lembretes é `reliable_reminders`;
- `app.MAIN_KB` × `operational_menu.MAIN_KB`: o menu operacional é a referência principal;
- `conversation_layer` × `context_memory`: o primeiro é contexto operacional ativo; o segundo pertence à arquitetura preservada;
- `nlu.py` × `intent_parser.py`: utilitários de data/hora do primeiro seguem ativos; o parser estrutural do segundo não governa o dispatcher atual.

## Regra para novos módulos

Antes de criar outro arquivo, responda:

1. qual módulo é dono desse domínio?
2. por que a mudança não cabe nele?
3. quem vai importar o novo módulo?
4. qual posição ele precisa no dispatcher?
5. qual símbolo ele substitui, se for patch?
6. qual teste demonstra que o caminho de produção o alcança?

Se essas respostas não estiverem claras, provavelmente o projeto não precisa de mais uma camada.
