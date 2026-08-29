# Butler — Inventário da Etapa 0

**Data-base:** 29/08/2026  
**Objetivo:** registrar o papel do código relevante antes de qualquer exclusão ou consolidação adicional.

> Classificação usada: **ATIVO**, **LEGADO NECESSÁRIO**, **PRESERVADO**, **DUPLICADO**, **OBSOLETO** e **REMOVIDO**. A classificação descreve a conexão com o runtime de produção; não mede a qualidade do código.

---

## 1. Runtime e entrypoints

| Arquivo / área | Classe | Papel |
|---|---|---|
| `cloudflare/src/worker.py` | ATIVO | Entrypoint configurado no Worker; sincroniza Durable Objects e delega webhook/cron ao dispatcher. |
| `cloudflare/src/entry.py` | ATIVO / AUTORIDADE | Dispatcher HTTP, callbacks, mensagens e cron. A ordem dos handlers é contrato de produção. |
| `cloudflare/src/app.py` | ATIVO + LEGADO NECESSÁRIO | Núcleo-base herdado. Ainda fornece estados guiados, CRUDs e scheduler de compatibilidade; vários símbolos são substituídos no bootstrap. |
| `cloudflare/wrangler.jsonc` | ATIVO | Configuração de deploy do Worker, D1, Durable Objects e cron. |
| raiz `src/` | PRESERVADO / LEGADO | Runtime antigo Python Telegram Bot + polling + SQLite. Não recebe correções de produção por padrão. |
| `cloudflare/src/runtime_schema.py` | PRESERVADO | Helper histórico/manual; não é a fonte formal de migrations nem bootstrap automático. |

### Decisão da Etapa 0

O diretório legado `src/` **não será apagado nesta etapa**. Ele está isolado e documentado, e removê-lo não traz benefício operacional proporcional ao risco de perder referência histórica. Uma futura exclusão deve ser um PR próprio.

---

## 2. Dispatcher ativo de mensagens

A cadeia autoritativa está em `entry.dispatch_message()`:

```text
/start/reset
→ prévia administrativa de aviso
→ diagnóstico de usuários
→ diagnóstico de alertas
→ despedida prioritária
→ usabilidade / Ler-Ver Depois
→ menu operacional
→ UI/edição de rotinas
→ presença UI
→ navegação global
→ core_fast_path
→ schema de presença
→ gestão de presença
→ presença natural
→ cancelamento/provas
→ acadêmico
→ lembrete explícito
→ referência recente
→ contexto de tarefa
→ runtime_guard
→ mercado informal
→ quality
→ musculação
→ conversation_layer
→ app.py somente para botão/estado guiado
→ fallback
```

`cloudflare/tests/test_dispatcher_integration.py` protege precedência administrativa, callbacks e ordem do cron.

---

## 3. Módulos ativos — Core e UX

| Módulo | Classe | Responsabilidade atual |
|---|---|---|
| `operational_menu.py` | ATIVO / AUTORIDADE | `MAIN_KB`, `COTIDIANO_KB`, `ADD_KB`; instala metas e rotas diretas de menu. |
| `production_usability_patch.py` | ATIVO | Ler/Ver Depois, usabilidade e sincronização final dos menus-base de `app.py`. |
| `core_fast_path.py` | ATIVO | Gate conservador para ações claras; chama fast paths específicos. |
| `runtime_guard.py` | ATIVO | Estados guiados e proteção de fluxos operacionais. |
| `start_reset.py` | ATIVO | `/start` e reinicialização de estado. |
| `ux_bugfixes.py` | ATIVO | navegação global, voltar/cancelar e correções de UX. |
| `task_context_patch.py` | ATIVO | tarefas, listas e ações contextuais. |
| `reference_patch.py` | ATIVO | referências recentes e resolução contextual curta. |
| `conversation_layer.py` | ATIVO | contexto operacional curto, ações sobre item recente e agenda enriquecida. Não dispara mais lembretes de itens. |
| `natural_behavior_patch.py` | ATIVO | lembretes explícitos/recorrência e comportamento natural delimitado. |
| `personality_variants.py` | ATIVO | variações de tom sem alterar autoridade de dados. |
| `performance_patch.py` | ATIVO | otimiza bootstrap de usuário conhecido. |
| `task_emoji_patch.py` | ATIVO | apresentação de tarefas. |
| `telegram_api.py` | ATIVO / INFRA | envio e callbacks Telegram. |
| `settings.py` | ATIVO / CONFIG | timezone, proprietário e defaults versionados. |
| `owner_profile.py` | ATIVO | identidade/autorização do proprietário. |

### Fast paths transitivos ativos

- `colloquial_reminder_fastpath.py`;
- `operational_informal_fastpath.py`;
- `routine_natural_fastpath.py`;
- `grocery_phrase_patch.py`;
- `exam_phrase_patch.py`;
- `weather_context.py`;
- `workout_progress_patch.py`.

