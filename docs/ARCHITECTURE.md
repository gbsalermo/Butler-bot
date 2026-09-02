# Arquitetura do Butler — fonte de verdade de produção

**Data-base:** 01/09/2026  
**Fase funcional:** Etapa 4.1–4.6 concluída  
**Próximo trabalho de produto:** fechamento obrigatório da Etapa 4 — menu por áreas da vida

> Este documento descreve o **runtime operacional atual**. Para andamento e próximo passo use `docs/STATUS_ATUAL.md`; para decisões duradouras use `CONTINUIDADE.md`; para ordem futura use `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`.

---

## 1. Runtime oficial

Produção está em `cloudflare/`:

```text
Telegram
  ↓ webhook
cloudflare/src/worker.py
  ↓
cloudflare/src/entry.py
  ↓
handlers operacionais ordenados
  ↓
D1 / Durable Objects / Telegram Bot API / Open-Meteo
```

A raiz `src/` é o runtime histórico polling/SQLite e **não governa produção**.

### Entrypoints

`worker.py` é o entrypoint Cloudflare. Ele mantém os Durable Objects temporais e delega o webhook/cron ao runtime de `entry.py`.

`entry.py` é o orquestrador autoritativo e expõe:

```text
dispatch_callback(db, token, callback)
dispatch_message(db, token, message)
dispatch_scheduled(db, token)
```

A ordem dos handlers é comportamento de produção e possui regressão.

`app.py` ainda contém base histórica útil — usuários, estados guiados e operações-base — mas vários símbolos são substituídos/compostos no bootstrap. Existir em `app.py` não significa ser a autoridade final.

---

## 2. Regra de precedência

Um handler que retorna `True` consome a mensagem. Quando uma frase cai no domínio errado, primeiro identifique **qual handler anterior a consumiu**; não acrescente regex/patch antes de entender a precedência.

A sequência operacional inclui, em linhas gerais:

```text
start/reset
→ administração/diagnóstico
→ despedidas prioritárias
→ usabilidade/Ler-Ver Depois
→ operational_menu
→ rotinas/presença/navegação
→ fast paths de domínio
→ acadêmico/provas
→ correção temporal
→ lembretes/referências/contexto curto
→ runtime_guard
→ mercado/musculação/conversation layer
→ app.handle_message apenas quando necessário
→ fallback seguro
```

`operational_menu.py` contém a entrada de **Cursos estruturados** e despacha a extensão da Etapa 4 antes do CRUD-base de Cursos.

---

## 3. Bootstrap e composição

A inicialização ativa instala/compõe módulos como:

```text
performance_patch
scheduler_patch
routine_integration / routine_ui_patch / routine_editing
conversation_layer
quality_patch
academic_intelligence / academic_polish / exam_* / attendance_*
task_context_patch
workout_progress_patch
scheduled_delivery_guard
operational_menu
production_usability_patch
```

`operational_menu.install()` também instala:

```text
goal_operational + família goal_*
course_stage4
```

`course_stage4.install()` enriquece as telas de `course_operational.py` sem criar outra autoridade de persistência.

Nem todo módulo ativo exige `install()`: `short_context.py`, `language_primitives.py`, `correction_patch.py`, `reference_patch.py` e outros entram por chamada/import direto.

---

## 4. Linguagem e contexto

A produção **não usa NLU ampla como roteador central**.

### `language_primitives.py`

Reconhece famílias linguísticas/polaridade sem acessar D1, enviar Telegram ou executar CRUD.

### `short_context.py`

Autoridade de contexto curto:

- isolamento por `user_id`;
- TTL curto;
- alvos recentes;
- listas posicionais na ordem realmente mostrada;
- barreira de mudança explícita de assunto.

Quando uma lista numerada foi apresentada, a posição temporária deve permanecer ligada aos IDs daquela lista, não a uma nova ordenação consultada depois.

### `correction_patch.py`

Corrige alvos recentes seguros sem duplicar registro. Contexto de lista não deve ser tratado como item recém-criado.

Regra geral:

```text
reconhecer linguagem ≠ autorizar escrita
```

---

## 5. Autoridade por domínio

