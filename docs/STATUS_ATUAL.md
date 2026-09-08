# Butler — Status Atual e Handoff

**Data-base:** 08/09/2026  
**Branch de produção:** `main`  
**Branch de trabalho atual:** `feat/etapa-5-5-usabilidade-operacional`  
**Etapas 0–5:** ✅ concluídas  
**Etapa atual:** **5.5 — ⚡ Usabilidade Operacional**  
**Subetapa atual:** **5.5.1 — Rotinas múltiplas e criação contínua**  
**Etapa 6 — Projetos e trabalho:** bloqueada até o gate 5.5.6

> Este é o primeiro arquivo para uma nova IA/agente consultar ao assumir o Butler. Para decisões duradouras use `CONTINUIDADE.md`; para runtime use `docs/ARCHITECTURE.md`; para ordem futura use `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`; para o gate atual use `docs/ETAPA_5_5_USABILIDADE_OPERACIONAL.md`.

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

A trilha de IA/Groq permanece pós-roadmap e só começa depois da Etapa 11 + gate de estabilidade.

---

## 3. Motivo da Etapa 5.5

O produto já possui muitos recursos, mas o teste cotidiano mostrou que a existência técnica não garante uma boa experiência operacional.

Problemas confirmados que passam a bloquear a Etapa 6:

- criar/manter várias rotinas precisa ser natural e confiável;
- edição simples não deve exigir navegar por várias telas quando alvo + alteração já estão claros;
- tarefas/rotinas precisam aceitar ações em lote quando o pedido for explícito;
- confirmações simples devem ser curtas;
- o usuário não deve precisar reentrar no mesmo domínio depois de cada ação simples.

Princípio novo do gate:

```text
feature existente + fluxo ruim = trabalho ainda não fechado
```

Documento autoritativo do gate: `docs/ETAPA_5_5_USABILIDADE_OPERACIONAL.md`.

---

## 4. Invariantes que não podem ser quebrados

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
12. CI verde não prova deploy Cloudflare — verificar `Workers Builds: salbutler-bot` separadamente;
13. `🌙 Day-off` permanece protegido contra toque acidental;
14. `🎓 Cursos` de Ler/Ver Depois é backlog simples e não é o domínio estruturado `📘 Cursos`;
15. ações em lote ou diretas só podem escrever quando os alvos estiverem explícitos/seguros;
16. reduzir passos não autoriza inferência ampla ou silenciosa.

---

## 5. Etapas consolidadas

### Etapas 0–3 ✅

Entregas principais:

- estrutura/runtime estabilizados;
- linguagem natural conservadora + contexto curto;
- domínio acadêmico/importação;
- quick timers;
- Modo Estudo persistente.

### Etapa 4 — Cursos ✅

Modelo estruturado:

```text
Curso
→ módulos
→ conteúdos
→ materiais/atividades
→ progresso explícito
```

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

Fechamento da Etapa 4: menu minimalista por áreas, mergeado pela PR #54.

### Etapa 5 — Inbox ✅

Migration:

```text
0015_inbox.sql
```

Ativos:

```text
inbox_domain.py
inbox_operational.py
core_actions.py
```

Entrega:

- captura por botão/texto;
- pendentes/arquivados;
- processamento explícito;
- conversão para tarefa/compromisso;
- idempotência por `source_inbox_id`;
- isolamento multiusuário.

PR de merge: #57.

---

## 6. Etapa 5.5.1 — trabalho atual

### Problema inicial

O modelo D1 já permite várias linhas em `routines` para o mesmo usuário; não existe unicidade por usuário que limite o cadastro a uma rotina.

O atrito encontrado está no fluxo de linguagem/UX. Um exemplo concreto era a continuação natural:

```text
cria uma rotina de Estudar inglês...
cria outra rotina de Academia...
adiciona mais uma rotina Curso DIO...
```

O parser reconhecia bem a primeira forma, mas `outra rotina` / `mais uma rotina` não tinham contrato explícito equivalente.

### Primeiro incremento já aplicado na branch

Arquivos alterados:

```text
cloudflare/src/routine_natural_fastpath.py
cloudflare/src/core_fast_path.py
cloudflare/tests/test_stage5_5_operational_usability.py
```

Mudança:

- criação natural reconhece `uma`, `outra`, `nova` e `mais uma` rotina;
- `core_fast_path` considera explicitamente qualquer criação de rotina reconhecida pelo parser;
- regressão cobre uma sequência de três pedidos consecutivos.

### Gate restante da 5.5.1

- [ ] criar pelo menos 3 rotinas distintas em sequência no fluxo completo;
- [ ] listar todas as rotinas ativas;
- [ ] editar uma sem alterar as demais;
- [ ] concluir uma sem concluir as demais;
- [ ] scheduler processar cada rotina independentemente;
- [x] parser reconhecer `outra rotina` / `mais uma rotina`;
- [ ] regressão integrada do fluxo completo;
- [ ] CI verde;
- [ ] deploy validado separadamente.

---

## 7. Banco e migrations

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
0015_inbox.sql
```

A Etapa 5.5 não deve criar schema novo sem necessidade real; os problemas atuais são predominantemente de operação/UX.

---

## 8. Próximo trabalho exato

Continuar **somente a Etapa 5.5.1** até o gate de rotinas múltiplas ficar verde.

Próximos passos:

1. validar a branch `feat/etapa-5-5-usabilidade-operacional` em CI;
2. adicionar regressão integrada que simule múltiplas rotinas persistidas para o mesmo usuário;
3. cobrir edição/conclusão isolada por `routine_id`;
4. cobrir scheduler com múltiplas rotinas;
5. revisar fluxo de criação para remover passos desnecessários sem ampliar inferência;
6. mergear/validar deploy;
7. marcar 5.5.1 concluída;
8. iniciar somente então 5.5.2 — Edição direta.

**Próximo ponto oficial: Etapa 5.5.1 — Rotinas múltiplas e criação contínua.**
