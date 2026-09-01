# Butler — Status Atual e Handoff

**Data-base:** 01/09/2026  
**Branch de produção:** `main`  
**Etapas 0–3:** ✅ concluídas  
**Etapa 4 — Cursos e trilhas:** ▶️ em andamento  
**4.1 — Modelo + autoridade:** ✅ concluída  
**4.2 — CRUD + navegação no Telegram:** ✅ concluída  
**Próxima subetapa oficial:** **4.3 — Progresso e `Continuar curso`**  
**Snapshot funcional da 4.2:** `4987327cae69e16d9973bee4a97aa3229c36f5d2`

> Este é o primeiro arquivo para uma nova IA/agente consultar ao assumir o Butler. Para decisões duradouras use `CONTINUIDADE.md`; para runtime use `docs/ARCHITECTURE.md`; para ordem futura use `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`.

---

## 1. O projeto em uma frase

Butler é um assistente pessoal multiusuário via Telegram para cotidiano, universidade, estudos, projetos e organização pessoal, com operações críticas determinísticas, persistência Cloudflare D1 e serviços temporais redundantes via Durable Objects.

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
4. 📚 Cursos e trilhas de estudo             ▶️ em andamento
   4.1 Modelo + autoridade                   ✅
   4.2 CRUD + navegação                      ✅
   4.3 Progresso / Continuar curso           ▶️ próxima
   4.4 Integração com Modo Estudo            ⏳
   4.5 Importação                            ⏳
   4.6 Gate final                            ⏳
   fechamento: menu por áreas da vida        ⏳ obrigatório
5. 📥 Caixa de entrada                       ⏳
6. 🗂️ Projetos e trabalho                    ⏳
7. 🧭 Resumo/contexto/priorização             ⏳
8. 🧠 Memória + Library seletiva             ⏳
9. 🔒 Hardening                              ⏳
10. 🌐 Abertura pública/capacidade/escala    ⏳
```

A trilha de IA/Groq está documentada como **pós-roadmap** e só começa depois da Etapa 10 + gate de estabilidade. Não antecipar IA para corrigir lacunas das Etapas 0–10.

---

## 3. Invariantes que não podem ser quebrados

1. reconhecer linguagem não autoriza escrita;
2. presença em aula nunca é presumida;
3. carga/repetições de treino só existem quando informadas;
4. fim de timer do Modo Estudo nunca conclui tópico;
5. tempo gasto em curso nunca conclui conteúdo;
6. progresso de curso é explícito;
7. dados são isolados por usuário;
8. migration é fonte formal do D1;
9. `ensure_schema()` é apenas tolerância operacional;
10. CI verde não prova deploy Cloudflare — verificar `Workers Builds: salbutler-bot`;
11. `🌙 Day-off` permanece sozinho na última linha do menu;
12. `🎓 Cursos` de Ler/Ver Depois é backlog simples e não é o domínio estruturado `📘 Cursos`.

---

## 4. Etapas 1–3 já consolidadas

### Linguagem natural

Ativos principais:

```text
language_primitives.py
short_context.py
correction_patch.py
compound_router.py
temporal_language.py
```

Contexto curto usa janela de 30 minutos, isolamento por usuário e referências posicionais/recentes. NLU ampla histórica não foi religada.

### Acadêmico

O modelo atual foi preservado:

```text
subjects
subject_sessions
```

Importação inicial usa TXT ou PDF textual pesquisável/selecionável, com prévia e confirmação. Não usar OCR em produção.

### Tempo

```text
0010_quick_timers.sql
quick_timers
```

Aceita timer/alerta rápido de 1 segundo a 24 horas. Persistência aceita `timer | quick_alert`; a intenção linguística `relative_alert` é normalizada antes do INSERT.

### Modo Estudo

```text
0011_study_mode.sql
study_sessions
study_topics
study_events
```

Tópico só muda por `concluí`/`pular` explícitos.

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

O manual só abre se a intenção de ajuda for explícita. Botões como `Cotidiano`, `Matérias` e `Musculação` não podem ser sequestrados pelo handler do manual.

Após alertas efêmeros, respostas sociais como `valeu`, `desliguei`, `já foi`, `feito` podem ser reconhecidas em contexto curto, mas são opcionais e nunca impedem a entrega do alerta.

---

## 6. Etapa 4.1 — modelo de Cursos

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

## 7. Etapa 4.2 — CRUD e navegação concluídos

Nova camada operacional:

```text
cloudflare/src/course_operational.py
```

Entrada no menu:

```text
📘 Cursos
```

Fluxos entregues:

```text
📘 Cursos
├── 📚 Meus cursos
├── ➕ Novo curso
├── 🗄️ Cursos arquivados
└── abrir curso
    ├── 🧩 módulos
    │   ├── criar
    │   ├── renomear
    │   └── abrir
    ├── 📄 conteúdos
    │   ├── criar
    │   ├── editar nome/tipo/data
    │   └── abrir
    ├── ✏️ editar curso
    └── 🗄️ arquivar / ♻️ reativar
