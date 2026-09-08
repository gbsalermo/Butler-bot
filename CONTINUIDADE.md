# Continuidade do desenvolvimento — Butler

**Data-base:** 08/09/2026

> Este é o handoff duradouro do projeto. Para andamento exato use `docs/STATUS_ATUAL.md`; para runtime use `docs/ARCHITECTURE.md`; para visão geral use `docs/BUTLER_DOSSIE_MESTRE.md`; para a ordem oficial use `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`.

---

## 1. Objetivo permanente

Butler é um assistente pessoal multiusuário via Telegram para cotidiano, universidade, estudo, cursos, projetos, trabalho, hábitos, treino e interesses.

O produto deve acompanhar o usuário sem virar apenas CRUD/menu e sem executar mudanças silenciosas quando há ambiguidade.

Princípios permanentes:

1. operações críticas são determinísticas;
2. ação explícita vence contexto antigo;
3. não inventar presença, conclusão, gasto, compromisso, treino, progresso ou memória;
4. persistência e estado são isolados por usuário;
5. escrita ambígua exige confirmação quando houver risco;
6. botões e linguagem natural coexistem;
7. contexto auxilia, mas não sequestra mudança de assunto;
8. comportamento novo exige regressão;
9. cada domínio deve possuir autoridade clara;
10. `cloudflare/migrations/` é a fonte formal do schema D1;
11. `ensure_schema()` é apenas tolerância operacional;
12. CI verde não é prova de deploy Cloudflare;
13. não criar, reorganizar nem pular o roadmap oficial por conta própria;
14. existência técnica de uma feature não encerra o trabalho se o fluxo cotidiano continuar excessivamente trabalhoso;
15. reduzir passos nunca autoriza inferência ampla ou escrita silenciosa.

---

## 2. Runtime oficial

```text
Telegram Webhook
→ cloudflare/src/worker.py
→ cloudflare/src/entry.py
→ handlers operacionais
→ D1 / Durable Objects / Telegram Bot API / Open-Meteo
```

A raiz `src/` permanece como runtime histórico polling/SQLite e não governa produção.

Scheduler:

```text
Cloudflare Cron
+ PersonalAlarm
+ AttendanceAlarm
```

`notification_log` é a barreira central de idempotência para entregas agendadas.

---

## 3. Linguagem e contexto

Produção privilegia handlers explícitos/ordenados, módulos de domínio e contexto curto em vez de uma NLU global ampla.

Ativos principais:

```text
language_primitives.py
short_context.py
correction_patch.py
reference_patch.py
compound_router.py
temporal_language.py
```

Regra:

```text
reconhecer linguagem ≠ autorizar escrita
```

Quando uma lista numerada foi exibida, posições temporárias devem continuar vinculadas à lista que o usuário realmente viu, não a uma nova consulta que possa ter mudado de ordem.

---

## 4. Roadmap oficial atual

```text
0. 🧹 Arrumar a casa                         ✅
1. 🗣️ Linguagem natural + conversa real     ✅
2. 🎓 Importação acadêmica confiável         ✅
3. ⏱️ Auxiliares de Tempo / Modo Estudo     ✅
4. 📚 Cursos e trilhas de estudo             ✅
   fechamento: menu por áreas da vida        ✅
5. 📥 Caixa de entrada                       ✅
5.5 ⚡ Usabilidade operacional                ▶️ atual
   5.5.1 Rotinas múltiplas                   ▶️ atual
   5.5.2 Edição direta                       ⏳
   5.5.3 Ações em lote                       ⏳
   5.5.4 Respostas curtas                    ⏳
   5.5.5 Fluxos contínuos                    ⏳
   5.5.6 Gate de UX real                     ⏳
6. 🗂️ Projetos e trabalho                    ⏳ bloqueada
7. 🧭 Resumo/contexto/priorização             ⏳
8. 🧠 Memória + Library seletiva             ⏳
9. 🔒 Hardening                              ⏳
10. 🌐 Abertura pública/capacidade/escala    ⏳
11. 🌍 Idiomas e internacionalização          ⏳
```

A trilha IA/Groq permanece pós-roadmap, somente após Etapa 11 + gate de estabilidade.

---

## 5. Decisão duradoura de 08/09/2026 — Etapa 5.5

Após uso real do produto, foi decidido **não iniciar a Etapa 6 imediatamente após a Inbox**.

Motivo: o Butler já acumulou funcionalidade suficiente, mas alguns fluxos ainda exigem passos demais para operações simples. O roadmap passa a medir também a qualidade operacional do uso cotidiano.

A Etapa 5.5 foi inserida oficialmente entre 5 e 6 com esta ordem:

```text
5.5.1 Rotinas múltiplas e criação contínua
→ 5.5.2 Edição direta
→ 5.5.3 Ações em lote
→ 5.5.4 Respostas curtas
→ 5.5.5 Fluxos contínuos
→ 5.5.6 Gate de UX real
→ Etapa 6
```

Documento detalhado:

```text
docs/ETAPA_5_5_USABILIDADE_OPERACIONAL.md
```

A Etapa 6 permanece bloqueada até o gate 5.5.6.

---

## 6. Domínios consolidados

### Tarefas / compromissos / rotinas / metas

Continuam multiusuário e determinísticos. Seleção numérica deve manter o objeto exibido entre turnos.

A Etapa 5.5 pode melhorar UX, edição direta e lotes, mas não pode criar mutações ambíguas.

### Acadêmico

Modelo:

```text
subjects
subject_sessions
```

Entrada oficial de grade: TXT ou PDF textual pesquisável/selecionável com prévia e confirmação. Presença nunca é presumida.

### Tempo / Modo Estudo

```text
0010_quick_timers.sql
0011_study_mode.sql
```

Quick timer/alerta rápido não vira `daily_items`.

Invariante:

```text
fim de foco/timer ≠ conclusão de tópico
```

### Cursos estruturados

Ativos principais:

```text
0013_courses.sql
0014_course_study_links.sql
course_domain.py
course_operational.py
course_stage4.py
course_study_bridge.py
course_importer.py
```

Invariantes:

```text
abrir/navegar         ≠ concluir
Continuar curso       ≠ concluir
fim do Modo Estudo    ≠ concluir conteúdo
último item resolvido ≠ concluir curso
```

`🎓 Cursos` em Ler/Ver Depois continua sendo backlog simples e não o domínio estruturado `📘 Cursos`.

### Inbox

Migration e autoridade:

```text
0015_inbox.sql
inbox_domain.py
inbox_operational.py
```

Captura não classifica nem executa automaticamente. Conversão para tarefa/compromisso é explícita e idempotente.

---

## 7. Etapa 5.5.1 — decisão de implementação atual

O schema de `routines` já aceita várias rotinas por usuário; não existe constraint que limite uma rotina ativa por usuário.

O primeiro problema corrigido é de linguagem/continuidade de fluxo. Depois de criar uma rotina, formas naturais como:

```text
cria outra rotina de Academia...
adiciona mais uma rotina Curso DIO...
```

passam a ser reconhecidas explicitamente pelo parser de rotina e pelo fast path.

Arquivos do primeiro incremento:

```text
cloudflare/src/routine_natural_fastpath.py
cloudflare/src/core_fast_path.py
cloudflare/tests/test_stage5_5_operational_usability.py
```

O gate 5.5.1 só fecha quando houver regressão completa provando várias rotinas persistidas, listadas, editadas, concluídas e agendadas independentemente.

---

## 8. Banco / migrations atuais

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
0015_inbox.sql
```

Migration destrutiva exige backup/export D1 e plano de rollback. Não usar `ensure_schema()` como substituto de migration.

A Etapa 5.5 deve preferir corrigir fluxo/autoridade existente e não adicionar schema sem necessidade real.

---

## 9. Testes, merge e deploy

Workflow oficial:

```text
.github/workflows/butler-regression.yml
```

Ele compila `cloudflare/src` e roda `pytest -q`.

Regras:

- código novo precisa de regressão;
- PR só deve ser mesclada com CI verde no head final;
- depois do merge, conferir workflow de `main`;
- **CI verde não prova deploy Cloudflare**; `Workers Builds: salbutler-bot` deve ser verificado separadamente.

---

## 10. Próximo trabalho oficial

Continuar **Etapa 5.5.1 — Rotinas múltiplas e criação contínua**.

Ordem:

1. validar CI do primeiro incremento;
2. criar regressão integrada com pelo menos 3 rotinas do mesmo usuário;
3. provar listagem completa;
4. provar edição isolada;
5. provar conclusão isolada;
6. provar scheduler independente por rotina;
7. revisar passos desnecessários do fluxo de criação;
8. fechar 5.5.1;
9. somente então iniciar 5.5.2 — Edição direta.

---

## 11. Regra para a próxima IA/agente

Antes de alterar qualquer coisa:

1. ler `docs/STATUS_ATUAL.md`;
2. ler este `CONTINUIDADE.md`;
3. ler `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`;
4. abrir `docs/ETAPA_5_5_USABILIDADE_OPERACIONAL.md`;
5. confirmar `main`, branch atual e deploy real;
6. identificar o módulo autoritativo do domínio;
7. não criar novo roadmap;
8. não avançar etapa sem gate/regressão da anterior.

**Ponto de retomada: Etapa 5.5.1 — Rotinas múltiplas e criação contínua.**
