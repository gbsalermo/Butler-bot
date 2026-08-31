# Arquitetura do Butler — fonte de verdade de produção

**Data-base:** 31/08/2026  
**Fase funcional:** Etapa 1 — linguagem natural/conversa  
**Subetapa atual:** 1.4 — correção e auto-reparo

> Este documento descreve **o runtime operacional atual**. Para saber onde o projeto está e qual é o próximo trabalho, comece por `docs/STATUS_ATUAL.md`. Para visão completa do produto use `docs/BUTLER_DOSSIE_MESTRE.md`; para evolução futura use `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`.

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
- mantém `AttendanceAlarm` e `PersonalAlarm`;
- no cron, sincroniza Durable Objects de forma síncrona antes de delegar;
- após webhook, rearma os Durable Objects com `ctx.waitUntil(...)`, **fora do caminho crítico da resposta HTTP**.

Essa última decisão evita fazer o Telegram esperar SELECTs globais e chamadas a Durable Objects antes do `200 OK`.

### `entry.py`

Orquestrador autoritativo. O fluxo é exposto em funções testáveis:

```text
dispatch_callback(db, token, callback)
dispatch_message(db, token, message)
dispatch_scheduled(db, token)
```

`Default.fetch()` resolve HTTP/webhook; `Default.scheduled()` delega ao cron operacional.

A ordem dos handlers é parte do comportamento e possui regressão em `cloudflare/tests/`.

### `app.py`

Núcleo-base herdado. Ainda contém:

- D1/bootstrap de usuários;
- estados guiados;
- operações-base de agenda, tarefas, mercado, finanças, metas e treino;
- scheduler legado/compatibilidade.

Vários símbolos são substituídos no bootstrap. Portanto, uma constante/função em `app.py` não é automaticamente a fonte final de produção.

---

## 3. Dispatcher real de mensagens

Ordem atual de `dispatch_message()`:

```text
1.  start/reset
2.  prévia de aviso administrativo
3.  diagnóstico administrativo de usuários
4.  diagnóstico de alertas
5.  despedida prioritária
6.  usabilidade / Ler-Ver Depois
7.  menu operacional
8.  UI de rotinas
9.  edição de rotinas
10. UI de presença
11. navegação global
12. core_fast_path
13. gestão de presença
14. presença natural
15. cancelamento de prova
16. frases de prova
17. acadêmico
18. correction_patch / auto-reparo
19. lembrete explícito simples
20. referência curta
21. contexto de tarefa
22. runtime_guard
23. mercado informal
24. quality
25. musculação
26. conversation_layer
27. app.handle_message somente para botão/estado guiado necessário
28. fallback
```

Um handler que retorna `True` consome a mensagem.

### Mudanças relevantes desde a Etapa 0

- DDL defensivo de presença **não roda mais no dispatcher geral**; migration 0003 é a fonte formal e guards locais permanecem onde necessários;
- `correction_patch` foi inserido antes dos parsers de criação para permitir auto-reparo do turno anterior;
- referências possuem gate lexical antes de consultar contexto/D1;
- famílias linguísticas compartilhadas reduzem listas duplicadas de verbos/formulações.

### Consequência

Quando uma frase cai no módulo errado, descubra primeiro **qual handler anterior a consumiu**. Não crie regex ou patch novo antes de entender a precedência.

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

Sequência relevante em `entry.py`:

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

Nem todo módulo ativo exige `install()`: `correction_patch`, `reference_patch`, `language_primitives`, `short_context` e outros também participam por import/chamada direta ou integração transitiva.

### Relações relevantes

- `quality_patch` **não define política temporal de tarefas/compromissos**;
- `conversation_layer` **não envia lembretes de `daily_items`**;
- `reminder_policy.py` foi removido;
- `scheduled_delivery_guard` protege canais de entrega crítica;
- `operational_menu` define o menu principal e instala a família de metas;
- `production_usability_patch` sincroniza menus-base e implementa Ler/Ver Depois;
- o contrato de contexto curto foi unificado em `short_context.py`.

---

## 6. Linguagem natural — arquitetura ativa da Etapa 1

A produção **não usa uma NLU ampla como roteador central**.

### `language_primitives.py`

Responsável por primitivas/famílias linguísticas compartilhadas e polaridade.

Contrato:

```text
reconhece sinais linguísticos
→ NÃO acessa D1
→ NÃO envia Telegram
→ NÃO executa CRUD
```

A escrita continua pertencendo ao módulo de domínio.

### `short_context.py`

Autoridade de contexto operacional curto.

Características:

- isolamento por `user_id`;
- expiração inicial de 30 minutos;
- histórico de alvos recentes;
- listas posicionais na ordem vista pelo usuário;
- barreira de mudança explícita de assunto;
- adaptação de chamadores legados de `conversation_layer._remember/_context` para o mesmo contrato.

### `reference_patch.py`

Resolve referências como:

```text
essa / ela / ele
a primeira / segunda / terceira
a outra
a anterior
a última
```

A resolução identifica o alvo; a escrita continua no domínio.

### `correction_patch.py`

Primeira fatia ativa da Etapa 1.4.

Exemplo:

```text
marca dentista amanhã às 15h
→ não, 16h
```

Só corrige silenciosamente contexto marcado como `source=created` ou `source=corrected`. Contextos de lista não são elegíveis.

### `temporal_language.py`

Concentra primitivas de tempo relativo preparadas na Etapa 1. A execução de timers gerais persistentes pertence à Etapa 3 e não deve ser anunciada como pronta.

---

## 7. Autoridade por domínio

| Domínio | Autoridade atual | Observação |
|---|---|---|
| Dispatcher | `entry.py` | mensagens, callbacks e cron |
| Menu principal/Cotidiano | `operational_menu.py` | `app.MAIN_KB` sincronizado como fallback |
| Linguagem comum | `language_primitives.py` | sem efeitos colaterais |
| Contexto curto | `short_context.py` | expiração, histórico e isolamento |
| Auto-reparo | `correction_patch.py` | Etapa 1.4, primeira fatia |
| Tarefas | `task_context_patch.py`, `runtime_guard.py`, `app.py` | fast paths complementam |
| Compromissos | `operational_menu.py`, `app.py` | temporalidade em `reliable_reminders.py` |
| `daily_items` temporais | `reliable_reminders.py` | autoridade única |
| Mercado | `grocery_phrase_patch.py`, `quality_patch.py`, `app.py` | relatos claros podem gravar direto |
| Rotinas | `routine_integration.py`, `runtime_guard.py`, `routine_editing.py`, `routine_ui_patch.py` | quality só ajusta checkpoint |
| Metas | `goal_operational.py` + família `goal_*` | instalada por `operational_menu` |
| Acadêmico | `academic_intelligence.py`, `academic_polish.py`, `exam_*`, `attendance_*` | família ainda fragmentada |
| Presença | `attendance_*`, `attendance_alarm.py` | eventos temporais próprios |
| Musculação | `workout_progress_patch.py`, `app.py`, `protocol_mass_data.py` | proprietário × genérico |
| Ler/Ver Depois | `production_usability_patch.py` | Livros/Filmes/Cursos/Outras; migration 0008 |
| Clima | `weather_context.py`, `weather_service.py`, `weather_personality.py` | dados objetivos + apresentação humana |
| Resumos | `reliable_summaries.py` | manhã 07:00; domingo 20:00 |
| Administração | `admin_diagnostics.py`, `admin_announcement_flow.py` | somente proprietário |
| Alarmes persistentes | `attendance_alarm.py`, `personal_alarm.py` | Durable Objects |
| Day-off | `day_off_policy.py` + políticas dos schedulers | escopo diário |
| Performance | `performance_patch.py` | cache por update e helpers compartilhados |

---

## 8. Menu autoritativo

`operational_menu.py`:

```text
MAIN_KB
➕ Adicionar | 🗓️ Hoje
🛒 Item faltando | 📚 Matérias
🏠 Cotidiano | 🏋️ Musculação
🌙 Day-off
```

`production_usability_patch.install()` mantém fallbacks de `app.py` sincronizados.

No submenu Ler/Ver Depois existem atualmente:

```text
📚 Livros
🎬 Filmes
🎓 Cursos
🗂️ Outras
```

A categoria `Cursos` é apenas captura da lista; o domínio completo Cursos/Trilhas permanece planejado para a Etapa 4.

---

## 9. Scheduler real e redundância

O Cron Trigger roda a cada minuto e continua a linha primária.

### Linha primária

```text
worker.py sincroniza Durable Objects
→ dispatch_scheduled()
   day_off
   → attendance
   → daily_items / reliable_reminders
   → routines
   → summaries
   → app.scheduled_tick (legado/compatibilidade)
```

`scheduler_runtime.run_isolated()` evita que uma falha cancele subsistemas seguintes.

### Linha persistente de contingência

Após o incidente de 30/08/2026, o Cron deixou de ser tratado como ponto único de falha:

```text
webhook/cron
→ sync_personal_alarms()
→ PersonalAlarm por usuário
→ próximo evento persistido
→ alarm()
→ dispatchers autoritativos
```

`PersonalAlarm` considera:

- tarefa com horário;
- compromisso em T-5;
- lembrete simples;
- checkpoint de rotina;
- resumo matinal;
- fechamento semanal.

`AttendanceAlarm` permanece separado para aula/presença.

Depois de POST/webhook, o rearme usa `ctx.waitUntil(...)`. No cron, a sincronização continua síncrona.

A redundância converge para as mesmas autoridades e `notification_log`; não deve duplicar mensagens.

Detalhes: `docs/SCHEDULER_REDUNDANCY.md`.

### Política temporal de `daily_items`

`reliable_reminders.py` é a autoridade:

- tarefa com horário: no horário;
- compromisso: 5 minutos antes;
- lembrete simples: no horário, janela curta;
- `notification_log`: idempotência;
- supressão da chave do scheduler legado;
- entrega crítica validada quando aplicável.

---

## 10. Performance do caminho quente

`performance_patch.py` reduz round-trips D1 durante um único update.

Cache local ao request:

```text
telegram_chat_id → user_id
user_sessions
```

O cache é reiniciado/limitado ao update e não deve ser interpretado como cache persistente global.

Outras decisões de latência:

- gate lexical antes de consultas de contexto;
- DDL defensivo de presença removido do dispatcher geral;
- sincronização global de Durable Objects fora da resposta HTTP interativa.

Regressões específicas existem em `cloudflare/tests/test_request_hotpath_performance.py` e testes relacionados.

---

## 11. Banco e migrations

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

As Etapas 1.1–1.4, até este snapshot, reutilizam estruturas existentes (`natural_events`, `user_sessions`, `daily_items`) e não adicionaram migration.

Alguns módulos mantêm `ensure_schema()` defensivo para implantação incremental. Isso **não substitui migration**.

`runtime_schema.py` permanece preservado como helper e não é catálogo/boot automático.

Migration destrutiva exige snapshot/export D1 e plano de rollback documentado.

---

## 12. Contexto/memória preservados fora do roteamento central

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

Esses componentes não devem ser alterados esperando efeito no bot sem religação explícita e teste de precedência.

A Etapa 1 está reaproveitando conceitos de forma seletiva, mas a autoridade operacional nova é explicitada nos módulos ativos citados acima.

---

## 13. Butler Library / conversa experimental

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

O `/health` mantém flags explícitas de broad NLU, Library genérica, sugestões transversais e memória pessoal genérica desabilitadas.

---

## 14. Clima

`weather_service.py`/`weather_context.py` mantêm os dados objetivos e integração com agenda. `weather_personality.py` acrescenta comentário mais humano à apresentação.

Invariante:

```text
personalidade pode interpretar/apresentar
≠
personalidade inventar temperatura, chuva, vento ou probabilidade
```

Falha de Open-Meteo não pode impedir agenda/resumo.

---

## 15. Runtime legado

A raiz `src/` usa `python-telegram-bot`, polling e SQLite. Foi classificada como **PRESERVADO/LEGADO**.

Correção feita somente ali não altera produção Cloudflare.

---

## 16. Configuração e segurança

`settings.py` ainda contém configuração versionada do deploy pessoal.

- `TIMEZONE_NAME` alinha clima/calendário;
- localização meteorológica default vale como fallback do proprietário;
- outros usuários configuram cidade;
- `TELEGRAM_WEBHOOK_SECRET` é suportado;
- tokens nunca devem ser versionados;
- configuração pessoal deve migrar para seed/config privada antes de distribuição ampla.

---

## 17. Testes

Workflow `.github/workflows/butler-regression.yml`:

```text
compileall cloudflare/src
pytest -q
```

`tests/conftest.py` fornece stubs mínimos de `js`, `pyodide` e `workers`; não simula rede real.

Testes novos devem priorizar:

- caminho alcançado por `entry.py`;
- precedência/falso positivo;
- sequências de conversa;
- dois usuários;
- idempotência;
- cancelar/voltar;
- scheduler/callback repetido;
- consultas D1 desnecessárias no caminho quente.

CI/regressão verde não é prova de deploy Cloudflare.

---

## 18. Como descobrir a fonte de verdade antes de editar

Pergunte nesta ordem:

1. `docs/STATUS_ATUAL.md` indica qual etapa está aberta?
2. `worker.py`/`entry.py` chamam o módulo?
3. há chamada transitiva a partir de módulo ativo?
4. existe `install()` substituindo símbolo?
5. um handler anterior consome a mensagem?
6. há estado em `user_sessions` ou alvo em `short_context` mudando o caminho?
7. é webhook, callback, cron ou Durable Object?
8. existe migration formal?
9. o teste cobre produção ou só arquitetura preservada?

Sem respostas claras, não criar outro patch nem outro roadmap.
