# Mapa de módulos — `cloudflare/src`

**Data-base:** 31/08/2026

Este diretório contém o runtime de produção do Butler e componentes preservados de arquiteturas anteriores.

Legenda:

- **ATIVO/DIRETO** — importado por `entry.py` ou `worker.py`;
- **ATIVO/TRANSITIVO** — alcançado por módulo ativo;
- **BASE/COMPAT** — núcleo herdado ainda necessário;
- **PRESERVADO** — referência/evolução futura, fora do dispatcher principal.

> Em dúvida, confira primeiro `../../docs/STATUS_ATUAL.md`, depois `entry.py` e `../../docs/ARCHITECTURE.md`. Existir no diretório não significa estar ativo.

## Entrypoint e infraestrutura

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `worker.py` | ATIVO/DIRETO | entrypoint Wrangler; mantém Durable Objects, rearma alarms após webhook com `ctx.waitUntil(...)` e sincroniza no cron |
| `entry.py` | ATIVO/DIRETO / AUTORIDADE | HTTP, `/health`, `dispatch_message`, `dispatch_callback` e `dispatch_scheduled` |
| `app.py` | BASE/COMPAT | D1, estados guiados, operações-base e scheduler herdado |
| `settings.py` | ATIVO/TRANSITIVO | timezone, proprietário e defaults do deploy |
| `telegram_api.py` | ATIVO/TRANSITIVO | Telegram Bot API e validação de entrega |
| `scheduler_runtime.py` | ATIVO/DIRETO | isolamento dos subsistemas do cron |
| `runtime_schema.py` | PRESERVADO/HELPER | helper histórico; migrations são a fonte formal |
| `maintenance.py` | ATIVO/TRANSITIVO | manutenção usada por schedulers |
| `performance_patch.py` | ATIVO/DIRETO | cache por update para usuário/estado e redução de round-trips D1 no caminho quente |

## Linguagem natural, dispatcher e contexto operacional

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `language_primitives.py` | ATIVO/TRANSITIVO / AUTORIDADE LINGUÍSTICA | famílias de ações, sinais e polaridade; sem D1/Telegram/CRUD |
| `short_context.py` | ATIVO/TRANSITIVO / AUTORIDADE DE CONTEXTO | contexto curto, expiração, histórico, listas posicionais e isolamento por usuário |
| `correction_patch.py` | ATIVO/DIRETO | auto-reparo temporal seguro do item recém-criado/corrigido — Etapa 1.4 |
| `temporal_language.py` | ATIVO/TRANSITIVO | primitivas de tempo relativo usadas pela Etapa 1; não é ainda um timer geral persistente |
| `core_fast_path.py` | ATIVO/DIRETO | gate conservador para ações claras |
| `operational_informal_fastpath.py` | ATIVO/TRANSITIVO | tarefas/compromissos informais usando famílias linguísticas comuns |
| `colloquial_reminder_fastpath.py` | ATIVO/TRANSITIVO / AUTORIDADE DE CRIAÇÃO NATURAL DE LEMBRETE | formulações coloquiais e persistência validada do lembrete |
| `routine_natural_fastpath.py` | ATIVO/TRANSITIVO | criação natural explícita de rotina |
| `operational_menu.py` | ATIVO/DIRETO / AUTORIDADE | `MAIN_KB`, `COTIDIANO_KB`, `ADD_KB` e instalação das metas |
| `runtime_guard.py` | ATIVO/DIRETO | estados guiados e operações seguras |
| `ux_bugfixes.py` | ATIVO/DIRETO | navegação global/cancelamento |
| `production_usability_patch.py` | ATIVO/DIRETO | Ler/Ver Depois e sincronização dos menus-base |
| `start_reset.py` | ATIVO/DIRETO | reset seguro no `/start` |
| `reference_patch.py` | ATIVO/DIRETO | referências curtas a entidades recentes, apoiadas em `short_context` |
| `conversation_layer.py` | ATIVO/DIRETO | agenda/contexto operacional e callbacks de itens; seus helpers antigos de contexto seguem o contrato de `short_context`; não dispara lembretes de `daily_items` |
| `quality_patch.py` | ATIVO/DIRETO | checkpoint inteligente de rotina e formulações específicas de mercado |
| `companion_safe_fallback.py` | ATIVO/DIRETO | despedidas/fallback social estreito |

### Estado da Etapa 1

```text
1.1 auditoria da linguagem        ✅ concluída
1.2 base linguística comum        ✅ concluída
1.3 contexto curto/referências    ✅ concluída
1.4 correção/auto-reparo          🚧 em andamento
```

O runtime não usa `intent_parser.py`/`context_router.py` como NLU global. Reconhecimento linguístico não autoriza escrita por si só.

