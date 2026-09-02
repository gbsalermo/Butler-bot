# Butler — Dossiê Mestre

**Data-base:** 01/09/2026  
**Runtime de produção:** Cloudflare Python Worker  
**Estado do roadmap:** Etapas 0–3 concluídas; Etapa 4.1–4.6 concluída; fechamento obrigatório do menu por áreas da vida é o próximo trabalho.

> Para andamento exato: `docs/STATUS_ATUAL.md`.  
> Para runtime técnico: `docs/ARCHITECTURE.md`.  
> Para decisões duradouras: `CONTINUIDADE.md`.  
> Para a ordem futura: `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`.

---

## 1. O que é o Butler

Butler é um assistente pessoal multiusuário via Telegram para organizar:

- cotidiano;
- tarefas e compromissos;
- rotinas e metas;
- universidade;
- estudo e temporizadores;
- cursos/trilhas;
- musculação;
- mercado/itens faltando;
- cardápio do RU;
- clima e resumos;
- interesses para Ler/Ver Depois;
- administração operacional.

O objetivo não é ser apenas um menu de CRUD nem uma IA que decide tudo. O produto combina **Core determinístico + linguagem natural conservadora + contexto curto**.

---

## 2. Princípios de produto

1. operações críticas são determinísticas;
2. ação explícita vence contexto antigo;
3. reconhecer linguagem não autoriza escrita sozinho;
4. presença nunca é presumida;
5. carga/repetições só existem quando informadas;
6. progresso de estudo/curso só muda por ação explícita;
7. dados são isolados por usuário;
8. uma autoridade por domínio;
9. migrations são fonte formal do D1;
10. contexto ajuda, mas não governa;
11. feature nova exige regressão;
12. CI verde não prova deploy Cloudflare;
13. existir no repositório não significa estar ligado ao webhook;
14. uma etapa só termina com gate;
15. Broad NLU/Library/IA preservadas não voltam por conveniência.

---

## 3. Arquitetura de produção

```text
Telegram
→ webhook
→ Cloudflare Python Worker
→ cloudflare/src/worker.py
→ cloudflare/src/entry.py
→ handlers operacionais ordenados
→ D1 / Durable Objects / Telegram Bot API / Open-Meteo
```

A raiz `src/` usa polling/SQLite e é histórica/preservada.

### `worker.py`

- entrypoint Cloudflare;
- integra webhook/cron;
- mantém `AttendanceAlarm` e `PersonalAlarm`;
- reconcilia alarmes persistentes.

### `entry.py`

Orquestrador autoritativo:

```text
dispatch_callback()
dispatch_message()
dispatch_scheduled()
```

Precedência de handlers é contrato e possui regressão.

### `app.py`

Base herdada ainda reutilizada, mas não é automaticamente a autoridade final para símbolos substituídos no bootstrap.

---

## 4. Estado do roadmap

```text
0. 🧹 Arrumar a casa                         ✅
1. 🗣️ Linguagem natural + conversa real     ✅
2. 🎓 Acadêmico + importação confiável       ✅
3. ⏱️ Tempo / Modo Estudo                   ✅
4. 📚 Cursos e trilhas                       ✅ 4.1–4.6
   fechamento: menu por áreas da vida        ▶️ próximo
5. 📥 Caixa de entrada                       ⏳
6. 🗂️ Projetos e trabalho                    ⏳
7. 🧭 Resumo/priorização                      ⏳
8. 🧠 Memória + Library seletiva             ⏳
9. 🔒 Hardening                              ⏳
10. 🌐 Abertura pública/escala               ⏳
11. 🌍 Idiomas e internacionalização          ⏳
```

A Etapa 5 está bloqueada até o fechamento do menu por áreas da vida.

IA/Groq é pós-roadmap, depois da Etapa 11 + gate de estabilidade.

---

## 5. Linguagem natural e contexto

A produção não é governada por uma NLU ampla.

Ativos importantes:

```text
language_primitives.py
short_context.py
correction_patch.py
reference_patch.py
compound_router.py
temporal_language.py
```

### Contexto curto

`short_context.py` mantém:

- alvos recentes;
- listas candidatas;
- referências posicionais;
- isolamento por usuário;
- expiração;
- barreira de mudança de assunto.

Listas numeradas devem manter os IDs da lista realmente exibida ao usuário. Se a ordem no banco mudar entre turnos, `1` continua apontando para o item mostrado como `1` naquele fluxo.

