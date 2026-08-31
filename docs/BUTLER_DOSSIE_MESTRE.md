# Butler — Dossiê Mestre

**Versão:** 1.1  
**Data-base:** 31/08/2026  
**Status:** referência mestre do produto e das decisões estruturais

> Este arquivo explica **o que é o Butler, como a produção está montada, quais módulos são autoridades, quais decisões já estão fechadas e como o projeto deve evoluir sem voltar a acumular camadas paralelas**.
>
> Para andamento exato e próximo passo: `docs/STATUS_ATUAL.md`.  
> Para o runtime técnico exato: `docs/ARCHITECTURE.md`.  
> Para a ordem futura: `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`.

---

# 1. O que é o Butler

Butler é um assistente pessoal multiusuário via Telegram projetado para acompanhar o estado real do cotidiano do usuário e ajudá-lo a agir sobre ele.

O produto não deve ser reduzido a:

- um CRUD com botões;
- um chatbot genérico;
- uma coleção de regex independentes;
- uma IA que toma decisões sem confirmação;
- um catálogo de funcionalidades sem integração.

A proposta combina:

- operações determinísticas;
- linguagem natural conservadora;
- contexto curto;
- agenda e histórico reais;
- automação temporal confiável;
- isolamento multiusuário;
- memória/Library seletivas apenas em etapa futura.

O Butler deve trabalhar com informações como:

```text
tarefas
compromissos
matérias e aulas
provas e faltas
rotinas e metas
treinos
itens faltando em casa
coisas para ler/ver depois
clima
cursos estruturados (roadmap)
projetos e sessões de trabalho (roadmap)
```

O objetivo de longo prazo é responder com confiança perguntas como:

```text
O que eu tenho hoje?
O que ficou de ontem?
Onde eu parei nesse projeto?
O que eu estudo hoje no curso?
Qual é a próxima coisa realmente importante?
```

---

# 2. Princípios não negociáveis

1. **Core governa ações críticas.** Linguagem, memória e Library nunca escrevem silenciosamente onde uma operação determinística deve validar.
2. **Ação explícita vence contexto antigo.** Mudar de assunto não pode deixar o último tópico sequestrar a mensagem.
3. **Nada é inventado.** Não presumir presença, conclusão, treino, gasto, compromisso, prioridade, clima ou progresso.
4. **Isolamento por usuário é obrigatório.** Toda operação pessoal resolve `telegram_chat_id → user_id` e filtra SQL corretamente.
5. **Ambiguidade de escrita pede confirmação.** Especialmente remoção, alteração ou alvo não identificado.
6. **Botões e texto natural coexistem.** Botão é UX, não a única interface.
7. **Scheduler precisa ser idempotente.** Reprocessar um minuto/evento não pode duplicar notificação crítica.
8. **Falha de um subsistema não derruba os demais.** O cron é isolado por domínio.
9. **Migration é a fonte formal do banco.** `ensure_schema()` é apenas tolerância operacional.
10. **Código novo entra no módulo dono.** Novo patch é exceção, não padrão.
11. **Produção e código preservado são coisas diferentes.** Existir no repositório não significa estar ligado ao webhook.
12. **Uma etapa só termina com regressão e gate.** Funcionar manualmente uma vez não é conclusão.
13. **CI verde não prova deploy Cloudflare.** Código validado e produção publicada são estados diferentes.
14. **Não recriar planejamento já decidido.** Outra IA deve continuar a etapa atual documentada em `STATUS_ATUAL.md`.

---

# 3. Estado atual do desenvolvimento

Roadmap oficial:

```text
0. 🧹 Arrumar a casa                         ✅ concluída
1. 🗣️ Linguagem natural + conversa real     🚧 em andamento
2. 🎓 Acadêmico + importação robusta         ⏳
3. ⏱️ Auxiliares de Tempo / Modo Estudo     ⏳
4. 📚 Cursos e trilhas de estudo             ⏳
5. 📥 Caixa de entrada                       ⏳
6. 🗂️ Projetos e trabalho                    ⏳
7. 🧭 Resumo/contexto/priorização             ⏳
8. 🧠 Memória + Library seletiva             ⏳
9. 🔒 Hardening                              ⏳
```

