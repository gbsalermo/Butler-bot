# Butler — Trilha Definitiva de Desenvolvimento

**Roadmap mestre de evolução do produto e da arquitetura**  
**Versão:** 1.7  
**Data-base:** 08/09/2026  
**Status:** oficial  
**Fase atual:** **Etapa 5.5 — Usabilidade Operacional**

> Este documento define **para onde o Butler evolui e em qual ordem**. Ele não substitui `docs/ARCHITECTURE.md` como fonte de verdade do runtime nem `docs/STATUS_ATUAL.md` como snapshot de andamento.
>
> Outra IA/agente deve continuar o ponto atual. **Não criar outro roadmap, não reorganizar etapas e não pular gates sem decisão explícita do proprietário.**

---

# 1. Visão do Butler

Butler deve ser um **assistente pessoal de verdade**, centrado em Telegram, capaz de organizar cotidiano, estudo, universidade, cursos, projetos, trabalho, hábitos e interesses sem virar apenas um menu de CRUDs nem uma IA imprevisível.

Experiência desejada:

```text
O que eu tenho hoje?
O que ficou de ontem?
Onde eu parei nesse projeto?
Essa matéria mudou de horário, ajusta aí.
Não vou conseguir treinar hoje porque vou viajar.
Anota isso para eu organizar depois.
Quero estudar Cálculo agora: limites, derivadas e integrais.
Qual é a próxima coisa realmente importante?
```

---

# 2. Princípios não negociáveis

1. **Core determinístico:** ações críticas não dependem de interpretação ampla ou imprevisível.
2. **Ação explícita vence contexto antigo.**
3. **Não inventar fatos:** presença, conclusão, gasto, treino, prioridade, compromisso ou progresso dependem de dado real/regra explícita.
4. **Multiusuário por padrão:** informação pessoal é isolada por usuário.
5. **Confirmação para escrita derivada/ambígua.**
6. **Texto natural e botões convivem.**
7. **Uma autoridade por domínio.**
8. **Migration é fonte formal do D1.**
9. **Toda expansão exige regressão.**
10. **Contexto auxilia, não governa.**
11. **Documentação acompanha comportamento.**
12. **CI verde não prova deploy Cloudflare.**
13. **Uma etapa só avança quando o gate estiver fechado.**
14. **Broad NLU/Library preservadas não voltam ao dispatcher central por conveniência.**
15. **Correção urgente de produção não muda automaticamente a etapa oficial.**
16. **Existência técnica não basta:** fluxo cotidiano também precisa ser confortável e proporcional à ação executada.

---

# 3. Runtime assumido pelo roadmap

```text
Telegram
→ webhook
→ Cloudflare Python Worker
→ cloudflare/src/worker.py
→ cloudflare/src/entry.py
→ handlers operacionais
→ D1 / Durable Objects / Telegram Bot API / Open-Meteo
```

A raiz `src/` usa polling/SQLite e é histórica/preservada.

---

# 4. Roadmap oficial

```text
ETAPA 0  🧹 Arrumar a casa                         ✅ concluída
             ↓
ETAPA 1  🗣️ Linguagem natural + conversa real     ✅ concluída
             ↓
ETAPA 2  🎓 Acadêmico completo + importação        ✅ concluída
             ↓
ETAPA 3  ⏱️ Auxiliares de Tempo / Modo Estudo     ✅ concluída
             ↓
ETAPA 4  📚 Cursos e trilhas de estudo             ✅ concluída
             ↓
FECHAMENTO 4  🧭 Reformulação do menu por áreas    ✅ concluída
             ↓
ETAPA 5  📥 Caixa de entrada                       ✅ concluída / mergeada
             ↓
ETAPA 5.5 ⚡ Usabilidade operacional                ▶️ atual / obrigatória
             ↓
ETAPA 6  🗂️ Projetos e trabalho                    ⏳ bloqueada pela 5.5
             ↓
ETAPA 7  🧭 Resumo/contexto/priorização             ⏳
             ↓
ETAPA 8  🧠 Memória + Library seletiva             ⏳
             ↓
ETAPA 9  🔒 Hardening                              ⏳
             ↓
ETAPA 10 🌐 Abertura pública + capacidade/escala   ⏳
             ↓
ETAPA 11 🌍 Idiomas e internacionalização          ⏳
```

Correções urgentes podem ocorrer a qualquer momento, mas devem ser testadas/documentadas e o desenvolvimento retorna ao ponto oficial depois delas.