| Domínio | Autoridade / camada principal | Observação |
|---|---|---|
| Dispatcher | `entry.py` | mensagens, callbacks e cron |
| Menu principal | `operational_menu.py` | `app.MAIN_KB` sincronizado como fallback |
| Linguagem comum | `language_primitives.py` | sem efeitos colaterais |
| Contexto curto | `short_context.py` | expiração, referências e isolamento |
| Tarefas | `task_context_patch.py`, `runtime_guard.py`, base `app.py` | seleção posicional preserva lista vista |
| `daily_items` temporais | `reliable_reminders.py` | autoridade temporal única |
| Compromissos | `operational_menu.py` + base `app.py` | aviso temporal em `reliable_reminders.py` |
| Rotinas | `routine_integration.py`, `runtime_guard.py`, `routine_editing.py`, `routine_ui_patch.py` | fluxo guiado |
| Metas | `goal_operational.py` + família `goal_*` | seleção filtrada preserva IDs exibidos |
| Acadêmico | `academic_intelligence.py`, `academic_polish.py`, `exam_*`, `attendance_*` | presença continua explícita |
| Modo Estudo | `study_mode.py` | fim de foco não conclui tópico |
| Cursos — persistência | `course_domain.py` | autoridade única do domínio estruturado |
| Cursos — CRUD | `course_operational.py` | wizard/navegação 4.2 |
| Cursos — progresso/UX | `course_stage4.py` | 4.3–4.5, sem SQL de negócio próprio |
| Cursos ↔ Modo Estudo | `course_study_bridge.py` | ponte explícita entre domínios |
| Importação de Cursos | `course_importer.py` | parser/prévia; persistência via `course_domain.py` |
| Musculação | `workout_progress_patch.py`, base `app.py`, `protocol_mass_data.py` | dados informados, nunca inventados |
| Ler/Ver Depois | `production_usability_patch.py` | backlog simples |
| Clima | `weather_context.py`, `weather_service.py`, `weather_personality.py` | dados objetivos + apresentação |
| Resumos | `reliable_summaries.py` | agenda/resumo persistentes |
| Administração | `admin_diagnostics.py`, `admin_announcement_flow.py` | proprietário |
| Alarmes persistentes | `personal_alarm.py`, `attendance_alarm.py` | Durable Objects |
| Day-off | `day_off_policy.py` + schedulers | política diária |
| Performance | `performance_patch.py` | cache por update |

---

## 6. Cursos estruturados — runtime após Etapa 4.6

Entrada atual:

```text
📘 Cursos
├── 📚 Meus cursos
├── ➕ Novo curso
├── 📥 Importar curso
└── 🗄️ Cursos arquivados
```

Esse domínio é diferente de `🎓 Cursos` em Ler/Ver Depois, que continua sendo apenas backlog.

### Persistência

Migration principal:

```text
0013_courses.sql
```

Tabelas:

```text
courses
course_modules
course_contents
course_materials
course_activities
course_events
```

`course_domain.py` é a autoridade de negócio/persistência. As camadas Telegram não devem escrever SQL concorrente nessas tabelas.

### Progresso

`course_stage4.py` expõe:

```text
▶️ Continuar curso
📊 Progresso
✅ Concluir conteúdo
⏭️ Pular conteúdo
↩️ Voltar para pendente
🏁 Concluir curso
↩️ Reabrir curso
```

Invariantes:

```text
abrir/navegar                 ≠ concluir conteúdo
Continuar curso               ≠ concluir conteúdo
último conteúdo resolvido     ≠ concluir curso
```

Autogerido usa a ordem persistida de módulo/conteúdo. Curso ao vivo respeita `scheduled_at` persistido.

### Ponte com Modo Estudo

Migration:

```text
0014_course_study_links.sql
```

`course_study_bridge.py` cria uma `study_session` vinculada ao conteúdo e registra `course_study_links`.

Invariante:

```text
fim de foco/tópico/sessão de estudo ≠ conclusão do conteúdo do curso
```

A conclusão continua sendo feita explicitamente no domínio de Cursos.

### Importação

`course_importer.py` aceita TXT, PDF textual pesquisável ou texto colado em formato explícito.

