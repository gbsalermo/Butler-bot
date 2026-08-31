# Butler — Status Atual e Handoff

**Data-base:** 31/08/2026  
**Branch de produção:** `main`  
**Snapshot revisado:** `8119b4b8e8bf17b0445a911283182acb1f658c1d`  
**Fase oficial:** **Etapa 1 — Linguagem natural + estabilidade de conversa real**  
**Subetapa em andamento:** **1.4 — Correção e auto-reparo conversacional**

> Este é o primeiro arquivo para uma nova IA/agente consultar ao assumir o Butler. Ele registra **onde o projeto está agora**, o que já foi concluído, o que está em andamento e quais decisões não devem ser reinterpretadas. Para detalhes completos do produto use `BUTLER_DOSSIE_MESTRE.md`; para o runtime exato use `ARCHITECTURE.md`; para a ordem futura use `TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`.

---

## 1. O projeto em uma frase

Butler é um assistente pessoal multiusuário via Telegram que combina organização cotidiana, universidade, tarefas, compromissos, rotinas, metas, musculação, mercado, clima e acompanhamento temporal confiável, mantendo operações críticas determinísticas e linguagem natural conservadora.

A produção **não** é o runtime antigo da raiz `src/`.

```text
Telegram
→ webhook
→ Cloudflare Python Worker
→ cloudflare/src/worker.py
→ cloudflare/src/entry.py
→ handlers operacionais
→ D1 / Durable Objects / Telegram Bot API / Open-Meteo
```

---

## 2. Estado do roadmap

Roadmap oficial:

```text
0. 🧹 Arrumar a casa                         ✅ concluída
1. 🗣️ Linguagem natural + conversa real     🚧 em andamento
2. 🎓 Acadêmico + importação robusta         ⏳ não iniciar ainda
3. ⏱️ Auxiliares de Tempo / Modo Estudo     ⏳ planejada
4. 📚 Cursos e trilhas de estudo             ⏳ planejada
5. 📥 Caixa de entrada                       ⏳ planejada
6. 🗂️ Projetos e trabalho                    ⏳ planejada
7. 🧭 Resumo/contexto/priorização             ⏳ planejada
8. 🧠 Memória + Library seletiva             ⏳ planejada
9. 🔒 Hardening                              ⏳ planejada
```

### Etapa 1 — situação real

| Subetapa | Status | Resultado principal |
|---|---|---|
| **1.1 — Auditoria da linguagem** | ✅ concluída | mapa da linguagem ativa, primitivas iniciais e corpus executável |
| **1.2 — Base Linguística Comum** | ✅ concluída | `language_primitives.py`, famílias comuns e polaridade sem NLU central de escrita |
| **1.3 — Referências + Contexto Curto** | ✅ concluída | `short_context.py`, expiração, isolamento por usuário, referências posicionais e histórico curto |
| **1.4 — Correção / Auto-reparo** | 🚧 em andamento | primeira fatia temporal já mesclada na `main` via PR #16 |

A primeira fatia da 1.4 já permite corrigir o item recém-criado sem duplicá-lo:

```text
marca dentista amanhã às 15h
→ não, 16h
```

O contexto só pode ser alterado silenciosamente quando está marcado como `source=created` ou `source=corrected`. Contexto vindo de lista não é elegível.

### O que ainda falta para fechar a 1.4

- rollback seguro de correção, como `deixa como tava`;
- correção explícita de título/alvo;
- correção em fluxos guiados antes da persistência, quando aplicável;
- sequências maiores de 3–8 turnos;
- manter falsos positivos baixos em negações/referências.

### O que ainda falta para fechar a Etapa 1

Depois da 1.4, ainda precisam ser atendidos os gates globais da Etapa 1, principalmente:

- conjunções estruturais;
- mensagens compostas/múltiplas intenções com segurança;
- corpus de regressão maior;
- sequências reais mais longas;
- falsos positivos deliberados;
- isolamento de contexto com dois usuários;
- Core permanecendo como autoridade de escrita.

**Não avançar para a Etapa 2 enquanto o gate da Etapa 1 estiver aberto.**

---

## 3. Decisões arquiteturais que já estão fechadas