### Correção

Correções seguras do item recém-criado podem atualizar o mesmo registro:

```text
marca dentista amanhã às 15h
não, 16h
```

Contexto de lista não deve ser confundido com item recém-criado.

---

## 6. Cotidiano

### Tarefas

Fluxos distribuídos entre:

```text
task_context_patch.py
runtime_guard.py
app.py
```

Seleção temporal/posicional foi endurecida para não esquecer o item escolhido entre turnos.

### Compromissos

`operational_menu.py` expõe listagem/entrada e a política temporal pertence a `reliable_reminders.py`.

### Rotinas

Família:

```text
routine_integration.py
routine_ui_patch.py
routine_editing.py
runtime_guard.py
```

### Metas

Família `goal_*`, com `goal_operational.py` como camada principal. Seleções em listas filtradas preservam os IDs exibidos.

### Mercado / itens faltando

Fluxos de `grocery_phrase_patch.py`, `quality_patch.py`, `app.py` e menu operacional.

---

## 7. Acadêmico

Modelo preservado:

```text
subjects
subject_sessions
```

Família ativa:

```text
academic_intelligence.py
academic_polish.py
exam_*
attendance_*
```

A importação acadêmica usa TXT ou PDF textual pesquisável/selecionável, com validação, prévia e confirmação.

Regra permanente:

```text
aula prevista ≠ presença
```

---

## 8. Tempo e Modo Estudo

Migrations:

```text
0010_quick_timers.sql
0011_study_mode.sql
```

### Alertas rápidos

Pedidos como “me avisa daqui a 10 minutos” ou cronômetros rápidos usam persistência temporal própria e não precisam poluir `daily_items`.

### Modo Estudo

Autoridade:

```text
study_mode.py
```

Entidades:

```text
study_sessions
study_topics
study_events
```

Regra permanente:

```text
fim de foco/timer ≠ conclusão de tópico
```

O tópico só muda por ação explícita de concluir/pular.

---

## 9. Cursos estruturados — Etapa 4

Entrada:

```text
📘 Cursos
```

Não confundir com `🎓 Cursos` da lista Ler/Ver Depois.

### 9.1 Modelo e autoridade

Migration:

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

Autoridade:

```text
course_domain.py
```

Modos:

```text
self_paced
live
```

Status de conteúdo:

```text
pending
completed
skipped
```

`skipped` é resolvido, não aprendido/concluído.

### 9.2 CRUD/navegação

`course_operational.py` fornece:

- criar/editar curso;
- arquivar/reativar;
- criar/renomear módulos;
- criar/editar conteúdos;
- persistir calendário em curso ao vivo;
- abrir estrutura sem alterar progresso.

### 9.3 Progresso explícito