Eles são alcançados por `core_fast_path.py` e não devem ser considerados “soltos” apenas por não aparecerem diretamente em `entry.py`.

---

## 4. Autoridade por domínio

| Domínio | Autoridade / módulos ativos | Observação |
|---|---|---|
| Menu principal | `operational_menu.py` | único desenho autoritativo; outros módulos usam `app.MAIN_KB` sincronizado. |
| Tarefas | `task_context_patch.py` + `runtime_guard.py` + base `app.py` | criação natural pode passar por fast paths. |
| Compromissos | `operational_menu.py` + base `app.py` | histórico permanece em `daily_items`. |
| Lembretes de tarefa/compromisso | `reliable_reminders.py` | autoridade temporal única após Etapa 0. |
| Lembrete pessoal simples | `natural_behavior_patch.py` / fast path + `reliable_reminders.py` | item é marcado com `details='simple_reminder'`. |
| Mercado | `grocery_phrase_patch.py` + `quality_patch.py` + base `app.py` | relatos claros de falta continuam gravando diretamente conforme política atual. |
| Rotinas | `routine_integration.py`, `routine_ui_patch.py`, `routine_editing.py`, `runtime_guard.py` | `quality_patch.py` só ajusta checkpoint inteligente. |
| Metas | `goal_operational.py` + família `goal_*` instalada por `operational_menu.py` | ativa de forma transitiva. |
| Acadêmico | `academic_intelligence.py`, `academic_polish.py`, `exam_*`, `attendance_*` | próximo grande refinamento funcional ocorre na Etapa 2. |
| Presença | família `attendance_*` + `attendance_alarm.py` | possui fluxo e scheduler críticos próprios. |
| Musculação | `workout_progress_patch.py` + `app.py` + `protocol_mass_data.py` | protocolo proprietário e treino genérico coexistem. |
| Ler/Ver Depois | `production_usability_patch.py` | migration formalizada como `0008_later_items.sql`. |
| Clima | `weather_context.py` + `weather_service.py` | Open-Meteo; integrado à agenda/resumo. |
| Resumos | `reliable_summaries.py` | manhã 07:00 e domingo 20:00. |
| Administração | `admin_diagnostics.py` + `admin_announcement_flow.py` | proprietário: status de usuários e avisos com confirmação por botão. |
| Alarmes pessoais | `personal_alarm.py` | Durable Object sincronizado por `worker.py`. |
| Day-off | `day_off_policy.py` + políticas dos schedulers | escopo diário; não é automático no fim de semana. |

---

## 5. Scheduler / notificações

### Autoridades ativas

`entry.dispatch_scheduled()` executa:

```text
day_off
→ attendance
→ daily_items / reliable_reminders
→ routines
→ summaries
→ legacy app.scheduled_tick
```

`worker.py` sincroniza antes os Durable Objects de presença e alarmes pessoais.

### Política consolidada de lembretes

`reliable_reminders.py` é a autoridade para `daily_items` temporais:

- tarefa: no horário cadastrado;
- compromisso: 5 minutos antes;
- lembrete pessoal simples: no horário, com tolerância curta;
- `notification_log`: idempotência;
- supressão de chave do scheduler-base antes do caminho legado;
- envio crítico só é considerado concluído após confirmação da API Telegram por meio da camada de entrega protegida.

### Limpeza realizada

- **REMOVIDO:** `reminder_policy.py` — era um `noop` necessário apenas para neutralizar um scheduler duplicado;
- **REMOVIDO da responsabilidade:** scheduler temporal de itens dentro de `conversation_layer.py`;
- **REMOVIDO da responsabilidade:** política temporal duplicada dentro de `quality_patch.py`.

Resultado: não existe mais uma cadeia `quality → conversation → noop` para decidir quem manda lembretes.

---

## 6. Menus

### Autoridade

`operational_menu.py` define:

```text
MAIN_KB
➕ Adicionar | 🗓️ Hoje
🛒 Item faltando | 📚 Matérias
🏠 Cotidiano | 🏋️ Musculação
🌙 Day-off
```

`production_usability_patch.install()` mantém `app.MAIN_KB` e `app.COTIDIANO_KB` sincronizados com essa fonte. `conversation_layer.py` deixou de possuir uma cópia própria do menu principal.

Menus locais de domínio (`TASK_KB`, `ROUTINE_KB`, `GROCERY_KB`, academia etc.) continuam válidos; centralizar o **menu principal** não significa criar um arquivo único gigantesco para todos os submenus.

---

## 7. Banco D1 — migrations formais