1. **`cloudflare/` é produção.** A raiz `src/` é histórica/preservada.
2. **`entry.py` governa a precedência.** Um módulo existir no repositório não significa que governa o webhook.
3. **Uma autoridade por domínio.** Novo `*_patch.py` só entra quando não houver caminho razoável no módulo dono.
4. **Core determinístico governa escrita crítica.** Linguagem/contexto resolvem intenção/alvo; persistência continua no domínio.
5. **Ação explícita vence contexto antigo.** Mudança de assunto cria barreira.
6. **Contexto curto tem autoridade em `short_context.py`.** Não criar outra memória curta paralela.
7. **`reliable_reminders.py` é a autoridade temporal de `daily_items`.** Não criar outro scheduler concorrente.
8. **Migrations são a fonte formal do D1.** `ensure_schema()` é apenas defesa operacional.
9. **Multiusuário é invariante.** Resolver `telegram_chat_id → user_id` e filtrar dados pessoais pelo usuário.
10. **Broad NLU, Library genérica, sugestões transversais e memória pessoal genérica continuam desativadas.** O código preservado não deve ser religado por conveniência.
11. **CI verde não prova deploy Cloudflare.** Deploy e funcionamento real precisam de validação própria.

---

## 4. Dispatcher de mensagens — estado atual

Ordem simplificada de `cloudflare/src/entry.py`:

```text
/start/reset
→ aviso administrativo / diagnósticos
→ despedida prioritária
→ usabilidade / Ler-Ver Depois
→ menu / rotinas / presença UI / navegação
→ core_fast_path
→ presença / provas / acadêmico
→ correction_patch
→ lembrete explícito
→ referência curta
→ contexto de tarefa
→ runtime_guard
→ mercado
→ quality
→ musculação
→ conversation_layer
→ app.py somente quando botão/estado guiado exigir
→ fallback
```

A posição de `correction_patch` é deliberada: auto-reparo deve acontecer antes de parsers que poderiam criar outro item.

Callbacks:

```text
admin_announcement_flow
→ attendance
→ conversation/context item callbacks
```

Cron autoritativo:

```text
day_off
→ attendance
→ daily_items
→ routines
→ summaries
→ app.scheduled_tick (compatibilidade)
```

---

## 5. Linguagem e contexto ativos

### Autoridades novas da Etapa 1

```text
language_primitives.py
→ famílias linguísticas, sinais e polaridade
→ sem D1, Telegram ou CRUD

short_context.py
→ contexto curto expirável, isolado por usuário
→ referências recentes/posicionais

correction_patch.py
→ auto-reparo conversacional seguro do item recém-criado

temporal_language.py
→ primitivas de tempo relativo usadas pelo trabalho da Etapa 1
```

`conversation_layer._remember/_context` foi redirecionado para a autoridade de `short_context`, evitando dois contratos de memória curta.

A janela inicial do contexto curto é de **30 minutos**.

---

## 6. Correções operacionais recentes que precisam permanecer documentadas

### 6.1 Redundância do scheduler

Em 30/08/2026 houve um incidente em que o heartbeat do Cron Trigger ficou congelado e notificações não foram processadas. A correção está documentada em `SCHEDULER_REDUNDANCY.md`.

Hoje há duas linhas:

```text
Cron Trigger a cada minuto
→ dispatch_scheduled()

Durable Object persistente por usuário
→ PersonalAlarm
→ próximo evento relevante
→ dispatchers autoritativos
```

`PersonalAlarm` cobre tarefas com horário, compromissos, lembretes simples, checkpoints de rotina, resumo matinal e fechamento semanal. `AttendanceAlarm` permanece separado para aula/presença.

Após um webhook, a reconciliação dos alarms é disparada com `ctx.waitUntil(...)`, fora do caminho crítico da resposta HTTP. No cron, ela continua síncrona.

A redundância depende da mesma idempotência de `notification_log`; não é autorização para enviar mensagens duplicadas.

### 6.2 Desempenho do caminho quente

Foram reduzidos round-trips D1 por update:

- cache local ao request para `telegram_chat_id → user_id`;
- cache local ao request para `user_sessions`;
- gates lexicais antes de consultas de contexto;
- DDL defensivo de presença removido do dispatcher geral;
- reconciliação de Durable Objects retirada do tempo de resposta do webhook.

O cache **não é persistente entre updates**.

### 6.3 Clima mais humano

A previsão continua baseada em Open-Meteo e dados determinísticos, mas ganhou uma camada de comentário mais natural em `weather_personality.py`.

Essa camada não deve inventar valores meteorológicos nem substituir a fonte objetiva; ela só melhora a apresentação.

### 6.4 Ler/Ver Depois

As categorias operacionais atuais incluem:

```text
📚 Livros
🎬 Filmes
🎓 Cursos
🗂️ Outras
```

A categoria `Cursos` na lista de “ver depois” **não significa** que o módulo completo de Cursos/Trilhas da Etapa 4 esteja implementado.

---