## Etapa 1

```text
1.1 auditoria da linguagem           ✅ concluída
1.2 base linguística comum           ✅ concluída
1.3 contexto curto/referências       ✅ concluída
1.4 correção/auto-reparo             🚧 em andamento
```

A primeira fatia da 1.4 já está na `main`: correção temporal do item recém-criado, por exemplo `não, 16h`, sem duplicar o registro.

Ainda faltam na 1.4, entre outros pontos:

- rollback seguro (`deixa como tava`);
- correção explícita de título/alvo;
- sequências maiores;
- correções em fluxos guiados quando aplicável.

Fechar a 1.4 **não fecha automaticamente a Etapa 1**. O gate global ainda inclui conjunções, mensagens compostas/múltiplas intenções, corpus ampliado, sequências reais, falsos positivos e isolamento entre dois usuários.

Fonte atualizada: `docs/STATUS_ATUAL.md`.

---

# 4. Arquitetura de produção

```text
Telegram
   ↓ webhook
Cloudflare Python Worker
   ↓
cloudflare/src/worker.py
   ↓
cloudflare/src/entry.py
   ↓
handlers operacionais ordenados
   ↓
Cloudflare D1 / Durable Objects / APIs externas
   ↓
Telegram Bot API
```

A raiz `src/` contém runtime histórico em polling/SQLite e não governa produção.

## `worker.py`

Responsabilidades atuais:

- ser o entrypoint do Worker;
- manter `AttendanceAlarm` e `PersonalAlarm`;
- sincronizar alarms no cron;
- após webhook, solicitar reconciliação persistente com `ctx.waitUntil(...)`, sem fazer o Telegram esperar essa varredura;
- delegar HTTP/cron ao `entry.Default`.

## `entry.py`

É o orquestrador autoritativo e expõe:

```text
dispatch_callback()
dispatch_message()
dispatch_scheduled()
```

A ordem é parte do contrato do produto.

## `app.py`

Núcleo-base herdado ainda necessário. Mantém bootstrap, estados guiados, operações-base e scheduler de compatibilidade. Não é, sozinho, a fonte final do comportamento visível.

---

# 5. Dispatcher de mensagens

Ordem simplificada atual:

```text
1.  start/reset
2.  aviso administrativo
3.  diagnósticos
4.  despedida prioritária
5.  usabilidade / Ler-Ver Depois
6.  menu / rotinas / presença UI / navegação
7.  core_fast_path
8.  presença / provas / acadêmico
9.  correction_patch
10. lembrete explícito
11. referência curta
12. contexto de tarefa
13. runtime_guard
14. mercado
15. quality
16. musculação
17. conversation_layer
18. app.py somente para botão/estado guiado necessário
19. fallback
```

Um handler que retorna `True` consome a mensagem.

A posição de `correction_patch` é deliberada: uma correção do turno anterior deve ser tratada antes de parsers que poderiam criar um novo item.

A migration 0003 é a fonte formal do schema de presença; DDL defensivo não roda mais em toda mensagem do dispatcher geral.

---

# 6. Callbacks

Ordem autoritativa:

```text
admin_announcement_flow
→ attendance
→ conversation/context item callbacks
```

A precedência administrativa é protegida por regressão porque envolve broadcast/efeitos sensíveis.

---

# 7. Linguagem natural e contexto — arquitetura ativa

A produção **não usa NLU ampla como roteador central**.

## `language_primitives.py`

Autoridade para famílias linguísticas e polaridade compartilháveis.

Contrato:

```text
reconhece linguagem
→ não consulta D1
→ não envia Telegram
→ não executa CRUD
```

## `short_context.py`

Autoridade de contexto curto:

- janela inicial de 30 minutos;
- isolamento por `user_id`;
- histórico de alvos;
- referências posicionais pela ordem realmente vista;
- barreira de mudança de assunto;
- contrato reaproveitado pelos helpers antigos de `conversation_layer`.

## `reference_patch.py`

Resolve referências como:

```text
essa / ela / ele
a primeira / segunda / terceira
a outra
a anterior
a última
```

Resolver alvo não equivale a autorizar escrita.

## `correction_patch.py`

Primeira fatia da Etapa 1.4.

Somente contextos `source=created` ou `source=corrected` podem sofrer correção silenciosa. Lista exibida não é alvo automático de reparo.

## `temporal_language.py`

Primitivas de tempo relativo já utilizadas pelo trabalho linguístico. O Assistente Geral de Tempo persistente continua planejado para a Etapa 3.

---

# 8. Mapa de domínios e autoridades

| Domínio | Autoridade principal | Observação |
|---|---|---|
| Dispatcher | `entry.py` | mensagens, callbacks e cron |
| Linguagem compartilhada | `language_primitives.py` | sem efeitos colaterais |
| Contexto curto | `short_context.py` | 30 min, isolamento e histórico |
| Auto-reparo | `correction_patch.py` | Etapa 1.4 |
| Menu principal | `operational_menu.py` | `app.MAIN_KB` sincronizado como fallback |
| Tarefas | `task_context_patch.py`, `runtime_guard.py`, `app.py` | fast paths complementam |
| Compromissos | `operational_menu.py`, `app.py` | entrega em `reliable_reminders.py` |
| Lembretes temporais | `reliable_reminders.py` | autoridade única de `daily_items` |
| Mercado | `grocery_phrase_patch.py`, `quality_patch.py`, `app.py` | relatos claros podem gravar diretamente |
| Rotinas | `routine_integration.py`, `routine_editing.py`, `routine_ui_patch.py` | checkpoints próprios |
| Metas | `goal_operational.py` + `goal_*` | integrada ao menu operacional |
| Acadêmico | `academic_*`, `exam_*`, `attendance_*` | ainda fragmentado; consolidar na Etapa 2 |
| Musculação | `workout_progress_patch.py`, `app.py`, `protocol_mass_data.py` | proprietário × usuário genérico |
| Ler/Ver Depois | `production_usability_patch.py` | migration 0008 |
| Clima | `weather_context.py`, `weather_service.py`, `weather_personality.py` | Open-Meteo + apresentação |
| Resumos | `reliable_summaries.py` | manhã e semanal |
| Administração | `admin_diagnostics.py`, `admin_announcement_flow.py` | proprietário |
| Alarmes pessoais | `personal_alarm.py` | contingência persistente |
| Presença rígida | `attendance_alarm.py` | Durable Object separado |
| Day-off | `day_off_policy.py` | escopo diário |
| Performance | `performance_patch.py` | cache por update e hot path |

Mapa detalhado: `cloudflare/src/README.md`.

---

# 9. Funcionalidades ativas

O runtime de produção cobre:

- tarefas e pendências;
- compromissos e agenda;
- lembretes simples;
- matérias, grade, provas, presença e faltas;
- importação SIGAA por PDF textual/TXT;
- lista de itens faltando em casa;
- rotinas e metas;
- musculação, exercícios, séries, cargas e progresso;
- Ler/Ver Depois;
- clima por usuário;
- Day-off;
- resumo matinal e fechamento semanal;
- alarmes persistentes/redundância temporal;
- diagnóstico e avisos administrativos;
- linguagem natural operacional conservadora;
- contexto curto/referências;
- primeira fatia de auto-reparo temporal.

Finanças continuam preservadas no Core, mas não são destaque do menu principal.

## Ler/Ver Depois

Categorias visíveis:

```text
📚 Livros
🎬 Filmes
🎓 Cursos
🗂️ Outras
```

`Cursos` aqui é captura simples; não significa que o módulo completo de Cursos/Trilhas esteja ativo.