## Tarefas, compromissos e lembretes

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `task_context_patch.py` | ATIVO/DIRETO | listagem, conclusão, adiamento e contexto de tarefas; grava ordem visível em `short_context` |
| `task_emoji_patch.py` | ATIVO/DIRETO | apresentação visual de tarefas |
| `natural_behavior_patch.py` | ATIVO/DIRETO/COMPAT | recorrência, pós-mensagem e wrappers compatíveis; criação natural simples delega para a autoridade específica |
| `reliable_reminders.py` | ATIVO/DIRETO / AUTORIDADE | política temporal única para tarefas, compromissos e lembretes simples |
| `scheduled_delivery_guard.py` | ATIVO/DIRETO | exige confirmação de entrega em canais críticos |
| `alert_diagnostics.py` | ATIVO/DIRETO | diagnóstico operacional de alertas |
| `scheduler_patch.py` | ATIVO/DIRETO/COMPAT | compatibilidade com scheduler/resumo herdado de `app.py` |
| `reliable_summaries.py` | ATIVO/DIRETO | resumo matinal e fechamento semanal |
| `personal_alarm.py` | ATIVO via `worker.py` | Durable Object persistente de contingência para tarefas, compromissos, lembretes, rotinas e resumos |

`reliable_reminders.py` continua sendo a autoridade de negócio. `PersonalAlarm` é uma linha de despertar/contingência, não uma política concorrente.

`reminder_policy.py` foi removido na Etapa 0 depois que o scheduler duplicado que ele neutralizava deixou de existir.

## Mercado

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `grocery_phrase_patch.py` | ATIVO/DIRETO/TRANSITIVO | frases informais e atualização da lista |
| `core_actions.py` | ATIVO/TRANSITIVO/PRESERVADO | gateway reutilizável de gravações simples do Core |

A política atual trata frases claras como `acabou café`/`tô sem detergente` como atualização direta da lista.

## Acadêmico, provas e presença

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `academic_intelligence.py` | ATIVO/DIRETO | matérias, provas e consultas acadêmicas |
| `academic_polish.py` | ATIVO/DIRETO | refinamentos acadêmicos |
| `exam_phrase_patch.py` | ATIVO/DIRETO/TRANSITIVO | formas naturais de prova |
| `exam_cancel_patch.py` | ATIVO/DIRETO | cancelamento seguro |
| `reliable_exam_reminders.py` | ATIVO/TRANSITIVO | lembretes de prova |
| `attendance_patch.py` | ATIVO/DIRETO | presença/faltas base |
| `attendance_enhancement.py` | ATIVO/DIRETO | callbacks e extensões de presença |
| `attendance_management.py` | ATIVO/DIRETO | gestão de faltas e limites |
| `attendance_production_fix.py` | ATIVO/DIRETO | UI e scheduler confiável de aula |
| `attendance_alarm.py` | ATIVO via `worker.py` | Durable Object específico de presença |

A migration 0003 é a fonte formal do schema de presença. DDL defensivo não pertence mais ao dispatcher geral. A família continua funcional, porém fragmentada; a consolidação pertence à Etapa 2.

## Rotinas e metas

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `routine_integration.py` | ATIVO/DIRETO | agenda, checkpoints e lembretes de rotina |
| `routine_editing.py` | ATIVO/DIRETO | edição |
| `routine_ui_patch.py` | ATIVO/DIRETO | UI especializada |
| `goal_operational.py` | ATIVO/TRANSITIVO / AUTORIDADE | núcleo de metas |
| `goal_polish.py` | ATIVO/TRANSITIVO | UX de metas |
| `goal_deadline_patch.py` | ATIVO/TRANSITIVO | prazos |
| `goal_routine_bridge.py` | ATIVO/TRANSITIVO | rotina ↔ meta |
| `goal_natural_patch.py` | ATIVO/TRANSITIVO | linguagem natural delimitada de metas |

A família `goal_*` é instalada por `operational_menu.install()`.

## Musculação

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `workout_progress_patch.py` | ATIVO/DIRETO | exercícios, cargas, séries, conclusão e evolução |
| `protocol_mass_data.py` | ATIVO/TRANSITIVO | protocolo pessoal de 12 semanas e substituições |

Parte do fluxo genérico permanece em `app.py`/`runtime_guard.py`.

## Ler/Ver Depois

Autoridade: `production_usability_patch.py`.

Categorias visíveis atuais:

```text
📚 Livros
🎬 Filmes
🎓 Cursos
🗂️ Outras
```

`Cursos` aqui é somente categoria de captura. O domínio completo de Cursos/Trilhas continua planejado para a Etapa 4.

Schema formal: migration `0008_later_items.sql`.