Pipeline:

```text
arquivo/texto
→ extração textual
→ parser determinístico
→ validação integral
→ prévia
→ confirmação explícita
→ course_domain.py
```

Linhas ambíguas são recusadas. PDF sem texto pesquisável é recusado; OCR não faz parte do fluxo oficial. A prévia não persiste nada.

---

## 7. Menu atual

Fonte autoritativa: `operational_menu.py`.

```text
➕ Adicionar      | 🗓️ Hoje
🛒 Item faltando | 📚 Matérias
🏠 Cotidiano      | 🏋️ Musculação
📘 Cursos
📖 Manual
🌙 Day-off
```

`🌙 Day-off` permanece sozinho na última linha para reduzir toque acidental.

Este é **o menu atual**, não o menu final. O próximo ponto oficial do roadmap é a reformulação por áreas da vida. Até esse fechamento, não antecipar a Etapa 5.

---

## 8. Scheduler e redundância temporal

Linha primária:

```text
Cloudflare Cron
→ dispatch_scheduled()
→ day_off / attendance / daily_items / routines / summaries / compatibilidade
```

Linha persistente de contingência:

```text
webhook/cron
→ PersonalAlarm por usuário
→ próximo evento persistido
→ alarm()
→ dispatchers autoritativos
```

`AttendanceAlarm` continua separado para presença/aula.

`notification_log` é a barreira central de idempotência. Depois de webhook, reconciliações dos Durable Objects usam `ctx.waitUntil(...)` para não atrasar o `200 OK`.

`reliable_reminders.py` continua sendo a autoridade temporal de `daily_items`.

---

## 9. Performance do caminho quente

`performance_patch.py` reduz round-trips D1 dentro de um update com cache local de:

```text
telegram_chat_id → user_id
user_sessions
```

Esse cache é por update, não persistência global.

Também permanecem:

- gates lexicais antes de consultas irrelevantes;
- DDL defensivo fora do dispatcher geral;
- sincronização global de Durable Objects fora da resposta interativa.

---

## 10. Banco e migrations

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
0009_ru_menu.sql
0010_quick_timers.sql
0011_study_mode.sql
0012_runtime_errors.sql
0013_courses.sql
0014_course_study_links.sql
```

`ensure_schema()` pode existir como tolerância de implantação incremental, mas **não substitui migration**.

Migration destrutiva exige export/backup D1 e plano de rollback.

---

## 11. Código preservado fora do roteamento central

Módulos históricos/experimentais como:

```text
context_router.py
intent_parser.py
action_policy.py
context_memory.py
suggestion_engine.py
deterministic_memory.py
butler_library.py
library_catalog_handler.py
knowledge/
companion_*
conversational_*
```

não formam o roteador central de produção só por existirem no repositório. Reativação futura exige posição explícita no dispatcher, isolamento, política de leitura/escrita e regressão.

A trilha IA/Groq continua **pós-Etapa 11 + gate de estabilidade**.

---

## 12. Testes e deploy

Workflow:

```text
.github/workflows/butler-regression.yml
```

O CI:

1. compila `cloudflare/src`;
2. executa `pytest -q` na regressão determinística.

A Etapa 4 adicionou:

```text
test_stage4_3_course_progress.py
test_stage4_4_course_study_bridge.py
test_stage4_5_course_import.py
test_stage4_6_course_gate.py
```

O gate de código integrado passou no commit `7b41c42d4f151b126f405c7be9bceffcd452b9f9` e a documentação final da branch também passou pelas execuções subsequentes.

**CI verde não prova deploy Cloudflare.** O Worker `salbutler-bot`/Workers Builds precisa ser conferido separadamente após merge quando houver publicação.

---

## 13. Próximo ponto oficial

As subetapas **4.1–4.6 estão concluídas**. O próximo trabalho não é Inbox ainda.

```text
FECHAMENTO DA ETAPA 4
→ reformular menu por áreas da vida
→ regressão de navegação
→ documentação
→ somente então liberar Etapa 5
```

Documento de referência: `docs/ETAPA_4_FECHAMENTO_REFORMULACAO_MENU_AREAS_DA_VIDA.md`.