`course_stage4.py` adiciona:

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
abrir conteúdo               ≠ concluir
Continuar curso              ≠ concluir
tempo gasto                  ≠ concluir
último conteúdo resolvido    ≠ concluir curso
```

`next_content()` é consulta pura.

Curso autogerido segue posição persistida. Curso ao vivo segue `scheduled_at`.

### 9.4 Integração com Modo Estudo

Migration:

```text
0014_course_study_links.sql
```

Ponte:

```text
course_study_bridge.py
```

A ponte cria uma `study_session` ligada ao conteúdo, mas mantém os estados independentes.

```text
fim de foco/tópico/sessão ≠ conclusão do conteúdo do curso
```

Uma sessão ativa/pausada não é substituída silenciosamente.

### 9.5 Importação

`course_importer.py` aceita:

- TXT;
- PDF textual pesquisável;
- texto colado em formato explícito.

Pipeline:

```text
entrada
→ extração textual
→ parser determinístico
→ validação integral
→ prévia
→ confirmação
→ course_domain.py
```

Linhas ambíguas são recusadas. PDF sem texto pesquisável é recusado. OCR não é usado.

Conteúdos/atividades importados começam pendentes.

### 9.6 Gate

Regressões específicas:

```text
test_stage4_3_course_progress.py
test_stage4_4_course_study_bridge.py
test_stage4_5_course_import.py
test_stage4_6_course_gate.py
```

O gate integrado cobre:

- ordem autogerida;
- calendário ao vivo;
- progresso explícito;
- histórico de eventos;
- independência Modo Estudo × progresso de curso;
- importação com prévia;
- isolamento multiusuário.

Gate de código validado no commit `7b41c42d4f151b126f405c7be9bceffcd452b9f9` pelo workflow `Butler regression` run #286.

---

## 10. Musculação

Família principal:

```text
workout_progress_patch.py
protocol_mass_data.py
app.py
```

Carga/repetição só podem ser registradas quando informadas.

Perfis específicos de um usuário não devem ser aplicados automaticamente a outro.

---

## 11. Ler/Ver Depois

Autoridade operacional: `production_usability_patch.py`.

Categorias:

```text
📚 Livros
🎬 Filmes
🎓 Cursos
🗂️ Outras
```

A categoria `🎓 Cursos` continua backlog simples e não é migrada automaticamente para `📘 Cursos`.

---

## 12. Restaurante Universitário

`ru_menu.py` governa consulta/importação do cardápio.

Leitura é compartilhada. A atualização do arquivo permanece exclusiva do proprietário enquanto essa política estiver vigente.

---

## 13. Clima

Módulos:

```text
weather_service.py
weather_context.py
weather_personality.py
```

Open-Meteo fornece dados objetivos. A camada de personalidade pode comentar/apresentar, mas não alterar temperatura, chuva, vento ou probabilidades.

Falha do clima não deve derrubar agenda/resumo.

---

## 14. Scheduler e redundância

Linha primária:

```text
Cloudflare Cron
→ dispatch_scheduled()
```

Linha persistente de contingência:

```text
PersonalAlarm
AttendanceAlarm
```

`notification_log` é barreira de idempotência para evitar duplicidade quando múltiplas fontes temporais convergem.

`reliable_reminders.py` é autoridade temporal de `daily_items`.

Após webhook, reconciliação dos alarmes usa `ctx.waitUntil(...)` para não bloquear o retorno interativo quando aplicável.

---

## 15. Day-off

`day_off_policy.py` e políticas dos schedulers aplicam o descanso diário.

Day-off não apaga nem conclui silenciosamente tarefas, tópicos, conteúdos ou histórico.

O botão permanece isolado na última linha do menu atual para reduzir toque acidental.

---

## 16. Administração

Principais módulos:

```text
admin_diagnostics.py
admin_announcement_flow.py
```

Ações administrativas validam proprietário e, quando necessário, usam prévia/confirmação.

`runtime_errors` guarda metadados técnicos, não o texto completo da conversa.

---

## 17. Menu atual

Fonte: `operational_menu.py`.

```text
➕ Adicionar      | 🗓️ Hoje
🛒 Item faltando | 📚 Matérias
🏠 Cotidiano      | 🏋️ Musculação
📘 Cursos
📖 Manual
🌙 Day-off
```

Este menu ainda **não é o desenho final**. O próximo trabalho oficial é a reorganização por áreas da vida antes da Etapa 5.

---

## 18. Banco de dados

Migrations formais:

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

`ensure_schema()` é proteção operacional, não substituto de migration.

Migration destrutiva exige backup/export D1 e plano de rollback.

---

## 19. Código preservado e futuro

Existem componentes históricos/experimentais como:

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

Eles não devem ser tratados como dispatcher ativo só por existirem.

A Etapa 8 prevê reativação seletiva de memória/Library.

IA/Groq permanece pós-Etapa 10 + estabilidade.

---

## 20. Testes e qualidade

Workflow:

```text
.github/workflows/butler-regression.yml
```

Executa:

1. compilação de `cloudflare/src`;
2. `pytest -q`.

Gate global, conforme aplicável:

- módulo autoritativo definido;
- isolamento multiusuário;
- migration formal;
- estados/cancelamento seguros;
- caso feliz + falso positivo;
- sequência multi-turno;
- CI verde;
- documentação sincronizada;
- deploy verificado separadamente quando necessário.

**CI verde não prova publicação do Worker.**

---

## 21. Próximo trabalho

Etapa 4.1–4.6 está concluída.

Antes da Etapa 5 é obrigatório:

```text
inventariar menus ativos
→ comparar protótipos
→ reorganizar por áreas humanas da vida
→ preservar atalhos/linguagem natural
→ proteger Day-off e ações administrativas
→ testar navegação
→ sincronizar documentação
```

Documento: `docs/ETAPA_4_FECHAMENTO_REFORMULACAO_MENU_AREAS_DA_VIDA.md`.

Somente depois desse fechamento o roadmap libera **Etapa 5 — Caixa de entrada**.
