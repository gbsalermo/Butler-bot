# Continuidade do desenvolvimento — Butler

**Data-base:** 01/09/2026

> Este documento é o handoff duradouro do projeto. Para detalhes complementares:
>
> - status/handoff técnico: `docs/STATUS_ATUAL.md`;
> - runtime: `docs/ARCHITECTURE.md`;
> - visão completa: `docs/BUTLER_DOSSIE_MESTRE.md`;
> - roadmap oficial: `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`;
> - decisões pós-roadmap de IA: `docs/POS_ROADMAP_IA.md`;
> - manual de uso: `docs/MANUAL_USUARIO.md`.

---

## 1. Objetivo permanente

Butler é um assistente pessoal via Telegram para organização cotidiana, universidade, estudo, projetos, trabalho, hábitos, treino e interesses.

O objetivo de produto é parecer um assistente que acompanha o usuário, sem virar apenas CRUD/menu e sem executar ações silenciosamente quando há ambiguidade.

Princípios permanentes:

1. operações críticas são determinísticas;
2. ação explícita vence contexto antigo;
3. não inventar presença, conclusão, gasto, compromisso, treino, progresso ou memória;
4. persistência e estado são isolados por usuário;
5. escrita ambígua exige confirmação quando houver risco;
6. botões e linguagem natural coexistem;
7. contexto auxilia, mas não sequestra mudança de assunto;
8. comportamento novo exige regressão;
9. cada domínio deve ter uma autoridade clara de negócio/persistência;
10. `cloudflare/migrations/` é a fonte formal do schema D1;
11. CI verde não deve ser confundido com deploy Cloudflare validado;
12. não criar ou reorganizar roadmap por conta própria quando existe etapa oficial aberta.

---

## 2. Runtime oficial

Produção:

```text
Telegram Webhook
→ Cloudflare Python Worker
→ D1 / Durable Objects
→ Telegram Bot API
```

Entrypoints:

```text
cloudflare/src/worker.py
cloudflare/src/entry.py
```

A raiz `src/` continua preservada como runtime histórico polling/SQLite e não governa produção.

### Scheduler e redundância

O Butler combina:

```text
Cloudflare Cron
+
PersonalAlarm (Durable Object)
+
AttendanceAlarm (Durable Object)
```

`notification_log` é a autoridade central de idempotência para entregas agendadas. Após webhook, reconciliações persistentes devem usar `ctx.waitUntil(...)` para não atrasar a resposta interativa. Falha de um subsistema não deve derrubar os demais.

---

## 3. Arquitetura de linguagem e contexto

Uma geração anterior tentou centralizar linguagem/contexto em módulos globais como `context_router.py`, `intent_parser.py`, `action_policy.py`, `context_memory.py` e `suggestion_engine.py`. Eles podem permanecer preservados, mas **não são o roteador central do webhook atual**.

A produção privilegia handlers explícitos e ordenados, `language_primitives.py` como base linguística sem efeitos colaterais, `short_context.py` como autoridade do contexto curto, estados guiados, módulos autoritativos por domínio e fallback estreito.

Regra permanente:

```text
reconhecer linguagem
≠
autorizar escrita
```

`short_context.py` mantém contexto por usuário com TTL curto, referências recentes/posicionais e barreira contra mudança explícita de assunto. `correction_patch.py` corrige alvos recentes seguros sem duplicar. `compound_router.py` só cria lotes quando todas as ações são determinísticas e válidas.

---

## 4. Etapa 0 — Arrumar a casa ✅

Concluída.

Decisões permanentes:

- `entry.py` governa precedência do dispatcher;
- `operational_menu.py` governa o menu principal;
- `reliable_reminders.py` governa lembretes baseados em `daily_items`;
- schema formal vem de migrations;
- não excluir código apenas por idade/nome sem demonstrar que runtime não depende dele;
- evitar novas cadeias de patches paralelos quando existe módulo autoritativo.

---

## 5. Etapa 1 — Linguagem natural + conversa real ✅

Concluída.

Invariantes principais:

```text
não me lembra de estudar hoje
→ não cria lembrete

me lembra de não estudar hoje
→ lembrete positivo; a negação pertence ao conteúdo

não deixa eu esquecer...
→ pedido positivo de lembrete
```

```text
preciso pagar a conta
→ pode ser tarefa

preciso de ajuda com cálculo
→ não deve virar tarefa
```

Referências curtas só funcionam quando existe alvo recente seguro. Lotes determinísticos de 2–5 tarefas/compromissos/lembretes podem ter prévia e confirmação conjunta.

Documento final: `docs/ETAPA_1_6_GATE_FINAL.md`.

---