---

# ETAPA 0 — 🧹 Arrumar a casa ✅

Concluída em 29/08/2026.

Entregas consolidadas:

- inventário estrutural;
- Dossiê Mestre e arquitetura documentada;
- dispatcher/callback/cron testáveis;
- menu principal com uma autoridade;
- lembretes de `daily_items` com uma autoridade;
- migrations formais;
- separação entre runtime Cloudflare ativo e raiz histórica;
- política contra patches paralelos sem justificativa.

---

# ETAPA 1 — 🗣️ Linguagem natural + conversa real ✅

Concluída em 31/08/2026. Gate: `docs/ETAPA_1_6_GATE_FINAL.md`.

Entregas duradouras:

- base linguística comum;
- contexto curto isolado por usuário;
- referências recentes/posicionais;
- correção/auto-reparo seguro;
- mensagens compostas/conjunções;
- confirmação de lotes;
- regressões de sequências, negação, mudança de assunto e múltiplos usuários.

Invariante:

```text
reconhecer linguagem ≠ autorizar escrita
```

---

# ETAPA 2 — 🎓 Acadêmico completo + importação confiável ✅

O domínio acadêmico atual foi considerado suficiente e preservado.

Modelo-base:

```text
subjects
subject_sessions
```

Importação acadêmica usa pipeline com validação, prévia e confirmação. Fonte recomendada: tabela do painel do SIGAA. Formatos oficiais: PDF textual pesquisável/selecionável e TXT. OCR não é dependência de produção.

Presença continua explícita; aula prevista não implica presença.

---

# ETAPA 3 — ⏱️ Auxiliares de Tempo / Modo Estudo ✅

Migrations:

```text
0010_quick_timers.sql
0011_study_mode.sql
```

Quick timers/alertas são persistentes e não poluem `daily_items`.

Modo Estudo mantém sessões/tópicos persistentes. Regra central:

> **fim de foco/timer nunca conclui tópico.**

Tópico só muda por conclusão/pulo explícito.

---

# ETAPA 4 — 📚 Cursos e trilhas de estudo ✅

## Objetivo

Representar aprendizado de longo prazo e integrar o próximo conteúdo ao cotidiano/Modo Estudo sem inventar progresso.

```text
Curso
→ módulos[]
   → conteúdos[]
      → materiais[]
      → atividades[]
      → progresso explícito
```

`🎓 Cursos` em Ler/Ver Depois continua sendo captura simples e **não** este domínio estruturado `📘 Cursos`.

## 4.1 — Modelo + autoridade ✅

```text
cloudflare/migrations/0013_courses.sql
cloudflare/src/course_domain.py
```

Tipos:

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

`skipped` conta como resolvido, não como concluído/aprendido.

## 4.2 — CRUD + navegação ✅

```text
cloudflare/src/course_operational.py
```

Entrega: criar/editar/arquivar/reativar curso; criar/renomear módulos; criar/editar conteúdos; calendário `scheduled_at` em curso ao vivo; navegação sem progresso implícito.

## 4.3 — Progresso + Continuar curso ✅

```text
cloudflare/src/course_stage4.py
```

Entrega:

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

- `Continuar curso` só consulta/abre `next_content()`;
- autogerido segue posições persistidas;
- ao vivo respeita calendário persistido;
- concluir último conteúdo não conclui curso;
- curso só conclui por confirmação explícita.

Documento: `docs/ETAPA_4_3_PROGRESSO_CURSOS.md`.

## 4.4 — Integração com Modo Estudo ✅

```text
cloudflare/migrations/0014_course_study_links.sql
cloudflare/src/course_study_bridge.py
```

Conteúdo pendente pode iniciar Modo Estudo, mas:

```text
tempo/foco/sessão ≠ conclusão do conteúdo
```

Sessão ativa/pausada não é substituída silenciosamente.

Documento: `docs/ETAPA_4_4_MODO_ESTUDO_CURSOS.md`.

## 4.5 — Importação de curso/material ✅

```text
cloudflare/src/course_importer.py
```

Aceita `.txt`, PDF textual ou texto colado em formato explícito. Linhas ambíguas são recusadas. Sempre existe prévia e confirmação antes de persistir. Persistência é orquestrada pelas funções da autoridade `course_domain.py`.

Documento: `docs/ETAPA_4_5_IMPORTACAO_CURSOS.md`.

## 4.6 — Gate final ✅

Regressões específicas:

```text
test_stage4_3_course_progress.py
test_stage4_4_course_study_bridge.py
test_stage4_5_course_import.py
test_stage4_6_course_gate.py
```

O gate cobre ordem autogerida, calendário ao vivo, explicitness, histórico, integração com Modo Estudo, importação com prévia e isolamento multiusuário.

Evidência de código: commit `7b41c42d4f151b126f405c7be9bceffcd452b9f9`, workflow `Butler regression` run #286 com `success`.

Documento: `docs/ETAPA_4_6_GATE_FINAL_CURSOS.md`.

## Gate funcional da Etapa 4

- [x] Curso → Módulo → Conteúdo;
- [x] progresso explícito;
- [x] modos autogerido/ao vivo distintos;
- [x] importação com prévia;
- [x] integração com Modo Estudo;
- [x] histórico preservado;
- [x] isolamento multiusuário;
- [x] regressão integrada verde.

---

# FECHAMENTO DA ETAPA 4 — 🧭 Menu por áreas da vida ✅

Concluído pela reorganização minimalista do menu, mergeada na `main` pela PR #54.

Direção consolidada:

- raiz minimalista;
- organização por áreas humanas da vida;
- atalhos frequentes preservados;
- linguagem natural independente do menu;
- ações exclusivas do proprietário escondidas para usuários comuns;
- Voltar/Cancelar consistentes;
- Day-off protegido;
- distinção `🎓 Cursos` backlog × `📘 Cursos` estruturados preservada;
- regressões de navegação/menu adicionadas.

Documento de referência: `ETAPA_4_FECHAMENTO_REFORMULACAO_MENU_AREAS_DA_VIDA.md`.

---

# ETAPA 5 — 📥 Caixa de entrada / captura rápida ✅

## Objetivo

Capturar algo sem exigir classificação imediata.

```text
anota isso pra eu organizar depois
joga na inbox: revisar autenticação do SGL
```

Entrega consolidada em `docs/ETAPA_5_CAIXA_DE_ENTRADA.md` e mergeada pela PR #57.

Gate:

- [x] captura por botão/texto;
- [x] listar/processar/arquivar;
- [x] conversão segura para domínios;
- [x] sem duplicação ao converter;
- [x] isolamento multiusuário.

---

# ETAPA 5.5 — ⚡ Usabilidade Operacional ▶️

## Objetivo

Antes de adicionar novos domínios, reduzir o atrito dos fluxos que já existem e tornar o Butler confortável para uso cotidiano.

Problemas que motivaram a subetapa:

- dificuldade percebida para criar várias rotinas em sequência;
- edição simples exigindo navegação/wizards desnecessários;
- ações como conclusão de tarefas limitadas a um alvo por operação;
- respostas com mais texto do que a ação exige;
- fluxos que encerram e obrigam o usuário a reentrar no domínio para continuar.

Ordem oficial:

```text
5.5.1 Rotinas múltiplas e criação contínua
→ 5.5.2 Edição direta
→ 5.5.3 Ações em lote
→ 5.5.4 Respostas curtas
→ 5.5.5 Fluxos contínuos
→ 5.5.6 Gate de UX real
```

Gate macro:

- [ ] várias rotinas podem ser criadas, listadas, editadas e concluídas independentemente;
- [ ] pedidos diretos evitam wizard quando alvo + alteração já são claros;
- [ ] ações em lote funcionam com segurança e confirmação quando necessário;
- [ ] confirmações simples são curtas e orientadas à ação;
- [ ] fluxos de domínio permitem continuar trabalhando sem reentrada desnecessária;
- [ ] bateria mínima de 20 cenários reais de UX passa;
- [ ] CI verde e deploy validados separadamente.

Documento: `docs/ETAPA_5_5_USABILIDADE_OPERACIONAL.md`.

**A Etapa 6 permanece bloqueada até o fechamento da 5.5.6.**

---

# ETAPA 6 — 🗂️ Projetos e trabalho ⏳

## Objetivo

Acompanhar projetos reais e responder “onde parei?”.

```text
Projeto
├─ estado
├─ objetivo
├─ próximos passos
├─ tarefas relacionadas
├─ bloqueios
├─ notas/sessões
└─ última atividade relevante
```

Gate:

- [ ] CRUD/estado confiável;
- [ ] próximo passo explícito;
- [ ] bloqueios;
- [ ] histórico/sessões;
- [ ] relação com tarefas/agenda;
- [ ] “onde parei?” baseado em dado real.

