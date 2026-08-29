# Mapa de módulos — `cloudflare/src`

Este diretório contém o runtime de produção do Butler e componentes preservados de arquiteturas anteriores.

Legenda:

- **ATIVO/DIRETO** — importado por `entry.py` ou `worker.py`;
- **ATIVO/TRANSITIVO** — alcançado por módulo ativo;
- **BASE/COMPAT** — núcleo herdado ainda necessário;
- **PRESERVADO** — referência/evolução futura, fora do dispatcher principal.

> Em dúvida, confira `entry.py` e `docs/ARCHITECTURE.md`. Existir no diretório não significa estar ativo.

## Entrypoint e infraestrutura

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `worker.py` | ATIVO/DIRETO | entrypoint Wrangler; sincroniza Durable Objects e delega ao dispatcher |
| `entry.py` | ATIVO/DIRETO / AUTORIDADE | HTTP, `/health`, `dispatch_message`, `dispatch_callback` e `dispatch_scheduled` |
| `app.py` | BASE/COMPAT | D1, estados guiados, operações-base e scheduler herdado |
| `settings.py` | ATIVO/TRANSITIVO | timezone, proprietário e defaults do deploy |
| `telegram_api.py` | ATIVO/TRANSITIVO | Telegram Bot API e validação de entrega |
| `scheduler_runtime.py` | ATIVO/DIRETO | isolamento dos subsistemas do cron |
| `runtime_schema.py` | PRESERVADO/HELPER | helper histórico; migrations são a fonte formal |
| `maintenance.py` | ATIVO/TRANSITIVO | manutenção usada por schedulers |
| `performance_patch.py` | ATIVO/DIRETO | otimiza bootstrap de usuários conhecidos |

## Dispatcher, navegação e contexto operacional

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `core_fast_path.py` | ATIVO/DIRETO | gate conservador para ações claras |
| `operational_informal_fastpath.py` | ATIVO/TRANSITIVO | tarefas/compromissos informais |
| `colloquial_reminder_fastpath.py` | ATIVO/TRANSITIVO | formulações coloquiais de lembrete |
| `routine_natural_fastpath.py` | ATIVO/TRANSITIVO | criação natural explícita de rotina |
| `operational_menu.py` | ATIVO/DIRETO / AUTORIDADE | `MAIN_KB`, `COTIDIANO_KB`, `ADD_KB` e instalação das metas |
| `runtime_guard.py` | ATIVO/DIRETO | estados guiados e operações seguras |
| `ux_bugfixes.py` | ATIVO/DIRETO | navegação global/cancelamento |
| `production_usability_patch.py` | ATIVO/DIRETO | Ler/Ver Depois e sincronização dos menus-base |
| `start_reset.py` | ATIVO/DIRETO | reset seguro no `/start` |
| `reference_patch.py` | ATIVO/DIRETO | referências curtas a entidades recentes |
| `conversation_layer.py` | ATIVO/DIRETO | contexto operacional, agenda enriquecida e callbacks de itens; **não dispara lembretes de daily_items** |
| `quality_patch.py` | ATIVO/DIRETO | checkpoint inteligente de rotina e formulações específicas de mercado |
| `companion_safe_fallback.py` | ATIVO/DIRETO | despedidas/fallback social estreito |

### Decisão da Etapa 0

`conversation_layer.py` deixou de manter uma cópia do menu principal. Respostas gerais reutilizam `app.MAIN_KB`, sincronizado por `operational_menu.py`.

## Tarefas, compromissos e lembretes

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `task_context_patch.py` | ATIVO/DIRETO | listagem, conclusão, adiamento e contexto de tarefas |
| `task_emoji_patch.py` | ATIVO/DIRETO | apresentação visual de tarefas |
| `natural_behavior_patch.py` | ATIVO/DIRETO | criação de lembrete explícito, recorrência e pós-mensagem |
| `reliable_reminders.py` | ATIVO/DIRETO / AUTORIDADE | política temporal única para tarefas, compromissos e lembretes simples |
| `scheduled_delivery_guard.py` | ATIVO/DIRETO | exige confirmação de entrega em canais críticos |
| `alert_diagnostics.py` | ATIVO/DIRETO | diagnóstico operacional de alertas |
| `scheduler_patch.py` | ATIVO/DIRETO/COMPAT | compatibilidade com scheduler/resumo herdado de `app.py` |
| `reliable_summaries.py` | ATIVO/DIRETO | resumo matinal e fechamento semanal |

