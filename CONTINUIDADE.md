# Continuidade do desenvolvimento — Butler

**Data-base:** 31/08/2026

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

`notification_log` é a autoridade central de idempotência para entregas agendadas.

Após webhook, reconciliações persistentes devem usar `ctx.waitUntil(...)` para não atrasar a resposta interativa. No cron, a reconciliação permanece síncrona.

Falha de um subsistema não deve derrubar os demais.

---

## 3. Arquitetura de linguagem e contexto

Uma geração anterior tentou centralizar linguagem/contexto em módulos globais como `context_router.py`, `intent_parser.py`, `action_policy.py`, `context_memory.py` e `suggestion_engine.py`.

Eles podem permanecer preservados, mas **não são o roteador central do webhook atual**.

A produção privilegia:

- handlers explícitos e ordenados;
- fast paths conservadores;
- `language_primitives.py` como base linguística compartilhada sem efeitos colaterais;
- `short_context.py` como autoridade do contexto operacional curto;
- estados guiados;
- módulos autoritativos por domínio;
- fallback estreito.

Regra permanente:

```text
reconhecer linguagem
≠
autorizar escrita
```

### Contexto curto

`short_context.py` mantém contexto por usuário, com TTL curto e barreira contra mudança explícita de assunto.

Suporta referências como:

```text
essa / esse / isso
ela / ele
anterior / última
primeira / segunda / terceira
a outra / o outro
```

Referências posicionais usam a ordem realmente mostrada ao usuário.

### Correção recente

`correction_patch.py` pode corrigir um alvo recente seguro sem duplicar o item.

Exemplos:

```text
não, 16h
quinta não, sexta
não é dentista, é oftalmo
deixa como tava
```

Contexto de lista não deve ser alterado silenciosamente.

### Frases compostas

`compound_router.py` segmenta lotes determinísticos, sem transformar qualquer conjunção em segunda ação.

Lotes suportados devem ser totalmente válidos antes de persistir; lote incompleto não grava metade.

---

## 4. Etapa 0 — Arrumar a casa ✅

Concluída.

Decisões que permanecem:

- `entry.py` governa precedência do dispatcher;
- `operational_menu.py` governa o menu principal;
- `reliable_reminders.py` governa lembretes baseados em `daily_items`;
- schema formal vem de migrations;
- não excluir código apenas por idade/nome sem demonstrar que runtime não depende dele;
- evitar criar cadeias de `*_fix2.py`, `*_final.py` ou módulos paralelos sem necessidade real.

---

## 5. Etapa 1 — Linguagem natural + conversa real ✅

Concluída.

Principais invariantes:

### Negação

```text
não me lembra de estudar hoje
→ não cria lembrete

me lembra de não estudar hoje
→ lembrete positivo; a negação pertence ao conteúdo

não deixa eu esquecer...
→ pedido positivo de lembrete
```

### Tarefas

```text
preciso pagar a conta
→ pode ser tarefa

preciso de ajuda com cálculo
→ não deve virar tarefa
```

### Contexto e referências

Referências curtas funcionam apenas quando existe alvo recente seguro.

### Lotes

Lotes determinísticos de 2–5 tarefas/compromissos/lembretes podem ser mostrados em prévia e confirmados de uma vez.

Documento final: `docs/ETAPA_1_6_GATE_FINAL.md`.

---

## 6. Etapa 2 — Importação acadêmica confiável ✅

Concluída.

**Decisão de produto importante:** a Etapa 2 não redesenhou o domínio acadêmico.

O modelo atual foi considerado suficiente e deve ser preservado:

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

Não adicionar professor, carga horária, semestre ou novas entidades acadêmicas apenas por conveniência.

Objetivo da Etapa 2 foi tornar o primeiro cadastro/importação mais confiável:

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

Fonte recomendada no SIGAA:

```text
Componente Curricular | Local | Horário
```

Aceitos em produção:

- PDF com texto pesquisável/selecionável;
- TXT.

Não tratar screenshot, foto, scan ou OCR como formato oficial.

### Presença/faltas

