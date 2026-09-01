# Butler — Status Atual e Handoff

**Data-base:** 01/09/2026  
**Branch de produção:** `main`  
**Etapas 0–3:** ✅ concluídas  
**Etapa 4 — Cursos e trilhas:** ✅ subetapas 4.1–4.6 concluídas  
**Próximo trabalho oficial:** **fechamento obrigatório da Etapa 4 — menu por áreas da vida**  
**PR final da implementação 4.3–4.6:** #46

> Este é o primeiro arquivo para uma nova IA/agente consultar ao assumir o Butler. Para decisões duradouras use `CONTINUIDADE.md`; para runtime use `docs/ARCHITECTURE.md`; para ordem futura use `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`.

---

## 1. O projeto em uma frase

Butler é um assistente pessoal multiusuário via Telegram para cotidiano, universidade, estudos, cursos, projetos e organização pessoal, com operações críticas determinísticas, persistência Cloudflare D1 e serviços temporais redundantes via Durable Objects.

Produção:

```text
Telegram
→ webhook
→ Cloudflare Python Worker
→ cloudflare/src/worker.py
→ cloudflare/src/entry.py
→ handlers operacionais
→ D1 / Durable Objects / Telegram Bot API / Open-Meteo
```

A raiz `src/` é runtime histórico/preservado e não governa produção.

---

## 2. Roadmap oficial

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

**Não avançar para a Etapa 5 antes do fechamento do menu por áreas da vida.**

A trilha de IA/Groq permanece pós-roadmap e só começa depois da Etapa 10 + gate de estabilidade.

---

## 3. Invariantes que não podem ser quebrados

1. reconhecer linguagem não autoriza escrita;
2. presença em aula nunca é presumida;
3. carga/repetições de treino só existem quando informadas;
4. fim de timer do Modo Estudo nunca conclui tópico;
5. tempo gasto em curso nunca conclui conteúdo;
6. `Continuar curso` nunca conclui conteúdo;
7. concluir o último conteúdo nunca conclui o curso silenciosamente;
8. progresso de curso é explícito;
9. prévia de importação não persiste dados;
10. dados são isolados por usuário;
11. migration é fonte formal do D1;
12. `ensure_schema()` é apenas tolerância operacional;
13. CI verde não prova deploy Cloudflare — verificar `Workers Builds: salbutler-bot` separadamente;
14. `🌙 Day-off` permanece sozinho na última linha do menu até o fechamento oficial;
15. `🎓 Cursos` de Ler/Ver Depois é backlog simples e não é o domínio estruturado `📘 Cursos`.

---

## 4. Etapas 0–3 consolidadas

### Linguagem/contexto

Ativos principais:

```text
language_primitives.py
short_context.py
correction_patch.py
compound_router.py
temporal_language.py
```

Contexto curto usa janela limitada, isolamento por usuário e referências recentes/posicionais. NLU ampla histórica não foi religada.

### Acadêmico

Modelo preservado:

```text
subjects
subject_sessions
```

Importação inicial usa TXT ou PDF textual pesquisável/selecionável, com prévia e confirmação. Não usar OCR como caminho oficial.

### Tempo / Modo Estudo

```text
0010_quick_timers.sql
0011_study_mode.sql
quick_timers
study_sessions
study_topics
study_events
```

Tópico de estudo só muda por ação explícita do usuário. Fim de foco/pausa não conclui tópico.

---

## 5. Diagnóstico e manual

Ativos:

```text
/status runtime
/status_runtime
/manual
/ajuda
📖 Manual
```

`runtime_errors` registra somente metadados técnicos; não persiste texto da conversa.

---

## 6. Etapa 4.1 — modelo + autoridade ✅

Migration formal:

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
cloudflare/src/course_domain.py
```

Modos:

```text
self_paced
live
```

Estados de conteúdo:

```text
pending
completed
skipped
```

`skipped` conta como resolvido, mas não como concluído/aprendido.

Documento: `docs/ETAPA_4_1_MODELO_CURSOS.md`.

---

## 7. Etapa 4.2 — CRUD + navegação ✅

Camada operacional:

```text
cloudflare/src/course_operational.py
```

Entrega:

```text
📘 Cursos
├── 📚 Meus cursos
├── ➕ Novo curso
├── 🗄️ Cursos arquivados
└── curso
    ├── módulos: criar / renomear / abrir
    ├── conteúdos: criar / editar / abrir
    ├── editar curso
    └── arquivar / reativar
