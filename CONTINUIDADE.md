# Continuidade do desenvolvimento — Butler

**Data-base:** 01/09/2026

> Este documento é o handoff duradouro do projeto. Para detalhes complementares:
>
> - andamento exato: `docs/STATUS_ATUAL.md`;
> - runtime: `docs/ARCHITECTURE.md`;
> - visão completa: `docs/BUTLER_DOSSIE_MESTRE.md`;
> - roadmap oficial: `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`;
> - decisões pós-roadmap de IA: `docs/POS_ROADMAP_IA.md`;
> - manual de uso: `docs/MANUAL_USUARIO.md`.

---

## 1. Objetivo permanente

Butler é um assistente pessoal multiusuário via Telegram para organização cotidiana, universidade, estudo, cursos, projetos, trabalho, hábitos, treino e interesses.

O produto deve parecer um assistente que acompanha o usuário sem virar apenas CRUD/menu e, principalmente, sem executar ações silenciosas quando existe ambiguidade.

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

Produção:

```text
Telegram Webhook
→ cloudflare/src/worker.py
→ cloudflare/src/entry.py
→ handlers operacionais
→ D1 / Durable Objects / Telegram Bot API / Open-Meteo
```

A raiz `src/` permanece como runtime histórico polling/SQLite e não governa produção.

### Scheduler

O Butler combina:

```text
Cloudflare Cron
+ PersonalAlarm (Durable Object)
+ AttendanceAlarm (Durable Object)
```

`notification_log` é a barreira central de idempotência para entregas agendadas. Falha de um subsistema temporal não deve derrubar os demais.

---

## 3. Linguagem e contexto

Produção privilegia handlers explícitos/ordenados, módulos de domínio e contexto curto em vez de uma NLU global ampla.

Ativos principais:

```text
language_primitives.py
short_context.py
correction_patch.py
compound_router.py
temporal_language.py
```

Regra permanente:

```text
reconhecer linguagem ≠ autorizar escrita
```

Referências recentes/posicionais só devem resolver quando existe contexto curto seguro e pertencente ao mesmo usuário. Quando uma lista numérica foi exibida, posições temporárias devem continuar vinculadas à lista que o usuário realmente viu, não a uma nova consulta que possa ter mudado de ordem.

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

Decisões duradouras:

- `entry.py` governa precedência do dispatcher;
- `operational_menu.py` governa o menu principal;
- `reliable_reminders.py` governa lembretes baseados em `daily_items`;
- schema formal vem de migrations;
- não excluir código apenas por idade/nome sem demonstrar que runtime não depende dele.

### Etapa 1 — Linguagem natural + conversa real ✅

Negação, contexto curto, correções e mensagens compostas devem permanecer conservadores. Uma intenção reconhecida não autoriza escrita silenciosa.

### Etapa 2 — Importação acadêmica confiável ✅

Modelo acadêmico preservado:

```text
subjects
subject_sessions
```

Entrada oficial de grade: TXT ou PDF textual pesquisável/selecionável com prévia e confirmação. Presença nunca é presumida; “vou” não registra presença.

### Etapa 3 — Tempo / Modo Estudo ✅

Migrations:

```text
0010_quick_timers.sql
0011_study_mode.sql
```

Quick timer/alerta rápido não vira `daily_items`.

Invariante permanente do Modo Estudo:

> tópico só avança quando o usuário explicitamente conclui ou pula.

Fim de foco, pausa, restart, Day-off ou passagem de tempo nunca concluem tópico.

---

## 6. Cotidiano e domínios existentes

Tarefas, compromissos, rotinas e metas continuam multiusuário e determinísticos. Seleção numérica deve manter o objeto exibido entre turnos.

O cardápio do RU é compartilhado para leitura, mas a importação/manutenção continua restrita ao proprietário enquanto essa política permanecer documentada.

`Ler/Ver Depois` mantém as categorias simples:

```text
Livros
Filmes
Cursos
Outras
```

**`🎓 Cursos` de Ler/Ver Depois é backlog simples. Nunca reinterpretar silenciosamente como o domínio estruturado `📘 Cursos`.**

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

Tabelas:

```text
courses
course_modules
course_contents
course_materials
course_activities
course_events
```

Autoridade única de negócio/persistência:

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

Regras duradouras:

- `next_content()` não possui efeito colateral;
- autogerido segue posição de módulo/conteúdo;
- ao vivo respeita `scheduled_at` persistido;
- material/atividade não concluem conteúdo;
- curso só termina por ação explícita;
- isolamento por usuário é obrigatório.

Documento: `docs/ETAPA_4_1_MODELO_CURSOS.md`.

### 4.2 — CRUD + navegação ✅

Camada:

```text
cloudflare/src/course_operational.py
```

Entregue:

- criar/editar/arquivar/reativar curso;
- criar/renomear/abrir módulo;
- criar/editar/abrir conteúdo;
- curso ao vivo com `scheduled_at`;
- navegação sem progresso implícito.

Snapshot funcional histórico: `4987327cae69e16d9973bee4a97aa3229c36f5d2`.

