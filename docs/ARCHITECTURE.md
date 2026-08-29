# Arquitetura do Butler — fonte de verdade de produção

> Este documento descreve **o runtime operacional atual**. Para visão completa do produto use `docs/BUTLER_DOSSIE_MESTRE.md`; para evolução futura use `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`.

## 1. Runtime oficial

A produção está em `cloudflare/`:

```text
Telegram
  ↓ webhook
cloudflare/src/worker.py
  ↓
cloudflare/src/entry.py
  ↓
handlers operacionais
  ↓
D1 / Durable Objects / APIs externas
```

A raiz `src/` é o runtime histórico polling/SQLite. Está preservada como referência e **não governa produção**.

---

## 2. Entrypoints

### `worker.py`

Entrypoint configurado pelo Cloudflare. Ele:

- herda `entry.Default`;
- sincroniza `AttendanceAlarm`;
- sincroniza `PersonalAlarm`;
- delega HTTP e o restante do cron para `entry.py`.

### `entry.py`

Orquestrador autoritativo. Na Etapa 0 o fluxo foi extraído para funções testáveis:

```text
dispatch_callback(db, token, callback)
dispatch_message(db, token, message)
dispatch_scheduled(db, token)
```

`Default.fetch()` apenas resolve HTTP/webhook e delega; `Default.scheduled()` delega ao cron operacional.

A ordem dos handlers é parte do comportamento e é protegida por `cloudflare/tests/test_dispatcher_integration.py`.

### `app.py`

Núcleo-base herdado. Ainda contém:

- D1/bootstrap de usuários;
- estados guiados;
- operações-base de agenda, tarefas, mercado, finanças, metas e treino;
- scheduler legado/compatibilidade.

Vários símbolos são substituídos no bootstrap. Portanto, uma constante em `app.py` não é automaticamente a fonte final de produção.

---

## 3. Dispatcher real de mensagens

Ordem atual de `dispatch_message()`:

```text
1. /start e reset
2. prévia de aviso administrativo
3. diagnóstico administrativo de usuários
4. diagnóstico de alertas
5. despedida prioritária
6. usabilidade / Ler-Ver Depois
7. menu operacional
8. UI de rotinas
9. edição de rotinas
10. UI de presença
11. navegação global
12. core_fast_path
13. ensure_schema de presença
14. gestão de presença
15. presença natural
16. cancelamento de prova
17. frases de prova
18. acadêmico
19. lembrete explícito simples
20. referência curta
21. contexto de tarefa
22. runtime_guard
23. mercado informal
24. quality
25. musculação
26. conversation_layer
27. app.handle_message apenas para botão/estado guiado necessário
28. fallback
```

Um handler que retorna `True` consome a mensagem.

`core_fast_path.py` chama transitivamente:

- `weather_context.py`;
- `colloquial_reminder_fastpath.py`;
- `operational_informal_fastpath.py`;
- `routine_natural_fastpath.py`;
- mercado, provas, tarefas, lembretes e musculação específicos.

### Consequência

Quando uma frase cai no módulo errado, descubra primeiro **qual handler anterior a consumiu**. Não crie um regex novo antes de entender a precedência.

---

## 4. Dispatcher de callbacks

Ordem atual de `dispatch_callback()`:

```text
admin_announcement_flow
→ attendance
→ conversation_layer/item callbacks
```

A precedência administrativa é proposital e coberta por regressão.

---

## 5. Bootstrap / instalações

Sequência em `entry.py` após a Etapa 0:

```text
performance_patch
scheduler_patch
routine_integration
routine_ui_patch
conversation_layer
quality_patch
natural_behavior recurrence patch
academic_intelligence
academic_polish
exam_cancel_patch
personality_variants
ux_bugfixes
task_context_patch
attendance_patch
attendance_enhancement
attendance_management
attendance_production_fix
task_emoji_patch
workout_progress_patch
scheduled_delivery_guard
operational_menu
production_usability_patch
```

### Relações relevantes

- `quality_patch` **não define mais política temporal de tarefas/compromissos**; apenas ajusta checkpoint de rotina e trata formulações específicas de mercado;
- `conversation_layer` **não envia mais lembretes de `daily_items`**;
- `reminder_policy.py` foi removido porque o `noop` deixou de ser necessário;
- `scheduled_delivery_guard` protege canais de entrega crítica;
- `operational_menu` define o menu principal e instala a família de metas;
- `production_usability_patch` sincroniza menus-base de `app` e implementa Ler/Ver Depois.

