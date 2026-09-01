# Continuidade do desenvolvimento — Butler

**Data-base:** 01/09/2026

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
13. não criar, reorganizar nem pular o roadmap oficial por conta própria.

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

## 4. Roadmap oficial

```text
0. 🧹 Arrumar a casa                         ✅
1. 🗣️ Linguagem natural + conversa real     ✅
2. 🎓 Importação acadêmica confiável         ✅
3. ⏱️ Auxiliares de Tempo / Modo Estudo     ✅
4. 📚 Cursos e trilhas de estudo             ▶️ fechamento pendente
   4.1 Modelo + autoridade                   ✅
   4.2 CRUD + navegação                      ✅
   4.3 Progresso / Continuar curso           ✅
   4.4 Integração com Modo Estudo            ✅
   4.5 Importação                            ✅
   4.6 Gate final                            ✅
   fechamento: menu por áreas da vida        ▶️ próximo e obrigatório
5. 📥 Caixa de entrada                       ⏳
6. 🗂️ Projetos e trabalho                    ⏳
7. 🧭 Resumo/contexto/priorização             ⏳
8. 🧠 Memória + Library seletiva             ⏳
9. 🔒 Hardening                              ⏳
10. 🌐 Abertura pública/capacidade/escala    ⏳
```

A trilha IA/Groq permanece pós-roadmap, somente após Etapa 10 + gate de estabilidade.

**Não iniciar Etapa 5 antes do fechamento do menu por áreas da vida.**

---

## 5. Etapas 0–3 consolidadas

### Etapa 0 — Arrumar a casa ✅

- `entry.py` governa precedência do dispatcher;
- `operational_menu.py` governa o menu principal;
- `reliable_reminders.py` governa lembretes de `daily_items`;
- schema formal vem de migrations;
- runtime Cloudflare ativo é separado da raiz histórica.

### Etapa 1 — Linguagem natural + conversa real ✅

Negação, contexto curto, correções e mensagens compostas continuam conservadores. Reconhecer uma intenção não autoriza escrita silenciosa.

### Etapa 2 — Importação acadêmica confiável ✅

Modelo:

```text
subjects
subject_sessions
```

Entrada oficial de grade: TXT ou PDF textual pesquisável/selecionável com prévia e confirmação. Presença nunca é presumida.

### Etapa 3 — Tempo / Modo Estudo ✅

Migrations:

```text
0010_quick_timers.sql
0011_study_mode.sql
```

Quick timer/alerta rápido não vira `daily_items`.

Invariante:

```text
fim de foco/timer ≠ conclusão de tópico
```

---

## 6. Domínios existentes

Tarefas, compromissos, rotinas e metas continuam multiusuário e determinísticos. Seleção numérica deve manter o objeto exibido entre turnos.

O cardápio do RU é compartilhado para leitura, mas manutenção/importação continua restrita ao proprietário enquanto essa política permanecer documentada.

Ler/Ver Depois possui:

```text
📚 Livros
🎬 Filmes
🎓 Cursos
🗂️ Outras
```

**`🎓 Cursos` é backlog simples. Nunca reinterpretar silenciosamente como o domínio estruturado `📘 Cursos`.**

Musculação mantém ficha/progresso por usuário. Carga e repetição só existem quando informadas.

---

## 7. Etapa 4 — Cursos e trilhas

### 4.1 — Modelo + autoridade ✅

Migration:

```text
0013_courses.sql
```

Modelo:

```text
Curso
├── Módulos
│   └── Conteúdos
│       ├── Materiais
│       └── Atividades
└── Eventos / histórico
```

Autoridade única:

```text
cloudflare/src/course_domain.py
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

`skipped` é resolvido, não concluído/aprendido.

### 4.2 — CRUD + navegação ✅

Camada:

```text
cloudflare/src/course_operational.py
```

Entregue: criar/editar/arquivar/reativar curso; módulos; conteúdos; calendário `scheduled_at`; navegação sem progresso implícito.

Snapshot funcional histórico: `4987327cae69e16d9973bee4a97aa3229c36f5d2`.

### 4.3 — Progresso + Continuar curso ✅

Camada incremental:

```text
cloudflare/src/course_stage4.py
```

Operações:

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
abrir/navegar         ≠ concluir
Continuar curso       ≠ concluir
último item resolvido ≠ concluir curso
```

Conclusão do curso exige confirmação explícita.

### 4.4 — Integração com Modo Estudo ✅

Migration:

```text
0014_course_study_links.sql
```

Ponte:

```text
cloudflare/src/course_study_bridge.py
```

Conteúdo pendente de curso ativo pode iniciar Modo Estudo, mas:

```text
tempo de foco ≠ concluir conteúdo
fim do tópico ≠ concluir conteúdo
fim da sessão ≠ concluir conteúdo
```

Sessão ativa/pausada não é substituída silenciosamente.

### 4.5 — Importação ✅

Parser/orquestrador:

```text
cloudflare/src/course_importer.py
```

Entrada Telegram:

```text
📥 Importar curso
```

Aceita TXT, PDF textual pesquisável ou texto colado no formato explícito:

```text
CURSO:
TIPO:
DESCRICAO:
[MÓDULO]
[CONTEÚDO]
[MATERIAL]
[ATIVIDADE]
```

Princípios:

- parser determinístico;
- linha desconhecida/ambígua bloqueia importação;
- PDF sem texto pesquisável é recusado; sem OCR;
- plano inteiro é validado antes da escrita;
- sempre mostrar prévia;
- prévia não persiste nada;
- somente confirmação explícita persiste;
- persistência usa funções de `course_domain.py`;
- conteúdos/atividades importados começam pendentes.

### 4.6 — Gate final ✅

Regressões:

```text
cloudflare/tests/test_stage4_3_course_progress.py
cloudflare/tests/test_stage4_4_course_study_bridge.py
cloudflare/tests/test_stage4_5_course_import.py
cloudflare/tests/test_stage4_6_course_gate.py
```

Gate cobre ordem self-paced, calendário live, progresso explícito, histórico, integração com Modo Estudo sem progresso automático, importação com prévia e isolamento multiusuário.

Evidência de código: commit `7b41c42d4f151b126f405c7be9bceffcd452b9f9`, GitHub Actions `Butler regression` run #286, job `deterministic-regression` verde.

**PR final de merge: #46.** O PR draft #45 foi fechado sem merge por limitação do conector ao convertê-lo para Ready e substituído pelo #46 usando a mesma branch funcional.

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
```

Migration destrutiva exige backup/export D1 e plano de rollback. Não usar `ensure_schema()` como substituto de migration.

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

A Etapa 4.1–4.6 está concluída. Falta o fechamento obrigatório já previsto no roadmap:

**reorganizar o menu por áreas da vida.**

Essa reorganização deve usar os domínios atuais como fonte de verdade, não recriar handlers concorrentes e não reinterpretar `🎓 Cursos` como `📘 Cursos`.

Sequência:

1. confirmar merge/CI do PR #46;
2. verificar deploy Cloudflare separadamente;
3. ler `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md` e o documento do fechamento;
4. implementar o menu por áreas da vida;
5. atualizar testes de contrato do menu;
6. rodar regressão completa;
7. atualizar documentação;
8. somente então liberar a **Etapa 5 — Caixa de entrada**.

---

## 11. Regra para a próxima IA/agente

Antes de alterar qualquer coisa:

1. ler `docs/STATUS_ATUAL.md`;
2. ler este `CONTINUIDADE.md`;
3. ler `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`;
4. confirmar `main` e deploy real;
5. identificar o módulo autoritativo do domínio;
6. não criar novo roadmap;
7. não avançar etapa sem gate/regressão da anterior.

**Ponto de retomada: fechamento da Etapa 4 — menu por áreas da vida.**