---

# 10. O que não está ativo ainda

Não anunciar como pronto:

- broad NLU/global;
- memória pessoal genérica;
- Butler Library genérica no dispatcher;
- sugestões transversais automáticas;
- Auxiliar de Estudos completo;
- Assistente Geral de Tempo persistente;
- Cursos/Trilhas completos;
- Inbox;
- Projetos/Trabalho completos;
- priorização global;
- voz/web/app.

Código ou documento existir para uma ideia não torna a funcionalidade operacional.

---

# 11. Scheduler, lembretes e alarmes

## Cron operacional

```text
day_off
→ attendance
→ daily_items
→ routines
→ summaries
→ app.scheduled_tick (compatibilidade)
```

Cada subsistema é isolado por `scheduler_runtime.run_isolated()`.

## `daily_items`

`reliable_reminders.py` é a autoridade:

```text
tarefa com horário → no horário
compromisso → 5 min antes
lembrete simples → no horário, tolerância curta
```

`notification_log` evita duplicidade.

## Redundância pós-incidente de 30/08

O Cron Trigger continua primeira linha, mas deixou de ser ponto único de falha.

```text
webhook/cron
→ sync_personal_alarms()
→ PersonalAlarm por usuário
→ próximo evento persistido
→ alarm()
→ dispatchers autoritativos
```

`PersonalAlarm` cobre tarefas com horário, compromissos, lembretes simples, rotinas e resumos. `AttendanceAlarm` permanece separado.

Após webhook, o rearme usa `ctx.waitUntil(...)`. No cron, sincronização é síncrona.

Cron e Durable Objects convergem para a mesma idempotência e não criam duas políticas de negócio.

Detalhes: `docs/SCHEDULER_REDUNDANCY.md`.

---

# 12. Performance

O caminho quente foi otimizado sem criar cache global.

`performance_patch.py` reaproveita, **somente durante um update**:

```text
telegram_chat_id → user_id
user_sessions
```

Outras decisões:

- gate lexical antes de consultas de contexto irrelevantes;
- DDL defensivo de presença fora do dispatcher geral;
- reconciliação global de Durable Objects fora da resposta HTTP interativa.

Essas regras devem permanecer protegidas por testes de latência estrutural/round-trips.

---

# 13. Clima

Fonte objetiva: Open-Meteo.

Autoridades:

- `weather_service.py` — dados/preferências/formatação-base;
- `weather_context.py` — comandos e integração com agenda;
- `weather_personality.py` — comentário mais humano/descontraído.

Regra permanente: personalidade pode melhorar a apresentação, mas não inventar temperatura, chuva, vento ou chance de precipitação.

Falha meteorológica não derruba agenda/resumo.

---

# 14. Banco de dados

Fonte formal: `cloudflare/migrations/`.

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

Escopo resumido:

- **0001:** usuários, matérias, `daily_items`, mercado, metas, rotinas, finanças, musculação, eventos e notificações;
- **0002:** `user_sessions` e logs de treino;
- **0003:** configurações/faltas acadêmicas;
- **0004:** contexto estruturado preservado;
- **0005:** perfis de meta;
- **0006:** preferências de clima;
- **0007:** avisos administrativos pendentes;
- **0008:** Ler/Ver Depois.

As subetapas 1.1–1.4 usam estruturas existentes e não introduziram migration nova até este snapshot.

Regra de schema:

```text
migration
→ backfill se necessário
→ índice quando justificado
→ ensure_schema defensivo apenas se necessário
→ teste
→ documentação
```

Migration destrutiva exige snapshot/export D1 e rollback documentado.

---

# 15. Multiusuário

Butler nasceu pessoal e evoluiu para multiusuário.

Regras obrigatórias:

- `telegram_chat_id` identifica a conversa externa;
- operações internas obtêm `users.id`;
- tabelas pessoais usam `user_id` ou vínculo equivalente;
- queries/updates filtram usuário;
- contexto, sessão, memória e logs nunca são globais;
- regressões de contexto/persistência devem usar dois usuários quando houver risco.