---

## 6. Autoridade por domínio

| Domínio | Autoridade atual | Observação |
|---|---|---|
| Dispatcher | `entry.py` | mensagens, callbacks e cron testáveis |
| Menu principal/Cotidiano | `operational_menu.py` | `app.MAIN_KB` é sincronizado como fallback |
| Tarefas | `task_context_patch.py`, `runtime_guard.py`, `app.py` | fast paths conservadores complementam |
| Compromissos | `operational_menu.py`, `app.py` | temporalidade em `reliable_reminders.py` |
| Lembretes de `daily_items` | `reliable_reminders.py` | autoridade temporal única após Etapa 0 |
| Lembretes naturais | `natural_behavior_patch.py`, `colloquial_reminder_fastpath.py` | criação; entrega continua em reliable |
| Mercado | `grocery_phrase_patch.py`, `quality_patch.py`, `app.py` | política atual grava relatos claros de falta |
| Rotinas | `routine_integration.py`, `runtime_guard.py`, `routine_editing.py`, `routine_ui_patch.py` | quality só ajusta checkpoint |
| Metas | `goal_operational.py` + família `goal_*` | instalada por `operational_menu` |
| Acadêmico | `academic_intelligence.py`, `academic_polish.py`, `exam_*`, `attendance_*` | família ainda fragmentada |
| Presença | `attendance_*`, `attendance_alarm.py` | eventos temporais próprios |
| Musculação | `workout_progress_patch.py`, `app.py`, `protocol_mass_data.py` | proprietário × genérico |
| Ler/Ver Depois | `production_usability_patch.py` | schema formal em migration 0008 |
| Clima | `weather_context.py`, `weather_service.py` | Open-Meteo; agenda/resumo |
| Resumos | `reliable_summaries.py` | manhã 07:00; domingo 20:00 |
| Administração | `admin_diagnostics.py`, `admin_announcement_flow.py` | somente proprietário |
| Alarmes persistentes | `attendance_alarm.py`, `personal_alarm.py` | Durable Objects sincronizados por worker |
| Day-off | `day_off_policy.py` + políticas dos schedulers | escopo diário |

---

## 7. Menu autoritativo

`operational_menu.py`:

```text
MAIN_KB
➕ Adicionar | 🗓️ Hoje
🛒 Item faltando | 📚 Matérias
🏠 Cotidiano | 🏋️ Musculação
🌙 Day-off
```

`production_usability_patch.install()` mantém os fallbacks de `app.py` sincronizados. Na Etapa 0, `conversation_layer.py` deixou de possuir uma cópia própria do menu principal.

Menus locais de domínio continuam em seus módulos; o objetivo é uma fonte única para navegação principal, não um arquivo monolítico de toda a UI.

---

## 8. Scheduler real

O cron do Worker roda a cada minuto.

`worker.py` sincroniza primeiro os Durable Objects. Depois `dispatch_scheduled()` executa isoladamente:

```text
day_off
→ attendance
→ daily_items / reliable_reminders
→ routines
→ summaries
→ app.scheduled_tick (legado/compatibilidade)
```

`scheduler_runtime.run_isolated()` evita que uma falha cancele os subsistemas seguintes.

### Política temporal de `daily_items`

`reliable_reminders.py` é a autoridade:

- tarefa com horário: no horário;
- compromisso: 5 minutos antes;
- lembrete pessoal simples: no horário, com janela curta;
- `notification_log`: idempotência;
- supressão da chave do scheduler legado para evitar duplicação;
- entrega crítica validada quando aplicável.

A Etapa 0 removeu as políticas duplicadas que viviam em `quality_patch`/`conversation_layer` e o neutralizador `reminder_policy.py`.

### Outros eventos temporais

- aula/presença: camada própria e alarmes persistentes;
- rotinas: scheduler próprio;
- resumo da manhã: 07:00;
- semanal: domingo 20:00;
- clima: falha degrada para resumo sem previsão, não derruba o cron.

---

## 9. Banco e migrations

Fonte formal: `cloudflare/migrations/`.

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

### Escopo resumido