---

# ETAPA 7 — 🧭 Resumo, contexto operacional e priorização ⏳

Fontes: agenda, pendências, projetos, cursos, acadêmico, rotinas, clima, Day-off, prazos e bloqueios.

Priorização deve ser explicável e editável pelo usuário.

Gate:

- [ ] resumo usa dados reais;
- [ ] regras de prioridade visíveis/testáveis;
- [ ] usuário pode ignorar/reordenar;
- [ ] clima/Day-off influenciam só onde fizer sentido;
- [ ] recomendação não é apresentada como fato absoluto.

---

# ETAPA 8 — 🧠 Memória + Library seletiva ⏳

Reaproveitar seletivamente memória, sugestões e conhecimento preservados sem entregar o Core a uma arquitetura ampla.

Cada reativação precisa definir caso de uso, posição no dispatcher, leitura/escrita, expiração/invalidação, isolamento, precedência contra Core, confirmação antes de persistir e regressão.

Library pode responder/sugerir; persistência operacional continua no Core.

---

# ETAPA 9 — 🔒 Hardening ⏳

Escopo:

- backup/export/restore D1;
- retenção e migrations observáveis;
- secrets/webhook security/least privilege;
- redução de compatibilidades antigas;
- consolidação de patches no módulo dono;
- saúde de cron/DO/Telegram/migrations/latência;
- dívida técnica crítica.

Gate:

- [ ] backup/restore praticável;
- [ ] observabilidade mínima;
- [ ] secrets/configuração tratados;
- [ ] dívida crítica reduzida;
- [ ] documentação operacional/deploy completa.

Hardening não libera automaticamente o bot ao público.

---

# ETAPA 10 — 🌐 Abertura pública, capacidade e escala ⏳

Medir o caminho real:

```text
Telegram
→ Worker
→ handlers
→ D1
→ Durable Objects
→ scheduler
→ Telegram Bot API
```

Auditar limites/preços vigentes, requests/CPU, D1 reads/writes/storage, índices/scans, jobs, históricos, Durable Objects, Telegram 429/retry, rate limiting, privacidade e onboarding público.

Carga progressiva e banco sintético grande devem anteceder abertura irrestrita.

Abrir por ondas:

```text
uso interno
→ beta fechado
→ dezenas
→ centenas
→ aumento progressivo
→ público irrestrito
```

Documento: `ETAPA_10_ABERTURA_PUBLICA_ESCALA.md`.

---

# 5. Regras transversais de implementação

## Nova persistência

```text
migration
→ backfill se necessário
→ índice se justificado
→ teste
→ documentação
```

## Novo fluxo guiado

Precisa de cancelamento, voltar quando fizer sentido, limpeza de estado, troca segura de assunto e isolamento por usuário.

## Novo patch/ponte

Antes de criar:

```text
Por que não cabe no módulo dono?
É uma fronteira real entre domínios?
Quem chama?
Qual posição no dispatcher?
Qual símbolo substitui?
Como será removido?
Qual teste protege?
```

## Nova regra temporal

Definir fonte do dado, horário, tolerância, idempotência, Day-off, retry/falha e relação com Cron/Durable Objects.

---

# 6. Gate global de qualidade

Uma feature/subetapa só é concluída quando, conforme aplicável:

- módulo autoritativo definido;
- isolamento multiusuário preservado;
- persistência segura;
- migration criada se houver schema novo;
- callbacks/schedulers idempotentes;
- cancelamento/voltar disponíveis;
- caso feliz + falso positivo testados;
- sequências testadas quando há contexto;
- CI verde;
- documentação sincronizada;
- `/health` coerente quando a feature altera contrato de runtime;
- deploy validado separadamente quando necessário.

---

# 7. Como uma nova IA deve usar este roadmap

1. abrir `docs/STATUS_ATUAL.md`;
2. confirmar commits posteriores ao snapshot;
3. ler esta Trilha para entender a ordem;
4. abrir os documentos da etapa atual;
5. conferir `ARCHITECTURE.md` e `entry.py` antes de editar;
6. continuar o gate aberto;
7. não pular etapa;
8. correções de produção podem ocorrer fora da sequência, mas devem retornar ao gate oficial.

**Em 08/09/2026: Etapas 0–5 concluídas; Etapa 5.5 — Usabilidade Operacional é o ponto oficial atual; Etapa 6 permanece bloqueada até o fechamento do gate 5.5.6.**