## 6. Etapa 2 — Importação acadêmica confiável ✅

Concluída.

**Decisão de produto:** o domínio acadêmico atual foi considerado suficiente e não foi remodelado.

```text
subjects
→ name
→ active/locked

subject_sessions
→ weekday
→ start_time
→ end_time
→ location
```

A importação de primeiro acesso segue:

```text
SIGAA
↓
PDF textual ou TXT
↓
extração
↓
validação
↓
prévia
↓
confirmação
↓
tabelas existentes
```

Fonte recomendada:

```text
Componente Curricular | Local | Horário
```

Aceitos em produção: PDF pesquisável/selecionável e TXT. Não usar OCR como formato oficial.

### Presença/faltas

Aulas são previstas; presença nunca é presumida. **“vou” não persiste presença.** Somente ausência/resposta explícita gera registro conforme as regras existentes.

---

## 7. Etapa 3 — Auxiliares de Tempo / Modo Estudo ✅

### 3A — Alertas rápidos e cronômetros

Migration:

```text
0010_quick_timers.sql
```

Tipos persistidos:

```text
timer
quick_alert
```

`relative_alert` é apenas intenção linguística e deve ser normalizada para `quick_alert` antes do INSERT. Horizonte rápido: 1 segundo a 24 horas. Quick timer não vira tarefa em `daily_items`.

Após um aviso efêmero, respostas como `valeu`, `já foi`, `desliguei`, `feito` e `resolvido` podem ser reconhecidas opcionalmente em contexto curto. Essa camada é best-effort e nunca pode impedir o disparo do alerta.

### 3B — Modo Estudo

Migration:

```text
0011_study_mode.sql
```

Tabelas:

```text
study_sessions
study_topics
study_events
```

Invariante permanente:

> **Tópico só avança quando o usuário explicitamente conclui ou pula.**

Portanto fim de foco, pausa, restart ou Day-off nunca concluem tópico.

---

## 8. Diagnóstico de runtime e manual

Migration de diagnóstico:

```text
0012_runtime_errors.sql
```

Comando proprietário:

```text
/status runtime
```

`runtime_errors` guarda somente metadados técnicos, nunca o texto da conversa.

Manual completo: `docs/MANUAL_USUARIO.md`.

Ajuda rápida:

```text
/manual
/ajuda
manual
📖 Manual
```

Categorias do manual só abrem com intenção explícita de ajuda. Aliases soltos como `Cotidiano`, `Matérias` e `Musculação` não podem sequestrar botões operacionais.

No menu principal:

- `📖 Manual` permanece em linha própria;
- `🌙 Day-off` permanece sozinho na última linha para reduzir clique acidental.

---

## 9. Musculação

O perfil proprietário preserva o Protocol Mass de 12 semanas; usuários genéricos podem possuir ficha própria.

Regras permanentes:

- não aplicar protocolo pessoal a outro usuário;
- registrar carga/repetição somente quando informadas;
- substituição não apaga histórico;
- evolução usa dados realmente registrados;
- “não consegui treinar hoje” não inventa séries;
- exercício substituído mantém rastreabilidade do original.

---

## 10. Cotidiano, RU e Ler/Ver Depois

A lista de itens faltando é persistente. O cardápio do RU é compartilhado para leitura, mas atualização/importação fica restrita ao proprietário.

`Ler/Ver Depois` mantém:

```text
Livros
Filmes
Cursos
Outras
```

**A categoria `🎓 Cursos` de Ler/Ver Depois é somente backlog simples.** Não migrar nem reinterpretar silenciosamente como o domínio estruturado `📘 Cursos`.

---

## 11. Etapa 4 — Cursos e trilhas de estudo ▶️ EM ANDAMENTO

### 4.1 — Modelo + autoridade ✅

Implementação:

```text
cloudflare/migrations/0013_courses.sql
cloudflare/src/course_domain.py
docs/ETAPA_4_1_MODELO_CURSOS.md
```

Modelo:

```text
Curso
│
├── Módulos
│   └── Conteúdos
│       ├── Materiais
│       └── Atividades
│
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

Tipos:

```text
self_paced
live
```

Regras permanentes:

- ordenação de módulos/conteúdos é explícita;
- curso autogerido segue a primeira pendência pela ordem persistida;
- curso ao vivo respeita calendário persistido e não desloca aula sozinho;
- status de conteúdo: `pending`, `completed`, `skipped`;
- `skipped` conta como resolvido, não como concluído/aprendido;
- `next_content()` é consulta sem efeito colateral;
- material/atividade não concluem conteúdo automaticamente;
- tempo no Modo Estudo não conclui conteúdo;
- curso só termina por ação explícita;
- isolamento por usuário é obrigatório.

### 4.2 — CRUD + navegação no Telegram ✅

Implementação funcional:

```text
cloudflare/src/course_operational.py
cloudflare/src/course_domain.py
cloudflare/src/operational_menu.py
cloudflare/tests/test_stage4_2_course_operational.py
```

PR funcional: **#43**  
Merge funcional: `4987327cae69e16d9973bee4a97aa3229c36f5d2`  
Gate: **366 testes passando**.

Entrada operacional:

```text
📘 Cursos
├── 📚 Meus cursos
├── ➕ Novo curso
├── 🗄️ Cursos arquivados
└── abrir curso
```

Criação pergunta:

1. nome;
2. `🧭 Autogerido` ou `📡 Ao vivo`;
3. descrição opcional.

A tela do curso mostra estrutura e progresso somente para leitura nesta subetapa.

Operações disponíveis:

```text
curso
├── editar nome
├── editar descrição
├── trocar self_paced/live
├── arquivar
└── reativar

módulo
├── criar
├── abrir
└── renomear

conteúdo
├── criar
├── abrir
├── editar nome
├── editar tipo
└── editar data/horário
```

Tipos de conteúdo:

```text
lesson
reading
exercise
project
review
other
```

Curso ao vivo pode registrar `scheduled_at`; entrada humana aceita `DD/MM/AAAA HH:MM` e persiste normalizada.

#### Arquivamento

A 4.2 usa **arquivar**, não hard delete operacional:

```text
active/paused/completed
→ confirmação
→ archived
```

Estrutura e histórico permanecem. Curso arquivado pode voltar para `active` por ação explícita.

#### Autoridade

`course_domain.py` continua sendo a única autoridade de persistência de Cursos. A 4.2 adicionou:

```text
list_courses()
get_course()
update_course()
rename_module()
update_content()
content_details()
```

`course_operational.py` mantém apenas diálogo/wizard e chama a autoridade para escrita.

#### Invariantes da 4.2

```text
abrir conteúdo  ≠ concluir
editar conteúdo ≠ concluir
navegar          ≠ progresso
passar o tempo   ≠ progresso
criar módulo     ≠ avançar curso
```

O wizard cancelado não deve deixar uma criação parcial quando o curso ainda não foi persistido. Todos os acessos respeitam o proprietário do curso.

Documento: `docs/ETAPA_4_2_CRUD_NAVEGACAO_CURSOS.md`.

### Próxima subetapa: 4.3 — Progresso + `Continuar curso`

A base já existe:

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

- `Continuar curso` só consulta/abre o próximo pendente;
- nenhuma duração ou navegação altera progresso;
- autogerido segue posição de módulo/conteúdo;
- ao vivo respeita `scheduled_at` persistido;
- último conteúdo concluído não conclui o curso silenciosamente;
- conclusão do curso exige ação explícita;
- integração com Modo Estudo só começa na 4.4.

Sequência restante:

```text
✅ 4.1 Modelo + autoridade
✅ 4.2 CRUD + navegação
▶️ 4.3 Progresso + Continuar curso
⏳ 4.4 Integração com Modo Estudo
⏳ 4.5 Importação de cursos/material
⏳ 4.6 Gate final
⏳ Fechamento: menu por áreas da vida
```

A reformulação do menu por áreas da vida é **obrigatória ao final da Etapa 4 e antes da Etapa 5**.

---

## 12. Projetos, Inbox e priorização

Compromissos futuros:

- Caixa de entrada para captura rápida sem classificação imediata;
- Projetos/Trabalho com estado, próximos passos, bloqueios e “onde parei?”;
- priorização do dia/semana baseada em regras explicáveis e dados reais;
- integração posterior com cursos, agenda, clima, rotinas e pendências.

Não implementar antes dos gates oficiais.

---

## 13. Library e conhecimento

Os acervos de culinária, jogos, cultura pop, livros e filosofia continuam preservados para etapa própria.

Library pode sugerir, mas ação persistente pertence ao Core. A Library genérica continua fora do dispatcher principal até reativação seletiva planejada.

---

## 14. Clima

Open-Meteo continua sendo a fonte objetiva. Camadas de personalidade podem acrescentar comentário humano, mas nunca inventar dados meteorológicos. Falha de clima não derruba agenda/resumo.

---

## 15. Multiusuário e proprietário

Toda persistência pessoal é isolada por usuário. A barreira `is_owner(chat_id)` não deve ser removida sem mecanismo equivalente. Recursos administrativos permanecem exclusivos do proprietário.

---

## 16. Banco e migrations

Disciplina obrigatória:

1. migration versionada;
2. backfill explícito quando necessário;
3. índice quando a consulta justificar;
4. `ensure_schema()` somente como tolerância operacional;
5. testes;
6. documentação.

Migrations atuais:

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

Migration destrutiva exige snapshot/export D1 e plano de rollback.

---

## 17. Testes e deploy

A suíte em `cloudflare/tests/` protege o caminho realmente alcançado pelo dispatcher.

Último gate funcional da Etapa 4.2:

```text
366 testes passando
```

A regressão da 4.2 encontrou e corrigiu antes do merge:

1. tentativa de colocar `📖 Manual` na mesma linha de Cursos, quebrando proteção de UX;
2. estado de wizard recuperado tarde demais em chamadas isoladas;
3. variation selector invisível do emoji `🗄️`, que impedia reabrir curso arquivado.

Sempre preservar:

```text
GitHub Actions verde
≠ automaticamente produção validada
```

Após mudança de runtime, verificar também `Workers Builds: salbutler-bot`.

---

## 18. Ordem oficial de evolução

```text
0. 🧹 Arrumar a casa                         ✅
1. 🗣️ Linguagem natural + conversa real     ✅
2. 🎓 Importação acadêmica confiável         ✅
3. ⏱️ Auxiliares de Tempo / Modo Estudo     ✅
4. 📚 Cursos e trilhas de estudo             ▶️ em andamento
   4.1 Modelo + autoridade                   ✅
   4.2 CRUD + navegação                      ✅
   4.3 Progresso / continuar curso           ▶️ próxima
   4.4 Integração com Modo Estudo            ⏳
   4.5 Importação                            ⏳
   4.6 Gate final                            ⏳
   fechamento: menu por áreas da vida        ⏳