### Consolidação da Etapa 0

Foram removidos:

- `reminder_policy.py` — era apenas um `noop` para neutralizar um scheduler duplicado;
- a política temporal de itens em `quality_patch.py`;
- `_pre_send_item_reminders` em `conversation_layer.py`.

`reliable_reminders.py` passou a ser explicitamente a única autoridade temporal de `daily_items`.

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
| `attendance_enhancement.py` | ATIVO/DIRETO | schema/callbacks e extensões |
| `attendance_management.py` | ATIVO/DIRETO | gestão de faltas e limites |
| `attendance_production_fix.py` | ATIVO/DIRETO | UI e scheduler confiável de aula |
| `attendance_alarm.py` | ATIVO via `worker.py` | Durable Object de presença |

A família continua funcional, porém fragmentada; a consolidação pertence à Etapa 2.

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

## Clima

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `weather_context.py` | ATIVO/TRANSITIVO | comandos, Hoje/Amanhã e integração com agenda |
| `weather_service.py` | ATIVO/TRANSITIVO | Open-Meteo, preferências, formatação e fallback seguro |

## Administração

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `admin_diagnostics.py` | ATIVO/DIRETO | status/listagem de usuários para proprietário |
| `admin_announcement_flow.py` | ATIVO/DIRETO | prévia, persistência e callback de confirmação/cancelamento de avisos |

## Alarmes pessoais e Day-off

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `personal_alarm.py` | ATIVO via `worker.py` | Durable Object para alarmes pessoais |
| `day_off_policy.py` | ATIVO/DIRETO | validade diária/expiração de Day-off |

## Personalidade e NLU utilitária

| Arquivo | Status | Responsabilidade |
|---|---|---|
| `personality_variants.py` | ATIVO/DIRETO | variação controlada de tom |
| `nlu.py` | ATIVO/TRANSITIVO | datas/horas e parsing determinístico herdado |

A NLU ampla não é o roteador central; utilitários de `nlu.py` seguem ativos.

## Arquitetura preservada de linguagem/contexto

| Arquivo | Status | Papel preservado |
|---|---|---|
| `context_router.py` | PRESERVADO | domínio/tier |
| `intent_parser.py` | PRESERVADO | intenção/alvo/tempo |
| `action_policy.py` | PRESERVADO | conversa × ação × sugestão |
| `context_memory.py` | PRESERVADO | memória curta estruturada |
| `context_sync.py` | PRESERVADO | sincronização/invalidação |
| `compound_router.py` | PRESERVADO | mensagens compostas |
| `language_context.py` | PRESERVADO | normalização da arquitetura antiga |
| `suggestion_engine.py` | PRESERVADO | sugestões transversais confirmáveis |
| `study_plan_flow.py` | PRESERVADO | plano derivado de provas |

### Removido na Etapa 0

`add_intent_patch.py` foi apagado após confirmação de que não estava conectado ao runtime.

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

Todos classificados como **PRESERVADO** até decisão explícita da Etapa 7.

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

O `/health` declara o dispatcher genérico da Library como desabilitado.

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

`0008` foi adicionada na Etapa 0 para formalizar o schema que Ler/Ver Depois já criava defensivamente em runtime.

## Código legado fora deste diretório

A raiz `src/` é runtime antigo polling/SQLite. Está preservada e isolada; correções de produção não devem ser aplicadas ali por padrão.

## Regra para novos módulos

Antes de criar outro arquivo:

1. qual módulo é dono do domínio?
2. por que a mudança não cabe nele?
3. quem importa o novo módulo?
4. qual posição no dispatcher?
5. qual símbolo será substituído, se houver monkeypatch?
6. como esse patch será removido depois?
7. qual teste comprova o caminho real de produção?

Sem respostas claras, não criar outra camada.