```

Criação de curso pergunta:

1. nome;
2. `Autogerido` ou `Ao vivo`;
3. descrição opcional.

Curso ao vivo pode guardar data/horário por conteúdo.

Arquivamento preserva estrutura/histórico e substitui hard delete operacional nesta etapa.

`course_domain.py` foi ampliado com:

```text
list_courses()
get_course()
update_course()
rename_module()
update_content()
content_details()
```

O handler Telegram não faz mutações SQL de cursos fora da autoridade.

Regressão da PR funcional: **366 testes passando**.

Documento: `docs/ETAPA_4_2_CRUD_NAVEGACAO_CURSOS.md`.

---

## 8. O que a Etapa 4.2 NÃO faz

Não antecipar:

```text
concluir/pular conteúdo
voltar conteúdo para pendente
Continuar curso
concluir curso no Telegram
integração com Modo Estudo
importação de curso/material
reorganização final do menu
```

A tela de curso pode mostrar `progress_summary()`, mas na 4.2 esse progresso é somente leitura.

---

## 9. Banco e migrations

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
```

---

## 10. Próximo trabalho exato — Etapa 4.3

**Progresso e `Continuar curso`.**

A base já existe no domínio:

```text
set_content_status()
next_content()
progress_summary()
set_course_status()
```

A 4.3 deve expor UX segura para:

```text
✅ concluir conteúdo
⏭️ pular conteúdo
↩️ voltar para pendente
▶️ continuar curso
📊 ver progresso
🏁 concluir curso explicitamente
```

Regras obrigatórias:

- nenhuma navegação altera progresso;
- nenhuma duração altera progresso;
- `Continuar curso` apenas encontra/abre o próximo pendente;
- curso autogerido segue posição de módulo/conteúdo;
- curso ao vivo respeita calendário persistido;
- conclusão do último conteúdo não deve concluir o curso silenciosamente;
- qualquer conclusão do curso precisa de ação explícita.

A integração com Modo Estudo só entra na **4.4**.

---

## 11. Instrução para a próxima IA/agente

1. confirmar `main` e deploy do snapshot funcional da 4.2;
2. ler `CONTINUIDADE.md`;
3. ler `docs/ETAPA_4_1_MODELO_CURSOS.md`;
4. ler `docs/ETAPA_4_2_CRUD_NAVEGACAO_CURSOS.md`;
5. iniciar **4.3 — Progresso e `Continuar curso`**;
6. reutilizar `course_domain.py`, não criar autoridade paralela;
7. preservar progresso explícito;
8. não integrar Modo Estudo antes da 4.4;
9. não reinterpretar `🎓 Cursos` de Ler/Ver Depois;
10. não avançar para 4.4 sem gate/regressão da 4.3.

**Próximo ponto oficial: Etapa 4.3.**