## 7. Banco de dados

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
```

Até este snapshot, as mudanças da Etapa 1.1–1.4 usam estruturas já existentes (`natural_events`, `user_sessions`, `daily_items`) e **não adicionaram migration nova**.

---

## 8. Funcionalidades ativas hoje

- tarefas, pendências e agenda;
- compromissos;
- lembretes pessoais;
- matérias, provas, presença e faltas;
- importação SIGAA por PDF textual/TXT;
- mercado/itens faltando;
- rotinas e metas;
- musculação, exercícios, séries, carga e progresso;
- Ler/Ver Depois, incluindo Cursos como categoria de captura;
- clima;
- Day-off;
- resumos matinal e semanal;
- alarmes persistentes e redundância do scheduler;
- administração do proprietário;
- linguagem natural operacional conservadora;
- contexto curto e referências;
- primeira fatia de auto-reparo temporal.

Finanças continuam preservadas no Core, mas não são destaque do menu principal.

---

## 9. O que NÃO está ativo ainda

Não anunciar como funcionalidade pronta:

- NLU ampla/global;
- memória pessoal genérica;
- Butler Library genérica no dispatcher;
- sugestões transversais automáticas;
- modo completo de Cursos/Trilhas;
- Auxiliar de Estudos/Modo Estudo;
- Assistente Geral de Tempo persistente;
- Inbox/Caixa de entrada;
- gestão completa de Projetos/Trabalho;
- motor global de priorização;
- voz/web/app.

Há código/documentos preservados para algumas dessas ideias, mas isso não equivale a runtime ativo.

---

## 10. Próximo trabalho recomendado

Ao assumir o projeto, continuar **a partir da Etapa 1.4**, sem criar novo roadmap.

Ordem prática:

1. ler `ETAPA_1_4_CORRECOES.md`;
2. conferir `entry.py`, `short_context.py`, `correction_patch.py` e testes da 1.4;
3. concluir rollback/correção adicional de forma conservadora;
4. ampliar sequências e falsos positivos;
5. rodar a regressão completa;
6. atualizar este arquivo e o documento da subetapa;
7. somente depois atacar os gates restantes da Etapa 1;
8. Etapa 2 só começa quando o gate global da Etapa 1 estiver marcado como concluído.

---

## 11. Ordem de leitura para outra IA

1. **`docs/STATUS_ATUAL.md`** — onde estamos agora;
2. **`docs/BUTLER_DOSSIE_MESTRE.md`** — visão completa e decisões estruturais;
3. **`docs/ARCHITECTURE.md`** — runtime técnico atual;
4. **`docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`** — ordem oficial futura;
5. **`docs/ETAPA_1_AUDITORIA_LINGUAGEM.md`** — início da Etapa 1;
6. **`docs/ETAPA_1_2_BASE_LINGUISTICA.md`**;
7. **`docs/ETAPA_1_3_CONTEXTO_REFERENCIAS.md`**;
8. **`docs/ETAPA_1_4_CORRECOES.md`** — trabalho atual;
9. **`docs/SCHEDULER_REDUNDANCY.md`** — incidente e arquitetura temporal de contingência;
10. **`docs/MAINTAINER_GUIDE.md`** — regras práticas;
11. **`cloudflare/src/README.md`** — mapa de módulos;
12. **`CONTINUIDADE.md`** — decisões duradouras.

`AUDIT_MAIN_2026-08.md` e `INVENTARIO_ETAPA_0.md` são importantes como histórico da Etapa 0, mas não devem substituir `STATUS_ATUAL.md`/`ARCHITECTURE.md` para inferir o runtime de hoje.

---

## 12. Checklist de handoff

Antes de fazer qualquer alteração:

- [ ] confirmar que a branch é `main` ou criar branch deliberadamente;
- [ ] verificar se o SHA atual avançou além do snapshot deste arquivo;
- [ ] ler os commits posteriores se houver diferença;
- [ ] localizar o handler real no `entry.py`;
- [ ] identificar o módulo autoritativo;
- [ ] verificar regressão existente;
- [ ] não reativar arquitetura preservada sem decisão explícita;
- [ ] não criar outro scheduler concorrente;
- [ ] manter isolamento multiusuário;
- [ ] criar migration se houver schema novo;
- [ ] atualizar documentação junto com comportamento;
- [ ] separar “CI passou” de “deploy Cloudflare foi validado”.

---

## 13. Regra para atualizar este snapshot

Atualize `STATUS_ATUAL.md` quando houver qualquer um destes eventos:

- conclusão/início de subetapa;
- mudança de módulo autoritativo;
- alteração da ordem do dispatcher;
- nova migration;
- incidente operacional relevante;
- mudança de arquitetura de scheduler/alarm;
- feature planejada passar a ativa;
- feature ativa ser desativada;
- alteração relevante no próximo passo oficial.

Este arquivo deve permanecer curto o suficiente para handoff e preciso o suficiente para impedir que uma nova IA recomece o planejamento do zero.