- **0001:** usuários, estado, matérias, `daily_items`, mercado, metas, rotinas, finanças, musculação, eventos e notificações;
- **0002:** `user_sessions` e logs de treino;
- **0003:** configurações/faltas acadêmicas;
- **0004:** contexto estruturado preservado;
- **0005:** perfis avançados de meta;
- **0006:** preferências de clima;
- **0007:** confirmação idempotente de avisos administrativos;
- **0008:** Ler/Ver Depois.

Alguns módulos mantêm `ensure_schema()` defensivo para implantação incremental. Isso **não substitui migration**.

`runtime_schema.py` permanece preservado como helper e não é catálogo/boot automático.

### Regra

Nova persistência exige: migration → backfill se necessário → índice quando justificado → teste → documentação.

Migration destrutiva exige snapshot/export D1 e plano de rollback documentado.

---

## 10. Contexto e memória

### Ativo

- `natural_events` para referências operacionais curtas;
- `user_sessions` para estados guiados;
- `conversation_layer.py` para contexto recente delimitado;
- `reference_patch.py`/`task_context_patch.py` para ações contextuais.

### Preservado fora do roteamento central

```text
context_router.py
intent_parser.py
action_policy.py
context_memory.py
context_sync.py
compound_router.py
language_context.py
suggestion_engine.py
deterministic_memory.py
general_memory.py
```

Esses componentes são insumo futuro para as Etapas 1/7. Não devem ser alterados esperando efeito no bot sem religação explícita e teste de precedência.

---

## 11. Butler Library / conversa experimental

Preservados, mas não ligados como dispatcher genérico:

```text
butler_library.py
library_catalog_handler.py
library_context_bridge.py
library_index.py
knowledge/
cooking_library.py
companion_*
conversational_*
cultural_background.py
```

Exceção: `companion_safe_fallback.py` é alcançado pelo dispatcher para despedidas prioritárias/fallback seguro.

O `/health` continua explicitando:

```text
broad_nlu_disabled
generic_library_dispatch_disabled
cross_domain_suggestions_disabled
generic_personal_memory_disabled
```

---

## 12. Limpeza da Etapa 0

Removidos com prova de desuso:

- `add_intent_patch.py` — não conectado ao runtime;
- `reminder_policy.py` — `noop` sem função após consolidação.

Consolidado:

- menu principal: uma autoridade;
- lembretes temporais: uma autoridade;
- dispatcher/callback/cron: funções testáveis;
- `later_items`: migration formal.

Inventário detalhado: `docs/INVENTARIO_ETAPA_0.md`.

---

## 13. Runtime legado

A raiz `src/` usa `python-telegram-bot`, polling e SQLite. Foi classificada como **PRESERVADO/LEGADO**, não removida na Etapa 0.

Correção feita somente ali não altera produção Cloudflare.

---

## 14. Configuração e segurança

`settings.py` ainda contém configuração versionada do deploy pessoal.

- `TIMEZONE_NAME` alinha clima/calendário;
- localização meteorológica default vale como fallback do proprietário;
- outros usuários configuram sua cidade;
- `TELEGRAM_WEBHOOK_SECRET` é suportado;
- tokens nunca devem ser versionados;
- mover perfil/seed pessoal para configuração privada continua dívida antes de distribuição ampla.

---

## 15. Testes

Workflow `.github/workflows/butler-regression.yml`:

```text
compileall cloudflare/src
pytest -q
```

`tests/conftest.py` fornece stubs mínimos de `js`, `pyodide` e `workers` para permitir testes determinísticos; não simula rede real.

Testes novos devem priorizar:

- caminho alcançado por `entry.py`;
- precedência/falso positivo;
- sequências de conversa;
- dois usuários;
- idempotência;
- cancelar/voltar;
- scheduler/callback repetido.

---

## 16. Como descobrir a fonte de verdade antes de editar

Pergunte nesta ordem:

1. `worker.py`/`entry.py` chamam o módulo?
2. há chamada transitiva a partir de módulo ativo?
3. existe `install()` substituindo símbolo?
4. um handler anterior consome a mensagem?
5. há estado em `user_sessions` mudando o caminho?
6. é webhook, callback, cron ou Durable Object?
7. existe migration formal?
8. o teste cobre produção ou só arquitetura preservada?

Sem respostas claras, não criar outro patch.