5. 📥 Caixa de entrada                       ⏳
6. 🗂️ Projetos e trabalho                    ⏳
7. 🧭 Resumo/contexto/priorização             ⏳
8. 🧠 Memória + Library seletiva             ⏳
9. 🔒 Hardening                              ⏳
10. 🌐 Abertura pública/capacidade/escala    ⏳
```

---

## 19. IA — somente pós-roadmap

Decisão registrada em `docs/POS_ROADMAP_IA.md`.

**Não iniciar integração de IA durante as Etapas 0–10.**

```text
concluir roadmap 0–10
↓
estabilizar produção
↓
passar gate de estabilidade
↓
iniciar trilha de IA
```

Provedor inicial pretendido: **Groq**, por API em nuvem, dentro do free tier se ainda estiver disponível quando a trilha começar. O modelo específico será reavaliado nessa época.

Direção planejada:

```text
AI-1 — interpretação de linguagem
AI-2 — tarefas / timers / compromissos / lembretes
AI-3 — acadêmico
AI-4 — Modo Estudo
AI-5 — musculação
AI-6+ — demais domínios
```

Mesmo no futuro:

```text
LLM interpreta / escolhe ferramenta
↓
Butler valida regras
↓
ferramenta autoritativa executa
↓
D1
```

Nunca permitir LLM → SQL livre → D1. IA não deve mascarar bugs do roadmap determinístico.

---

## 20. Regra de retomada

Ao retomar:

1. ler `CONTINUIDADE.md`;
2. ler `docs/STATUS_ATUAL.md`;
3. ler `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`;
4. ler os documentos 4.1 e 4.2;
5. buscar `main` mais recente;
6. não redesenhar roadmap;
7. abrir branch própria;
8. implementar + testar;
9. PR;
10. merge apenas com regressão verde;
11. quando runtime mudar, confirmar Workers Builds da Cloudflare.

### Próximo ponto exato

```text
Etapa 4.3 — Progresso e Continuar curso
```

Base para reutilizar:

```text
cloudflare/src/course_domain.py
cloudflare/src/course_operational.py
cloudflare/migrations/0013_courses.sql
docs/ETAPA_4_1_MODELO_CURSOS.md
docs/ETAPA_4_2_CRUD_NAVEGACAO_CURSOS.md
```

Não antecipar Modo Estudo (4.4) nem importação (4.5).

---

## 21. Regra de atualização documental

Ao mudar:

- **status/subetapa/próximo passo:** atualizar `docs/STATUS_ATUAL.md`;
- **runtime/autoridade:** atualizar `docs/ARCHITECTURE.md` e Dossiê quando material;
- **roadmap/ordem futura:** atualizar a Trilha Definitiva;
- **decisão duradoura/handoff:** atualizar este arquivo;
- **capacidade pública/uso:** atualizar README quando necessário;
- **manual de uso:** atualizar `docs/MANUAL_USUARIO.md` quando função visível ao usuário mudar.

Não duplicar detalhes por conveniência. Cada documento tem uma função clara.