O proprietário possui capacidades extras, mas seus seeds/treinos/configurações não podem ser aplicados automaticamente aos demais.

---

# 16. Recursos exclusivos do proprietário

A diferenciação usa `owner_profile.is_owner(chat_id)`.

Recursos administrativos incluem:

- diagnóstico/listagem de usuários;
- `/aviso` com prévia;
- envio geral ou por ID interno;
- confirmação/cancelamento por botão.

Antes de distribuição ampla, defaults pessoais versionados devem migrar para configuração/seed privada.

---

# 17. Arquitetura preservada/desativada

O repositório preserva uma geração anterior mais ampla de linguagem, memória e Library:

```text
context_router.py
intent_parser.py
action_policy.py
context_memory.py
context_sync.py
compound_router.py
language_context.py
suggestion_engine.py
deterministic_memory.py
general_memory.py
butler_library.py
library_catalog_handler.py
library_context_bridge.py
library_index.py
knowledge/
companion_*
conversational_*
cultural_background.py
```

Esses arquivos:

- não são o roteador central de produção;
- não devem ser apagados só por estarem fora do dispatcher;
- não devem ser tratados como feature ativa;
- só podem ser reativados seletivamente com precedência, política de escrita, isolamento e regressão definidos.

A reativação seletiva de memória/Library pertence à **Etapa 8**.

---

# 18. Dívida técnica conhecida

## Alta prioridade estrutural

### `app.py` grande

Ainda concentra diversos domínios e compatibilidade histórica. Não fazer reescrita gigante; extrair domínio por domínio quando uma etapa funcional justificar e houver testes.

### Acadêmico/presença fragmentado

Família funcional, mas distribuída em muitos módulos `patch/enhancement/management/production_fix`. Consolidação pertence à Etapa 2.

### Scheduler legado ao final do cron

`app.scheduled_tick` ainda roda por compatibilidade. Remover somente quando as dependências restantes estiverem mapeadas e cobertas.

### Configuração pessoal versionada

Mover para seed/configuração privada antes de uso amplo.

## Prioridade operacional

- automatizar backup D1;
- melhorar observabilidade de migrations/deploy;
- ampliar sequências reais com dois usuários;
- consolidar patches conforme cada domínio for tocado;
- manter regressões de hot path;
- observar saúde real do Cron/Durable Objects.

---

# 19. Segurança e integridade

## Telegram

- token nunca entra no repositório;
- webhook suporta secret;
- ações administrativas exigem identidade do proprietário;
- callback sensível não confia só no dado do botão.

## Banco

- isolamento de usuário é invariante;
- migrations destrutivas exigem backup/rollback;
- updates críticos usam ID + usuário quando aplicável;
- idempotência deve existir em callbacks/schedulers repetíveis.

## APIs externas

Falha de Open-Meteo não impede resumo/agenda. Falha Telegram deve ser tratada conforme criticidade da entrega.

---

# 20. Testes e regressão

Workflow: `.github/workflows/butler-regression.yml`.

A suíte:

- compila `cloudflare/src`;
- roda pytest em CPython;
- usa stubs mínimos para JS/Pyodide/Workers;
- não simula rede real.

Coberturas recentes incluem:

- dispatcher/callback/cron;
- corpus da Etapa 1;
- contexto curto/referências;
- dois usuários;
- auto-reparo temporal;
- fallback persistente do scheduler;
- hot path/round-trips D1;
- personalidade do clima.

Regra futura para mudança de comportamento:

```text
caso feliz
+ variação natural próxima
+ falso positivo
+ correção/cancelamento quando aplicável
+ dois usuários quando houver persistência/contexto
+ idempotência quando houver tempo/callback
```

---

# 21. Deploy e operação

Runtime esperado:

```text
Cloudflare Worker
D1
Durable Objects
Telegram Bot API
Open-Meteo
```