Aulas são previstas; presença nunca é presumida.

**“vou” não persiste presença.**

Somente ausência/resposta explícita gera registro conforme as regras existentes.

---

## 7. Etapa 3 — Auxiliares de Tempo / Modo Estudo ✅

Concluída.

### 3A — Alertas rápidos e cronômetros

Migration formal:

```text
0010_quick_timers.sql
```

Tabela `quick_timers` é separada de `daily_items`, para não poluir tarefas.

Tipos persistidos:

```text
timer
quick_alert
```

Exemplos:

```text
me lembra de desligar o ovo daqui a 5 minutos
me avisa em 20 minutos de olhar o forno
cronometra 30 minutos
inicia um timer de 45 segundos
```

Horizonte rápido atual: 1 segundo até 24 horas. Acima disso deve usar lembrete normal.

`relative_alert` é apenas intenção linguística; ao persistir deve ser convertido para `quick_alert`.

Day-off não bloqueia timer/alerta rápido explicitamente iniciado.

### Resposta social opcional após alertas

Após alerta rápido/timer/lembrete simples recém-enviado, o Butler pode reconhecer respostas curtas como:

```text
valeu
fechado
já foi
desliguei
feito
terminei
resolvido
```

Isso é **opcional** e não cria obrigação de resposta.

A associação é curta e best-effort; falha dessa camada jamais pode impedir o disparo do aviso.

Tarefas e Modo Estudo mantêm semântica própria: `feito`/`terminei` não devem ser sequestrados por resposta social quando existe fluxo mais específico ativo.

### 3B — Modo Estudo

Migration formal:

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

Logo:

```text
fim do foco
≠ conclusão do tópico

fim da pausa
≠ conclusão do tópico

restart
≠ conclusão do tópico

Day-off
≠ conclusão do tópico
```

Tempos padrão:

```text
25 min foco
5 min pausa
15 min pausa longa
a cada 4 blocos
```

Exemplo:

```text
modo estudo Cálculo I: limites, derivadas, integrais
modo estudo 50/10/20 Física I: cinemática, dinâmica
```

Ações:

```text
status estudo
concluí o tópico
pular tópico
não terminei
pausar estudo
retomar estudo
cancelar estudo
histórico de estudo
```

Modo Estudo pode reutilizar nome canônico de matéria existente, mas não depende de FK acadêmica.

---

## 8. Diagnóstico de runtime e manual

Após incidentes de webhook silencioso, foi criada a camada de diagnóstico persistente.

Migration:

```text
0012_runtime_errors.sql
```

Comando proprietário:

```text
/status runtime
```

Ele verifica D1, tabelas importantes, heartbeat e últimos erros capturados.

Erros técnicos podem ser persistidos em `runtime_errors`, sem salvar o texto da conversa do usuário.

### Manual

Manual completo:

```text
docs/MANUAL_USUARIO.md
```

Ajuda rápida no Telegram:

```text
/manual
/ajuda
manual
📖 Manual
```

Categorias do manual **só** podem ser abertas com pedido explícito de ajuda (`Ajuda: ...` / `ajuda ...`).

Essa regra existe porque aliases soltos como `Cotidiano`, `Matérias` e `Musculação` chegaram a sequestrar botões operacionais. Essa regressão foi corrigida e deve permanecer coberta por testes.

`🌙 Day-off` deve continuar sozinho na última linha do menu principal para reduzir clique acidental.

---

## 9. Musculação

O perfil proprietário preserva o Protocol Mass de 12 semanas; usuários genéricos podem possuir ficha própria.

Regras permanentes:

- não aplicar protocolo pessoal a outro usuário;
- registrar carga/repetição somente quando informadas;
- substituição não apaga histórico;
- evolução usa dados realmente registrados;
- “não consegui treinar hoje” não deve inventar séries;
- exercício substituído deve manter rastreabilidade do original.

---

## 10. Cotidiano, RU e Ler/Ver Depois

### Lista de itens faltando

É uma lista persistente do que está faltando em casa, não uma compra descartável.