Documento: `docs/ETAPA_4_2_CRUD_NAVEGACAO_CURSOS.md`.

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
abrir/navegar          ≠ concluir
Continuar curso        ≠ concluir
último item resolvido  ≠ concluir curso
```

Conclusão do curso exige confirmação explícita.

Documento: `docs/ETAPA_4_3_PROGRESSO_CURSOS.md`.

### 4.4 — Integração com Modo Estudo ✅

Migration:

```text
0014_course_study_links.sql
```

Ponte:

```text
cloudflare/src/course_study_bridge.py
```

Conteúdo pendente de curso ativo pode iniciar:

```text
🧠 Estudar no Modo Estudo
```

Isso cria `study_session` + `course_study_link`, mas mantém o conteúdo `pending`.

Invariantes permanentes:

```text
tempo de foco              ≠ concluir conteúdo
fim do tópico              ≠ concluir conteúdo
fim da sessão              ≠ concluir conteúdo
```

Sessão ativa/pausada não pode ser substituída silenciosamente.

Documento: `docs/ETAPA_4_4_MODO_ESTUDO_CURSOS.md`.

### 4.5 — Importação ✅

Parser/orquestrador:

```text
cloudflare/src/course_importer.py
```

Entrada Telegram:

```text
📥 Importar curso
```

Aceita `.txt`, PDF textual pesquisável ou texto colado no formato explícito:

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
- material/atividade exige conteúdo-pai explícito;
- PDF sem texto pesquisável é recusado; sem OCR;
- plano inteiro é validado antes da escrita;
- sempre mostrar prévia;
- prévia não persiste nada;
- somente confirmação explícita persiste;
- persistência usa funções de `course_domain.py`;
- conteúdos/atividades importados começam pendentes.

Documento: `docs/ETAPA_4_5_IMPORTACAO_CURSOS.md`.

### 4.6 — Gate final ✅

Regressões:

```text
cloudflare/tests/test_stage4_3_course_progress.py
cloudflare/tests/test_stage4_4_course_study_bridge.py
cloudflare/tests/test_stage4_5_course_import.py
cloudflare/tests/test_stage4_6_course_gate.py
```

Gate cobre:

- ordem self-paced;
- calendário live;
- progresso explícito;
- histórico de eventos;
- integração com Modo Estudo sem progresso automático;
- importação com prévia obrigatória;
- isolamento multiusuário.

Evidência de gate de código: commit `7b41c42d4f151b126f405c7be9bceffcd452b9f9`, GitHub Actions `Butler regression` run #286, job `deterministic-regression` concluído com sucesso, incluindo compilação do Worker e suíte determinística.

Documento: `docs/ETAPA_4_6_GATE_FINAL_CURSOS.md`.

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

## 9. Diagnóstico e segurança operacional

Ativos:

```text
/status runtime
/status_runtime
/manual
/ajuda
📖 Manual
```

`runtime_errors` guarda apenas metadados técnicos, nunca o texto da conversa.

Administração e ações com efeito devem continuar com checagem de proprietário/usuário e confirmação quando aplicável.

---

## 10. Testes e merge

Workflow oficial:

```text
.github/workflows/butler-regression.yml
```

Ele compila `cloudflare/src` e roda `pytest -q` na suíte determinística.

Regras:

- código novo precisa de regressão;
- PR só deve ser mesclada com CI verde;
- após commits documentais finais, conferir novamente o head da PR;
- depois do merge, conferir o workflow de `main`;
- **CI verde não prova deploy Cloudflare**; `Workers Builds: salbutler-bot` deve ser verificado separadamente.

---

## 11. Próximo trabalho oficial

A Etapa 4.1–4.6 está concluída. Falta o fechamento obrigatório já previsto no roadmap:

**reorganizar o menu por áreas da vida.**

Essa reorganização deve usar o domínio atual como fonte de verdade, não recriar handlers concorrentes e não reinterpretar `🎓 Cursos` como `📘 Cursos`.

Sequência obrigatória:

1. confirmar merge/CI da PR #45;
2. verificar deploy Cloudflare separadamente;
3. ler `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md` para o formato planejado do fechamento;
4. implementar o menu por áreas da vida;
5. atualizar testes de contrato do menu;
6. rodar regressão completa;
7. atualizar `docs/STATUS_ATUAL.md`, este arquivo, README e arquitetura;
8. somente então liberar a **Etapa 5 — Caixa de entrada**.

Não antecipar Inbox, Projetos, memória seletiva nem IA/Groq antes do ponto correspondente no roadmap.

---

## 12. Regra prática para a próxima IA/agente

Antes de alterar qualquer coisa:

1. ler `docs/STATUS_ATUAL.md`;
2. ler este `CONTINUIDADE.md`;
3. ler `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`;
4. confirmar `main` e deploy real;
5. identificar o módulo autoritativo do domínio;
6. não criar novo roadmap;
7. não avançar etapa sem gate/regressão da anterior.

**Ponto de retomada: fechamento da Etapa 4 — menu por áreas da vida.**