Configuração relevante está em `cloudflare/wrangler.jsonc` e secrets do ambiente.

`/health` registra capacidades/flags, mas não substitui teste de fluxo real.

CI verde confirma código/testes no GitHub; **não confirma que o deploy Cloudflare ocorreu**.

---

# 22. Próximas etapas — intenção de produto

## Etapa 2 — Acadêmico + importação robusta

- edição integral de matérias;
- múltiplos horários/localizações;
- modelo acadêmico normalizado;
- pipeline de importação com prévia/correção/confirmação;
- SIGAA como adaptador, não modelo interno;
- presença sempre explícita.

## Etapa 3 — Auxiliares de Tempo / Modo Estudo

- sessão ativa de estudo;
- foco/pausa;
- tópico atual;
- progresso explícito;
- assistente geral de tempo/timers persistentes.

## Etapa 4 — Cursos e trilhas

Modelo conceitual:

```text
Curso
→ módulo
   → conteúdo
      → materiais/atividades
      → progresso
```

Curso autogerido e curso ao vivo têm políticas diferentes; conclusão é explícita.

## Etapa 5 — Inbox

Captura rápida sem obrigar classificação imediata.

## Etapa 6 — Projetos e trabalho

Estado, próximos passos, bloqueios e “onde parei?”.

## Etapa 7 — Resumo/contexto/priorização

Combinar dados reais para ajudar a decidir o que merece atenção hoje/na semana, usando regras explicáveis.

## Etapa 8 — Memória + Library seletiva

Reativar somente componentes que agreguem valor sem sequestrar o Core.

## Etapa 9 — Hardening

Backup, recuperação, observabilidade, segurança, consolidação arquitetural e preparação para distribuição mais ampla.

---

# 23. Definition of Done global

Uma mudança no Butler só está concluída quando, conforme aplicável:

- comportamento está no módulo autoritativo;
- persistência é isolada por usuário;
- migration existe quando há schema novo;
- callbacks são idempotentes;
- scheduler não duplica entrega;
- Day-off é respeitado;
- UX possui cancelamento/voltar em fluxo guiado;
- testes cobrem a mudança;
- CI passa;
- documentação relevante foi sincronizada;
- nenhum recurso preservado é anunciado como ativo;
- deploy real é validado separadamente quando necessário.

---

# 24. Hierarquia documental

Ordem recomendada para outra IA:

1. `docs/STATUS_ATUAL.md` — onde estamos;
2. `docs/BUTLER_DOSSIE_MESTRE.md` — visão completa/decisões;
3. `docs/ARCHITECTURE.md` — runtime técnico;
4. `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md` — roadmap;
5. documento da subetapa atual (`ETAPA_1_4_CORRECOES.md` no snapshot atual);
6. `docs/SCHEDULER_REDUNDANCY.md` — arquitetura temporal de contingência;
7. `docs/MAINTAINER_GUIDE.md` — manutenção prática;
8. `cloudflare/src/README.md` — mapa de módulos;
9. `CONTINUIDADE.md` — decisões duradouras;
10. `INVENTARIO_ETAPA_0.md` / `AUDIT_MAIN_2026-08.md` — histórico estrutural.

Cada documento tem função diferente. **Não usar um snapshot histórico para contradizer `STATUS_ATUAL.md` ou `ARCHITECTURE.md`.**

---

# 25. Regra de continuidade

Ao assumir o Butler:

1. confira `docs/STATUS_ATUAL.md`;
2. verifique se a `main` avançou depois do SHA/snapshot registrado;
3. leia commits novos se houver;
4. continue a etapa/subetapa aberta;
5. localize o handler real em `entry.py`;
6. identifique o módulo autoritativo;
7. teste o caminho real;
8. atualize documentação junto com o comportamento;
9. só avance de etapa quando o gate estiver fechado.

No estado de 31/08/2026, o próximo trabalho oficial é **continuar a Etapa 1.4**, não iniciar a Etapa 2 e não criar um novo roadmap.