Exemplos naturais como `acabou café` podem atualizar a lista quando o pedido estiver claro.

### RU

Cardápio semanal é compartilhado para usuários; atualização/importação fica restrita ao proprietário.

Consultas típicas:

```text
qual o almoço hoje?
qual o café amanhã?
cardápio da semana
```

### Ler/Ver Depois

Categorias atuais:

```text
Livros
Filmes
Cursos
Outras
```

**A categoria `Cursos` aqui é somente backlog simples.**

Ela não deve ser confundida, migrada silenciosamente ou reinterpretada como o módulo estruturado da Etapa 4.

---

## 11. Etapa 4 — Cursos e trilhas de estudo ▶️ EM ANDAMENTO

### 4.1 — Modelo + autoridade ✅ concluída

Implementação criada:

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

Tipos de curso:

```text
self_paced
live
```

Regras permanentes já definidas:

- módulos e conteúdos têm ordenação explícita;
- curso autogerido mantém o próximo conteúdo pendente até ação explícita;
- curso ao vivo segue calendário fixo e não desloca aulas automaticamente;
- progresso de conteúdo é `pending`, `completed` ou `skipped`;
- `skipped` não conta como conteúdo aprendido/concluído;
- `next_content()` é consulta e não produz efeito colateral;
- material e atividade têm progresso próprio e não concluem o conteúdo automaticamente;
- tempo gasto no Modo Estudo não conclui curso/conteúdo;
- mesmo com todos os conteúdos resolvidos, conclusão final do curso permanece explícita;
- todo acesso é isolado por usuário.

### Próxima subetapa oficial: 4.2 — CRUD + navegação no Telegram

Próximo trabalho:

- menu operacional de Cursos;
- adicionar curso;
- listar cursos;
- abrir detalhes;
- editar informações básicas;
- arquivar/remover conforme contrato definido;
- navegar por módulos e conteúdos;
- usar exclusivamente `course_domain.py` como autoridade de persistência.

**Ainda não fazer nesta subetapa:**

- integração completa com Modo Estudo;
- importador de cursos;
- reorganização final do menu por áreas da vida;
- IA.

Sequência prevista da Etapa 4:

```text
✅ 4.1 Modelo + autoridade
▶️ 4.2 CRUD + navegação
⏳ 4.3 Progresso + “continuar curso”
⏳ 4.4 Integração com Modo Estudo
⏳ 4.5 Importação de cursos/material
⏳ 4.6 Gate final
⏳ Fechamento: menu por áreas da vida
```

A reformulação do menu por áreas da vida é **obrigatória ao final da Etapa 4 e antes da Etapa 5**.

---

## 12. Projetos, Inbox e priorização

Compromissos futuros do roadmap:

- Caixa de entrada para captura rápida sem classificação imediata;
- Projetos/Trabalho com estado, próximos passos, bloqueios e “onde parei?”;
- priorização do dia/semana baseada em regras explicáveis e dados reais;
- integração posterior com cursos, agenda, clima, rotinas e pendências.

Não implementar essas frentes antes dos gates oficiais.

---

## 13. Library e conhecimento

Os acervos de culinária, jogos, cultura pop, livros e filosofia continuam preservados para etapa própria.

Direção permanente:

- preferir dados, aliases, tags e índice, não um `if` por exemplo;
- Library pode sugerir, mas ação persistente pertence ao Core;
- preferir dados abertos, domínio público, documentos próprios e resumos/metadados;
- Library genérica continua fora do dispatcher principal até reativação seletiva planejada.

---

## 14. Clima

Open-Meteo continua sendo a fonte objetiva de previsão.

Camadas de personalidade podem acrescentar comentário humano, mas nunca inventar temperatura, precipitação, vento ou probabilidade.

Falha de clima não derruba agenda/resumo.

---

## 15. Multiusuário e proprietário

Toda persistência pessoal é isolada por usuário.

A barreira `is_owner(chat_id)` não deve ser removida sem mecanismo equivalente.

Recursos administrativos permanecem exclusivos do proprietário.