```

Curso ao vivo persiste `scheduled_at`. Arquivamento preserva estrutura/histórico. O handler Telegram não faz mutações SQL de cursos fora da autoridade.

Snapshot funcional da 4.2: `4987327cae69e16d9973bee4a97aa3229c36f5d2`.

Documento: `docs/ETAPA_4_2_CRUD_NAVEGACAO_CURSOS.md`.

---

## 8. Etapa 4.3 — progresso + Continuar curso ✅

Implementação incremental:

```text
cloudflare/src/course_stage4.py
```

UX entregue:

```text
▶️ Continuar curso
📊 Progresso
✅ Concluir conteúdo
⏭️ Pular conteúdo
↩️ Voltar para pendente
🏁 Concluir curso
↩️ Reabrir curso
```

Regras:

- `Continuar curso` apenas abre `next_content()`;
- autogerido segue posição de módulo/conteúdo;
- ao vivo respeita calendário persistido;
- navegação/duração não alteram progresso;
- último conteúdo resolvido não conclui curso;
- conclusão do curso exige confirmação explícita.

Documento: `docs/ETAPA_4_3_PROGRESSO_CURSOS.md`.

---

## 9. Etapa 4.4 — Cursos ↔ Modo Estudo ✅

Migration formal:

```text
0014_course_study_links.sql
```

Ponte:

```text
cloudflare/src/course_study_bridge.py
```

Fluxo em conteúdo pendente:

```text
🧠 Estudar no Modo Estudo
→ cria study_session
→ cria course_study_link
→ conteúdo continua pending
```

Uma sessão ativa/pausada não é substituída silenciosamente. Concluir tópico ou sessão de estudo não conclui o conteúdo do curso.

Documento: `docs/ETAPA_4_4_MODO_ESTUDO_CURSOS.md`.

---

## 10. Etapa 4.5 — importação ✅

Implementação:

```text
cloudflare/src/course_importer.py
```

Entrada:

```text
📥 Importar curso
```

Aceita `.txt`, PDF textual pesquisável e texto colado em formato explícito.

Estrutura suportada:

```text
CURSO:
TIPO:
DESCRICAO:
[MÓDULO]
[CONTEÚDO]
[MATERIAL]
[ATIVIDADE]
```

O parser recusa linhas ambíguas em vez de inferir. Sempre há prévia; somente `✅ Confirmar importação` persiste. OCR não é usado. Todas as escritas são orquestradas pelas funções de `course_domain.py`.

Documento: `docs/ETAPA_4_5_IMPORTACAO_CURSOS.md`.

---

## 11. Etapa 4.6 — gate final ✅

Regressões novas:

```text
cloudflare/tests/test_stage4_3_course_progress.py
cloudflare/tests/test_stage4_4_course_study_bridge.py
cloudflare/tests/test_stage4_5_course_import.py
cloudflare/tests/test_stage4_6_course_gate.py
```

Gate integrado valida:

- sequência autogerida;
- calendário de curso ao vivo;
- progresso explícito;
- histórico de eventos;
- Modo Estudo separado do progresso do curso;
- importação com prévia;
- isolamento multiusuário.

Evidência de código: no commit `7b41c42d4f151b126f405c7be9bceffcd452b9f9`, o GitHub Actions `Butler regression` run #286 terminou com `success`; compilação do Worker e suíte determinística ficaram verdes.

PR final de merge: **#46**. O draft #45 foi fechado sem merge por limitação do conector ao convertê-lo para Ready e foi substituído pelo #46 com a mesma branch funcional.

Documento: `docs/ETAPA_4_6_GATE_FINAL_CURSOS.md`.

---

## 12. Banco e migrations

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
0009_ru_menu.sql
0010_quick_timers.sql
0011_study_mode.sql
0012_runtime_errors.sql
0013_courses.sql
0014_course_study_links.sql
```

---

## 13. Próximo trabalho exato

**Fechamento obrigatório da Etapa 4 — reorganizar o menu por áreas da vida.**

Não reabrir 4.3–4.6 sem regressão concreta. Não iniciar Etapa 5 ainda.

Ao assumir:

1. confirmar merge/CI do PR #46 em `main`;
2. verificar separadamente o deploy Cloudflare; CI verde não basta;
3. ler `docs/ETAPA_4_6_GATE_FINAL_CURSOS.md`;
4. ler `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md` para a definição do fechamento;
5. executar somente o fechamento do menu por áreas da vida;
6. rodar regressão completa;
7. atualizar este arquivo e `CONTINUIDADE.md`;
8. somente então liberar a Etapa 5 — Caixa de entrada.

**Próximo ponto oficial: fechamento da Etapa 4 — menu por áreas da vida.**
