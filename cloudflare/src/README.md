# Mapa de módulos — `cloudflare/src`

**Data-base:** 01/09/2026

Este diretório contém o runtime de produção do Butler em Cloudflare Python Worker.

> Em dúvida, leia primeiro `../../docs/STATUS_ATUAL.md`, depois `entry.py` e `../../docs/ARCHITECTURE.md`. **Existir neste diretório não significa estar ativo no webhook.**

---

## Entrypoints

### `worker.py`

Entrypoint Cloudflare. Integra webhook/cron e Durable Objects temporais.

### `entry.py`

Orquestrador autoritativo do runtime:

```text
dispatch_callback()
dispatch_message()
dispatch_scheduled()
```

A precedência dos handlers é contrato de produção e possui regressão.

### `app.py`

Base histórica ainda reutilizada por vários fluxos. Não é automaticamente a autoridade final de tudo que contém, porque o bootstrap instala/substitui componentes mais específicos.

---

## Menu e navegação

### `operational_menu.py`

Autoridade do menu principal atual e ponto de entrada operacional de domínios como Cotidiano, Metas e Cursos.

Também instala/despacha `course_stage4` antes do handler CRUD-base de Cursos.

### `production_usability_patch.py`

Usabilidade transversal, Ler/Ver Depois e sincronização de menus/fallbacks.

### `navigation_patch.py` / módulos de navegação relacionados

Tratam retorno e navegação global onde aplicável.

O próximo ponto oficial do roadmap é reorganizar o menu por áreas da vida. Não antecipar a Etapa 5 dentro destes módulos.

---

## Linguagem e contexto

### `language_primitives.py`

Famílias linguísticas/polaridade sem efeitos colaterais.

### `short_context.py`

Autoridade de contexto curto, referências recentes e listas posicionais.

### `reference_patch.py`

Resolve referências seguras para alvos recentes.

### `correction_patch.py`

Auto-reparo do item recém-criado/corrigido sem duplicar.

### `temporal_language.py`

Primitivas de interpretação temporal compartilhadas.

### `compound_router.py`

Estrutura de mensagens compostas conforme integração ativa.

Regra permanente:

```text
reconhecer texto ≠ autorizar escrita
```

---

## Tarefas, compromissos e lembretes

### `task_context_patch.py`

Listagem/contexto de tarefas e seleção numérica ligada à lista realmente exibida.

### `runtime_guard.py`

Fluxos guiados e operações determinísticas de tarefas/rotinas.

### `reliable_reminders.py`

Autoridade temporal de `daily_items`.

### `notification_ack.py`

Reconhecimento contextual de confirmações sociais após alertas efêmeros, sem substituir as ações persistentes dos domínios.

---

## Rotinas e metas

Rotinas:

```text
routine_integration.py
routine_editing.py
routine_ui_patch.py
```

Metas:

```text
goal_operational.py
goal_polish.py
goal_deadline_patch.py
goal_routine_bridge.py
goal_natural_patch.py
```

Listas filtradas devem preservar IDs/ordem exibidos durante seleção por posição.

---

## Acadêmico e presença

Família ativa inclui:

```text
academic_intelligence.py
academic_polish.py
exam_cancel_patch.py
attendance_patch.py
attendance_enhancement.py
attendance_management.py
attendance_production_fix.py
attendance_alarm.py
```

Presença nunca é presumida apenas pelo horário da aula.

Importação acadêmica oficial usa PDF textual/TXT com prévia e confirmação.

---

## Quick timers / Modo Estudo

### `study_mode.py`

Autoridade de sessões/tópicos do Modo Estudo.

Invariante:

```text
fim de foco/timer ≠ conclusão de tópico
```

### Quick timers

A infraestrutura temporal persistente de alertas rápidos usa a migration `0010_quick_timers.sql` e os dispatchers correspondentes. Alertas rápidos não viram tarefas normais.

---

## Cursos estruturados — Etapa 4.1–4.6

### `course_domain.py`

**Autoridade única de negócio/persistência de Cursos.**

Responsável por curso, módulos, conteúdos, materiais, atividades, eventos, progresso e busca do próximo conteúdo.

Migration principal:

```text
0013_courses.sql
```

### `course_operational.py`

CRUD/navegação Telegram da Etapa 4.2:

- criar/editar/arquivar/reativar curso;
- módulos;
- conteúdos;
- calendário de curso ao vivo.

Não deve escrever SQL concorrente ao domínio.

### `course_stage4.py`

Extensão operacional das Etapas 4.3–4.5:

```text
▶️ Continuar curso
📊 Progresso
✅ Concluir conteúdo
⏭️ Pular conteúdo
↩️ Voltar para pendente
🏁 Concluir / ↩️ Reabrir curso
🧠 Estudar no Modo Estudo
📥 Importar curso
```

Ele coordena UX/estado e chama as autoridades adequadas.

### `course_study_bridge.py`

Ponte Cursos ↔ Modo Estudo.

Cria sessão de estudo e vínculo persistido em:

```text
0014_course_study_links.sql
course_study_links
```

Não sincroniza conclusão automaticamente.

### `course_importer.py`

Parser/importador determinístico de TXT/PDF textual/texto colado.

Pipeline:

```text
entrada
→ parser
→ validação
→ prévia
→ confirmação
→ course_domain
```

Linhas ambíguas e PDF sem texto pesquisável são recusados. OCR não faz parte do fluxo oficial.

Invariantes de Cursos:

```text
abrir/navegar                 ≠ concluir conteúdo
Continuar curso               ≠ concluir conteúdo
tempo/fim do Modo Estudo      ≠ concluir conteúdo
último conteúdo resolvido     ≠ concluir curso
prévia de importação          ≠ persistir
```

---

## Musculação

Módulos principais incluem:

```text
workout_progress_patch.py
protocol_mass_data.py
```

e integração-base em `app.py`.

Carga e repetições só existem quando informadas.

---

## Mercado / itens faltando

Fluxos usam `grocery_phrase_patch.py`, `quality_patch.py`, base `app.py` e entrada de `operational_menu.py` conforme o caso.

---

## Ler/Ver Depois

`production_usability_patch.py` governa o backlog simples.

Categorias:

```text
📚 Livros
🎬 Filmes
🎓 Cursos
🗂️ Outras
```

`🎓 Cursos` aqui **não é** `📘 Cursos` estruturado.

---

## RU

### `ru_menu.py`

Consulta/importação operacional do cardápio.

Leitura é compartilhada; manutenção/importação permanece restrita ao proprietário enquanto essa política estiver documentada.

---

## Clima e resumos

Clima:

```text
weather_context.py
weather_service.py
weather_personality.py
```

`weather_personality.py` pode alterar apresentação/comentário, nunca os dados objetivos.

Resumos:

```text
reliable_summaries.py
```

Falha meteorológica não deve derrubar agenda/resumos.

---

## Scheduler / Durable Objects

Principais componentes:

```text
scheduler_runtime.py
personal_alarm.py
attendance_alarm.py
reliable_reminders.py
scheduled_delivery_guard.py
```

Cron + Durable Objects devem convergir para as mesmas autoridades e barreiras de idempotência.

`notification_log` continua central para evitar duplicidade de entregas.

---

## Administração e diagnóstico

```text
admin_diagnostics.py
admin_announcement_flow.py
runtime_errors / diagnóstico relacionado
```

Ações administrativas devem validar proprietário.

`runtime_errors` guarda metadados técnicos, não conversa completa.

---

## Performance

### `performance_patch.py`

Cache por update de informações como:

```text
telegram_chat_id → user_id
user_sessions
```

Não é cache persistente global.

---

## Código preservado/experimental

Arquivos como:

```text
context_router.py
intent_parser.py
action_policy.py
context_memory.py
suggestion_engine.py
deterministic_memory.py
butler_library.py
library_catalog_handler.py
companion_*
conversational_*
```

podem existir sem integrar o roteador central.

Não religue Broad NLU/Library genérica por conveniência. Qualquer reativação futura precisa de caso de uso, precedência, isolamento, política de escrita e regressão.

A trilha IA/Groq permanece pós-Etapa 10 + gate de estabilidade.

---

## Migrations atuais

Fonte formal: `../migrations/`.

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

`ensure_schema()` é somente tolerância operacional.

---

## Testes

A partir de `cloudflare/`:

```bash
pytest -q
```

A Etapa 4 possui regressões dedicadas:

```text
test_stage4_3_course_progress.py
test_stage4_4_course_study_bridge.py
test_stage4_5_course_import.py
test_stage4_6_course_gate.py
```

O GitHub Actions também compila `src` antes da regressão.

**CI verde não prova deploy do Worker.** Verifique Workers Builds separadamente depois do merge.

---

## Antes de criar novo módulo

Pergunte:

```text
Qual é o módulo dono?
A mudança cabe nele?
É realmente uma fronteira entre domínios?
Quem chama esse novo módulo?
Em qual posição do dispatcher?
Que estado/persistência ele usa?
Qual teste prova que está ativo?
```

Se essas respostas não estiverem claras, não crie outro patch.