Antes de abertura pública, seeds/configurações pessoais devem ser separados de defaults genéricos.

---

## 16. Banco e migrations

Disciplina obrigatória:

1. migration versionada;
2. backfill explícito quando necessário;
3. índice quando a consulta justificar;
4. `ensure_schema()` apenas como tolerância operacional;
5. testes;
6. documentação.

Migrations formais conhecidas atualmente:

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

Migration destrutiva exige snapshot/export do D1 e plano de rollback.

---

## 17. Testes e deploy

A suíte em `cloudflare/tests/` deve cobrir o caminho realmente alcançado pelo dispatcher.

Prioridades:

- sequências completas de conversa;
- falsos positivos;
- isolamento entre dois usuários;
- callbacks repetidos;
- scheduler/idempotência;
- cancelamento/voltar;
- precedência de handlers;
- ausência de round-trips D1 desnecessários no caminho quente.

Último gate técnico da Etapa 4.1:

```text
356 testes passando
```

A Etapa 4.1 foi implantada com sucesso pela Cloudflare Workers Builds.

Sempre preservar a distinção:

```text
GitHub Actions verde
≠ automaticamente produção validada
```

---

## 18. Ordem oficial de evolução

```text
0. 🧹 Arrumar a casa                         ✅
1. 🗣️ Linguagem natural + conversa real     ✅
2. 🎓 Importação acadêmica confiável         ✅
3. ⏱️ Auxiliares de Tempo / Modo Estudo     ✅
4. 📚 Cursos e trilhas de estudo             ▶️ em andamento
   4.1 Modelo + autoridade                   ✅
   4.2 CRUD + navegação                      ▶️ próxima
   4.3 Progresso / continuar curso           ⏳
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

Fluxo obrigatório:

```text
concluir roadmap 0–10
↓
estabilizar produção
↓
passar gate de estabilidade
↓
iniciar trilha de IA
```

Provedor inicial pretendido: **Groq**, por API em nuvem, inicialmente dentro do free tier se ainda estiver disponível.

O modelo específico **não está congelado**; deverá ser reavaliado quando a trilha começar.

Direção futura:

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

Nunca permitir LLM → SQL livre → D1.

A IA também não deve ser usada para mascarar bugs ou instabilidade que pertencem ao roadmap determinístico atual.

---

## 20. Regra de retomada

Ao retomar o projeto em uma nova conversa/IA:

1. ler `CONTINUIDADE.md`;
2. ler `docs/STATUS_ATUAL.md`;
3. ler `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`;
4. ler o documento da etapa/subetapa atual;
5. buscar `main` mais recente antes de alterar código;
6. não redesenhar roadmap por conta própria;
7. abrir branch própria;
8. implementar + testar;
9. PR;
10. merge apenas com regressão verde;
11. verificar pós-merge e, quando runtime mudar, confirmar Workers Builds da Cloudflare.

### Próximo ponto exato

```text
Etapa 4.2 — CRUD + navegação de Cursos no Telegram
```

Base já pronta para reutilizar:

```text
cloudflare/src/course_domain.py
cloudflare/migrations/0013_courses.sql
docs/ETAPA_4_1_MODELO_CURSOS.md
```

Não voltar para 4.1 salvo para corrigir bug/regressão comprovada.

---

## 21. Regra de atualização documental

Ao mudar:

- **status/subetapa/próximo passo:** atualizar `docs/STATUS_ATUAL.md`;
- **runtime/autoridade:** atualizar `docs/ARCHITECTURE.md` e o Dossiê quando material;
- **roadmap/ordem futura:** atualizar a Trilha Definitiva;
- **decisão duradoura/handoff:** atualizar este arquivo;
- **capacidade pública/uso:** atualizar README quando necessário;
- **incidente temporal/scheduler:** atualizar `docs/SCHEDULER_REDUNDANCY.md` quando aplicável;
- **manual de uso:** atualizar `docs/MANUAL_USUARIO.md` quando função visível ao usuário mudar.

Não duplicar detalhes por conveniência. Cada documento tem uma função clara.