## Clima

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `weather_context.py` | ATIVO/TRANSITIVO | comandos, Hoje/Amanhã e integração com agenda |
| `weather_service.py` | ATIVO/TRANSITIVO | Open-Meteo, preferências, dados objetivos e fallback seguro |
| `weather_personality.py` | ATIVO/TRANSITIVO | comentário mais humano/descontraído sem inventar dados meteorológicos |

## Administração

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `admin_diagnostics.py` | ATIVO/DIRETO | status/listagem de usuários para proprietário |
| `admin_announcement_flow.py` | ATIVO/DIRETO | prévia, persistência e callback de confirmação/cancelamento de avisos |

## Alarmes, scheduler e Day-off

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `personal_alarm.py` | ATIVO via `worker.py` | contingência persistente de eventos pessoais |
| `attendance_alarm.py` | ATIVO via `worker.py` | alarmes persistentes de aula/presença |
| `day_off_policy.py` | ATIVO/DIRETO | validade diária/expiração de Day-off |
| `scheduler_runtime.py` | ATIVO/DIRETO | execução isolada por subsistema |

Cron e Durable Objects convergem para os mesmos dispatchers e `notification_log`. A redundância não deve gerar duplicidade.

Detalhes do incidente de 30/08/2026: `../../docs/SCHEDULER_REDUNDANCY.md`.

## Personalidade e NLU utilitária

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `personality_variants.py` | ATIVO/DIRETO | variação controlada de tom |
| `nlu.py` | ATIVO/TRANSITIVO | datas/horas e parsing determinístico herdado |

A NLU ampla não é o roteador central; utilitários determinísticos seguem ativos.

## Arquitetura preservada de linguagem/contexto

| Arquivo | Status | Papel preservado |
|---|---|---|
| `context_router.py` | PRESERVADO | domínio/tier histórico |
| `intent_parser.py` | PRESERVADO | intenção/alvo/tempo histórico |
| `action_policy.py` | PRESERVADO | conversa × ação × sugestão |
| `context_memory.py` | PRESERVADO | arquitetura de memória curta anterior |
| `context_sync.py` | PRESERVADO | sincronização/invalidação histórica |
| `compound_router.py` | PRESERVADO | mensagens compostas; pode servir de referência, não está no dispatcher principal |
| `language_context.py` | PRESERVADO | normalização da arquitetura antiga |
| `suggestion_engine.py` | PRESERVADO | sugestões transversais confirmáveis |
| `study_plan_flow.py` | PRESERVADO | plano derivado de provas |

A Etapa 1 reaproveita conceitos seletivamente, mas não reativa essa pilha como roteador global.

## Memória/companion preservados

```text
deterministic_memory.py
personal_profile.py
general_memory.py
companion_life_context.py
companion_nlu_v2.py
companion_language_patch.py
conversational_background.py
conversational_companion.py
cultural_background.py
```

Todos permanecem **PRESERVADOS** até decisão explícita da Etapa 8.

## Butler Library preservada

```text
butler_library.py
cooking_library.py
library_catalog_handler.py
library_context_bridge.py
library_index.py
library_recipe_queries.py
knowledge/
```

O `/health` declara o dispatcher genérico da Library como desabilitado. Reativação seletiva pertence à Etapa 8.

## Banco

Migrations formais atuais:

```text
0001_initial.sql
0002_app_state.sql
0003_attendance.sql
0004_conversation_context.sql
0005_goal_profiles.sql
0006_weather_preferences.sql
0007_admin_pending_announcements.sql
0008_later_items.sql
```

As subetapas 1.1–1.4 usam estruturas existentes e não adicionaram migration até este snapshot.

## Performance

`performance_patch.py` usa `ContextVar` para cache **somente durante um update**. Helpers de vários módulos compartilham a resolução de usuário/estado para reduzir consultas repetidas.

Não transformar esse cache em estado global persistente sem desenho de invalidação.

Testes relevantes incluem:

```text
test_request_hotpath_performance.py
test_reference_latency_gate.py
```

## Código legado fora deste diretório

A raiz `src/` é runtime antigo polling/SQLite. Está preservada e isolada; correções de produção não devem ser aplicadas ali por padrão.

## Regra para novos módulos

Antes de criar outro arquivo:

1. `../../docs/STATUS_ATUAL.md` permite começar essa frente agora?
2. qual módulo é dono do domínio?
3. por que a mudança não cabe nele?
4. quem importa o novo módulo?
5. qual posição no dispatcher?
6. qual símbolo será substituído, se houver monkeypatch?
7. como esse patch será removido depois?
8. qual teste comprova o caminho real de produção?

Sem respostas claras, não criar outra camada.