| Migration | Escopo |
|---|---|
| `0001_initial.sql` | usuários, estado, matérias, agenda, mercado, metas, rotinas, finanças, musculação, eventos e `notification_log`. |
| `0002_app_state.sql` | `user_sessions` e logs incrementais de treino. |
| `0003_attendance.sql` | configurações e faltas por matéria/sessão. |
| `0004_conversation_context.sql` | contexto estruturado preservado/experimental. |
| `0005_goal_profiles.sql` | perfil estendido de metas. |
| `0006_weather_preferences.sql` | localização e preferências meteorológicas. |
| `0007_admin_pending_announcements.sql` | avisos administrativos pendentes e idempotência de confirmação. |
| `0008_later_items.sql` | Ler/Ver Depois formalizado no histórico de migrations. |

### Regra formal

Nova alteração persistente exige:

1. migration versionada;
2. backfill explícito quando necessário;
3. `ensure_schema()` somente como tolerância operacional, nunca substituto da migration;
4. índice quando a consulta quente justificar;
5. regressão;
6. atualização do Dossiê/Arquitetura quando a estrutura pública mudar.

### Backup

Ainda não existe automação de backup/exportação D1 versionada no repositório. Até a Etapa 8, a regra é: **antes de migration destrutiva, fazer export/snapshot do D1 e registrar o procedimento no PR**. Migration destrutiva sem plano de rollback é proibida.

---

## 8. Código preservado fora do dispatcher principal

Classificação **PRESERVADO**: trabalho útil, porém não deve ser anunciado como ativo nem alterado esperando efeito no webhook sem religação explícita.

### NLU/contexto/memória estruturada

- `context_router.py`;
- `intent_parser.py`;
- `action_policy.py`;
- `context_memory.py`;
- `context_sync.py`;
- `compound_router.py`;
- `language_context.py`;
- `suggestion_engine.py`;
- `deterministic_memory.py`;
- `general_memory.py`;
- `personal_profile.py` e auxiliares que não estejam ligados ao dispatcher.

Esses módulos são matéria-prima para a **Etapa 1** e **Etapa 7**, não uma segunda arquitetura de produção.

### Library / conhecimento

- `butler_library.py`;
- `library_catalog_handler.py`;
- `library_context_bridge.py`;
- `library_index.py` e consultas auxiliares;
- `cooking_library.py`;
- `cloudflare/src/knowledge/`;
- módulos culturais/conversacionais não conectados ao dispatcher.

### Companion / conversa experimental

- `companion_language_patch.py`;
- `companion_life_context.py`;
- `companion_nlu_v2.py`;
- `conversational_background.py`;
- `conversational_companion.py`;
- `cultural_background.py`.

Exceção: `companion_safe_fallback.py` é **ATIVO** apenas para despedidas prioritárias/fallback seguro alcançado por `entry.py`.

---

## 9. Código removido nesta etapa

| Arquivo | Classificação anterior | Motivo |
|---|---|---|
| `cloudflare/src/add_intent_patch.py` | OBSOLETO | não estava importado pelo runtime nem possuía chamada transitiva necessária; duplicava caminho de intenção já coberto por módulos ativos. |
| `cloudflare/src/reminder_policy.py` | OBSOLETO após consolidação | existia apenas para substituir `_pre_send_item_reminders` por `noop`; a função duplicada foi removida da origem. |

A regra é deliberadamente conservadora: **dois arquivos removidos com prova de desuso valem mais que dezenas apagados por aparência**.

---

## 10. Dívida técnica que permanece

### P0 — antes de expandir muito o Core

1. `app.py` continua grande e concentra base + legado + compatibilidade;
2. família acadêmica/presença possui vários patches sobrepostos e merece consolidação na Etapa 2;
3. partes do scheduler-base ainda são executadas no final por compatibilidade;
4. configuração pessoal do proprietário ainda está versionada em código.

### P1 — tratar ao longo das próximas etapas

1. consolidar gradualmente pequenos patches de apresentação quando houver testes suficientes;
2. criar estratégia automatizada de backup D1;
3. aumentar testes com dois usuários e sequências completas;
4. documentar/automatizar aplicação de migrations no deploy;
5. tornar `TELEGRAM_WEBHOOK_SECRET` obrigatório antes de distribuição mais ampla.

### P2 — somente quando chegar a etapa correspondente

1. decidir quais módulos preservados de NLU/memória voltam;
2. reduzir/arquivar o runtime raiz `src/`;
3. reativar Library de modo seletivo;
4. avaliar voz/interface web/app somente após o roadmap atual.

---

## 11. Critério de manutenção daqui para frente

Antes de criar `*_patch.py`, `*_fix.py` ou `*_integration.py` novo:

1. identificar o módulo autoritativo;
2. verificar se a mudança pode entrar nele diretamente;
3. proteger a regra com teste;
4. só criar camada paralela quando houver limitação técnica real e documentada;
5. registrar qualquer monkeypatch remanescente em `docs/ARCHITECTURE.md`.

Este inventário é a fotografia estrutural de encerramento da Etapa 0 e deve ser atualizado quando uma futura consolidação mudar a classificação de um componente.
