# Butler — Dossiê Mestre

**Versão:** 1.0  
**Data-base:** 29/08/2026  
**Status:** referência mestre do produto e da manutenção

> Este arquivo explica **o que é o Butler, como a produção está montada, quais módulos são autoridades e como o projeto deve evoluir sem voltar a acumular camadas paralelas**. Para detalhes exatos do runtime, `docs/ARCHITECTURE.md` continua sendo a fonte técnica de verdade. Para ordem futura de evolução, use `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`.

---

# 1. O que é o Butler

Butler é um assistente pessoal via Telegram projetado para acompanhar o estado real do cotidiano do usuário e ajudá-lo a agir sobre ele.

O produto não deve ser reduzido a:

- um CRUD com botões;
- um chatbot genérico;
- uma coleção de regex independentes;
- uma IA que toma decisões sem confirmação;
- um catálogo de funcionalidades sem integração.

A proposta é combinar **operações determinísticas**, **linguagem natural conservadora**, **contexto curto**, **agenda e histórico reais**, **automação temporal confiável** e, futuramente, memória/Library seletivas.

O Butler deve saber trabalhar com informações como:

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
3. **Nada é inventado.** Não presumir presença, conclusão, treino, gasto, compromisso, fato pessoal ou progresso.
4. **Isolamento por usuário é obrigatório.** Toda operação pessoal resolve `telegram_chat_id → user_id` e filtra SQL corretamente.
5. **Ambiguidade de escrita pede confirmação.** Especialmente remoção, alteração ou alvo não identificado.
6. **Botões e texto natural coexistem.** Botão é UX, não a única interface.
7. **Scheduler precisa ser idempotente.** Reprocessar um minuto/evento não pode duplicar notificação crítica.
8. **Falha de um subsistema não derruba os demais.** O cron é isolado por domínio.
9. **Migration é a fonte formal do banco.** `ensure_schema()` é apenas tolerância operacional.
10. **Código novo entra no módulo dono.** Novo patch é exceção, não padrão.
11. **Produção e código preservado são coisas diferentes.** Existir no repositório não significa estar ligado ao webhook.
12. **Uma etapa só termina com regressão.** Funcionar manualmente uma vez não é critério de conclusão.

---

# 3. Arquitetura de produção

## 3.1 Visão

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

O deploy atual usa Cloudflare Worker e webhook. A raiz `src/` contém um runtime histórico em polling/SQLite e não governa produção.

## 3.2 `worker.py`

Responsabilidades:

- ser o entrypoint do Worker;
- sincronizar alarmes persistentes de presença;
- sincronizar alarmes pessoais;
- delegar HTTP e cron ao `entry.Default`.

## 3.3 `entry.py`

É o **orquestrador autoritativo**.

Após a Etapa 0, a lógica foi explicitada em funções testáveis:

```text
dispatch_callback()
dispatch_message()
dispatch_scheduled()
```

Isso permite proteger a precedência do runtime em pytest sem depender de uma requisição HTTP real do Cloudflare.

## 3.4 `app.py`

É o núcleo-base herdado e ainda importante. Mantém:

- bootstrap de usuário;
- estados guiados;
- parte dos CRUDs;
- agenda-base;
- mercado;
- finanças;
- treino-base;
- scheduler de compatibilidade.

Não é, porém, a única fonte da interface final. Instalações de módulos operacionais ainda substituem símbolos de `app.py` no bootstrap.

---

# 4. Dispatcher de mensagens

A ordem é parte do comportamento.

```text
1. start/reset
2. aviso administrativo (prévia)
3. diagnóstico administrativo de usuários
4. diagnóstico de alertas
5. despedida prioritária
6. usabilidade / Ler-Ver Depois
7. menu operacional
8. rotinas UI/edição
9. presença UI
10. navegação global
11. core_fast_path
12. schema/gestão de presença
13. presença natural
14. provas/acadêmico
15. lembrete explícito
16. referências
17. contexto de tarefa
18. runtime_guard
19. mercado informal
20. quality
21. musculação
22. conversation_layer
23. app.py somente se botão ou estado guiado exigir
24. fallback
```

Um handler que retorna `True` consome a mensagem.

### Por que isso importa

Se uma frase cai no domínio errado, o primeiro diagnóstico é:

```text
qual handler anterior capturou a mensagem?
```

Não se deve começar criando mais regex antes de entender a precedência.

---

# 5. Callbacks

Ordem autoritativa:

```text
admin_announcement_flow
→ attendance
→ conversation/context item
```

O aviso administrativo fica primeiro porque seus callbacks possuem efeito de broadcast e precisam de autorização/idempotência próprias.

`test_dispatcher_integration.py` protege essa ordem.

---

# 6. Mapa dos domínios

## 6.1 Menu e navegação

**Autoridade:** `operational_menu.py`.

Menu principal:

```text
➕ Adicionar | 🗓️ Hoje
🛒 Item faltando | 📚 Matérias
🏠 Cotidiano | 🏋️ Musculação
🌙 Day-off
```

`production_usability_patch.py` sincroniza `app.MAIN_KB`/`COTIDIANO_KB` com essa fonte.

A Etapa 0 removeu a cópia divergente do menu principal em `conversation_layer.py`.

## 6.2 Tarefas

Autoridades atuais:

- `task_context_patch.py`;
- `runtime_guard.py`;
- partes-base em `app.py`;
- fast paths em `core_fast_path.py` e auxiliares.

Tarefa vencida e não concluída permanece pendente. Conclusão deve ser explícita.

## 6.3 Compromissos

Autoridades:

- `operational_menu.py` para navegação/listagem;
- `app.py` para parte do cadastro guiado;
- `reliable_reminders.py` para alerta temporal.

Compromisso passado pode sair da tela operacional sem ser apagado do histórico.

## 6.4 Mercado

Autoridades:

- `grocery_phrase_patch.py`;
- `quality_patch.py` para algumas formulações informais;
- `app.py` para base/listagem.

Política atual: relatos claros como “acabou o café” são tratados como atualização explícita do estado doméstico e entram na lista. Alterar essa política exige mudança funcional própria.

## 6.5 Rotinas

Autoridades:

- `routine_integration.py`;
- `runtime_guard.py`;
- `routine_ui_patch.py`;
- `routine_editing.py`;
- `quality_patch.py` somente para checkpoint inteligente.

A Etapa 0 retirou de `quality_patch.py` a responsabilidade por lembretes de tarefas/compromissos.

## 6.6 Metas

Autoridade principal: `goal_operational.py`.

Complementos ativos instalados por `operational_menu.py`:

- `goal_polish.py`;
- `goal_deadline_patch.py`;
- `goal_routine_bridge.py`;
- `goal_natural_patch.py`.

## 6.7 Acadêmico

Família ativa:

- `academic_intelligence.py`;
- `academic_polish.py`;
- `exam_phrase_patch.py`;
- `exam_cancel_patch.py`;
- `attendance_patch.py`;
- `attendance_enhancement.py`;
- `attendance_management.py`;
- `attendance_production_fix.py`;
- `attendance_alarm.py`.

Essa família funciona, mas ainda é uma das maiores concentrações de patches sobrepostos. A consolidação funcional e edição completa de matérias pertencem à **Etapa 2**.

## 6.8 Musculação

Autoridades:

- `workout_progress_patch.py`;
- base de treino em `app.py`;
- `protocol_mass_data.py` para o perfil Protocol Mass.

Regras:

- não inferir carga/repetição;
- substituição não apaga histórico;
- protocolo pessoal não deve ser aplicado automaticamente a usuários genéricos.

## 6.9 Ler/Ver Depois

Autoridade: `production_usability_patch.py`.

Categorias básicas:

```text
livro
filme
outra categoria informada pelo usuário
```

A Etapa 0 formalizou a tabela `later_items` na migration `0008_later_items.sql`.

## 6.10 Clima

Autoridades:

- `weather_context.py`;
- `weather_service.py`.

Fonte: Open-Meteo.

Integrado a:

- `Hoje`/`Amanhã` quando aplicável;
- consulta direta de clima;
- resumo matinal.

Falha meteorológica não pode derrubar a agenda.

## 6.11 Administração

Somente proprietário:

- `admin_diagnostics.py` — contagem/lista de usuários registrados;
- `admin_announcement_flow.py` — prévia e confirmação de avisos para usuários.

Broadcast exige confirmação. A confirmação por botão usa `admin_pending_announcements`, expira e é idempotente.

---

# 7. Scheduler, lembretes e alarmes

## 7.1 Cron operacional

`entry.dispatch_scheduled()`:

```text
day_off
→ attendance
→ daily_items
→ routines
→ summaries
→ legacy
```

Cada etapa passa por `scheduler_runtime.run_isolated()`.

## 7.2 Durable Objects

`worker.py` sincroniza:

- alarmes persistentes de presença;
- alarmes pessoais.

Eles existem para eventos pontuais mais críticos do que um simples sweep periódico.

## 7.3 Autoridade de `daily_items`

Após a Etapa 0, `reliable_reminders.py` é a única política temporal autoritativa para tarefas, compromissos e lembretes simples.

Política:

```text
tarefa com horário → no horário
compromisso → 5 min antes
lembrete simples → no horário, tolerância curta
```

Garantias:

- `notification_log` evita duplicidade;
- chave do scheduler legado é suprimida para evitar dupla entrega;
- caminho crítico valida entrega Telegram antes de considerar o aviso concluído;
- atrasos excessivos não viram notificações obsoletas.

## 7.4 Consolidação feita na Etapa 0

Antes existiam camadas redundantes:

```text
quality_patch
→ conversation_layer._pre_send_item_reminders
→ reminder_policy substituía por noop
→ reliable_reminders rodava por fora
```

Agora:

```text
reliable_reminders = autoridade
conversation_layer = contexto/agenda
quality_patch = rotina + mercado
reminder_policy = removido
```

Essa simplificação reduz comportamento implícito por monkeypatch.

---

# 8. Banco de dados

A fonte formal é `cloudflare/migrations/`.

## 8.1 Migration 0001 — base

Principais tabelas:

```text
users
assistant_state
subjects
subject_sessions
daily_items
grocery_items
goals
goal_progress
routines
routine_logs
finance_entries
finance_limits
workout_days
workout_exercises
protocol_mass_state
protocol_mass_sessions
protocol_mass_exercise_logs
protocol_mass_set_logs
natural_events
notification_log
```

## 8.2 Migration 0002

```text
user_sessions
workout_logs
workout_set_logs
```

## 8.3 Migration 0003

```text
subject_attendance_settings
subject_absences
```

## 8.4 Migration 0004

```text
conversation_context
```

Tabela preservada para arquitetura estruturada de contexto; não é o roteador central atual.

## 8.5 Migration 0005

```text
goal_profiles
```

## 8.6 Migration 0006

```text
weather_preferences
```

## 8.7 Migration 0007

```text
admin_pending_announcements
```

## 8.8 Migration 0008

```text
later_items
```

Criada na Etapa 0 para alinhar Ler/Ver Depois à disciplina formal de migrations.

## 8.9 Regra de schema

Para qualquer nova persistência:

```text
migration
→ backfill se necessário
→ índice se consulta quente exigir
→ ensure_schema defensivo apenas se necessário
→ teste
→ documentação
```

Não criar uma tabela apenas em `ensure_schema()` e esquecer a migration.

---

# 9. Multiusuário

Butler nasceu pessoal e evoluiu para multiusuário. Essa transição exige disciplina.

Regras obrigatórias:

- `telegram_chat_id` identifica a conversa externa;
- operações internas devem obter `users.id`;
- tabelas pessoais usam `user_id` ou vínculo indireto que preserve o dono;
- consultas e updates precisam filtrar o usuário;
- contexto, sessão, memória e logs nunca são globais;
- testes relevantes devem usar ao menos dois usuários quando houver risco de vazamento.

O proprietário possui capacidades extras, mas isso não autoriza aplicar seus seeds/treinos/configurações pessoais aos demais.

---

# 10. Recursos exclusivos do proprietário

Hoje há diferenciação explícita por `owner_profile.is_owner(chat_id)`.

Recursos administrativos:

- `/status usuarios` e aliases;
- `/aviso ...` com prévia;
- envio para todos os usuários não proprietários;
- envio para ID interno específico;
- confirmação/cancelamento por botão.

Defaults pessoais também existem em `settings.py`/perfil proprietário, incluindo localização meteorológica padrão.

Antes de distribuir o Butler amplamente, configuração pessoal deve migrar para seed/configuração privada.

---

# 11. Linguagem e contexto — estado atual

A produção **não usa uma NLU ampla como roteador central**.

O modelo atual privilegia:

```text
fast paths conservadores
+ handlers por domínio
+ estados guiados
+ contexto operacional curto
+ fallback estreito
```

`conversation_layer.py` e `natural_events` ajudam com referências recentes como:

```text
essa
ela
isso
a anterior
```

Há também `user_sessions` para fluxos guiados.

Essa opção foi tomada por confiabilidade. A **Etapa 1** deve melhorar português natural — conjugações, conjunções, frases compostas, correções e elipses — sem religar cegamente toda a NLU histórica.

---

# 12. Arquitetura preservada/desativada

O repositório preserva uma geração anterior mais ampla de linguagem, memória e Library.

Principais componentes:

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

Esses arquivos não devem ser apagados só por estarem fora do dispatcher. Eles concentram trabalho que pode ser reaproveitado nas Etapas 1 e 7.

Também não devem ser tratados como funcionalidade ativa.

Flags do `/health` continuam deixando isso explícito:

```text
broad_nlu_disabled
generic_library_dispatch_disabled
cross_domain_suggestions_disabled
generic_personal_memory_disabled
```

---

# 13. Limpeza realizada na Etapa 0

## 13.1 Remoções comprovadas

### `add_intent_patch.py`

Removido porque não estava conectado ao runtime e duplicava um caminho de intenção já absorvido pela arquitetura operacional.

### `reminder_policy.py`

Removido depois que a função que ele neutralizava deixou de existir. Manter um módulo cuja única função é transformar outro scheduler em `noop` esconderia a arquitetura em vez de simplificá-la.

## 13.2 Consolidações

- menu principal deixou de ser duplicado em `conversation_layer.py`;
- `quality_patch.py` deixou de possuir política temporal de tarefas/compromissos;
- `conversation_layer.py` deixou de enviar lembretes de `daily_items`;
- `reliable_reminders.py` passou a ser explicitamente a autoridade única;
- dispatcher e cron foram extraídos para funções testáveis;
- Ler/Ver Depois ganhou migration formal.

---

# 14. Dívida técnica conhecida

## Prioridade alta

### 14.1 `app.py` grande

Ainda concentra código-base de diversos domínios e compatibilidade histórica. Não deve ser quebrado em uma reescrita gigante. A estratégia é extrair domínio por domínio quando houver testes e uma etapa funcional justificar.

### 14.2 Acadêmico/presença fragmentado

A família funciona, mas possui muitos módulos `patch/enhancement/management/production_fix`. A Etapa 2 deve consolidar responsabilidades enquanto implementa edição completa de matérias e importador normalizado.

### 14.3 Scheduler-base ainda executado

`app.scheduled_tick` roda ao final por compatibilidade. O objetivo futuro é reduzir o que depende desse caminho até que ele possa ser retirado com prova de regressão.

### 14.4 Configuração pessoal em código

Ainda há defaults do proprietário versionados. Antes de produto genérico, mover para configuração/seed privado.

## Prioridade média

- automatizar backup D1;
- tornar aplicação de migrations mais observável;
- ampliar testes de sequências reais com dois usuários;
- consolidar patches pequenos conforme cada domínio for tocado;
- revisar exigência de secret do webhook.

## Prioridade planejada

- decidir reativação de memória/Library;
- decidir destino final do runtime raiz `src/`;
- voz/web/app somente após estabilidade do roadmap atual.

---

# 15. Segurança e integridade

## Telegram

- token nunca entra no repositório;
- webhook suporta secret;
- ações administrativas exigem identidade autoritativa do proprietário;
- callback administrativo não confia apenas em dados vindos do botão.

## Banco

- foreign keys e isolamento de usuário são invariantes;
- migrations destrutivas exigem backup/rollback;
- updates críticos devem usar ID + usuário quando aplicável;
- idempotência deve existir para callbacks e schedulers repetíveis.

## APIs externas

Falha de Open-Meteo não pode impedir resumo/agenda. Falha Telegram deve ser tratada conforme criticidade da entrega.

---

# 16. Estratégia de backup e recuperação

Ainda não há rotina automática versionada de backup D1.

Regra provisória obrigatória:

1. migration aditiva simples pode seguir o fluxo normal;
2. migration destrutiva ou backfill de alto impacto exige export/snapshot prévio;
3. PR deve documentar rollback;
4. exclusão de tabela/coluna não ocorre na mesma mudança que introduz o substituto, salvo necessidade técnica forte;
5. retenção/automação será fechada no Hardening (Etapa 8).

---

# 17. Testes e regressão

Workflow: `.github/workflows/butler-regression.yml`.

A suíte:

- compila `cloudflare/src`;
- roda pytest em Python 3.13;
- usa stubs mínimos de JS/Pyodide para funções determinísticas;
- não simula rede real.

A Etapa 0 adicionou `test_dispatcher_integration.py`, que protege:

- precedência de aviso administrativo;
- precedência de callbacks;
- fallthrough de callback;
- ordem autoritativa dos subsistemas do cron.

### Regra de teste futura

Cada mudança de comportamento deve preferir:

```text
caso feliz
+ variação natural próxima
+ falso positivo
+ correção/cancelamento quando aplicável
+ dois usuários quando houver persistência/contexto
```

---

# 18. Convenções de desenvolvimento

## Antes de alterar

1. leia este Dossiê;
2. confirme `docs/ARCHITECTURE.md`;
3. localize o handler em `entry.py`;
4. identifique o módulo autoritativo;
5. procure teste existente;
6. só então altere código.

## Novo módulo

Um módulo novo deve declarar em docstring:

- responsabilidade;
- quem o chama;
- estado/tabelas que altera;
- invariantes que não pode violar.

## Novo patch

Antes de criar `*_patch.py` ou `*_fix.py`, responder:

```text
Por que não cabe no módulo dono?
Qual símbolo será substituído?
Quem instala?
Em qual ordem?
Como será removido depois?
Qual teste protege a substituição?
```

Sem respostas claras, não criar patch.

---

# 19. Deploy e operação

Runtime esperado:

```text
Cloudflare Worker
D1
Durable Objects
Telegram Bot API
Open-Meteo
```

Configuração relevante está em `cloudflare/wrangler.jsonc` e secrets do ambiente.

`/health` é o painel técnico de capacidades e flags. A Etapa 0 passa a identificar o dispatcher como `butler-operational-core-v4` e registra a consolidação estrutural.

CI verde confirma código/testes no GitHub; **não deve ser confundido com prova de deploy Cloudflare concluído**.

---

# 20. Documentos e hierarquia

Ordem recomendada de leitura:

1. `docs/BUTLER_DOSSIE_MESTRE.md` — visão completa;
2. `docs/ARCHITECTURE.md` — runtime técnico atual;
3. `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md` — ordem futura;
4. `docs/INVENTARIO_ETAPA_0.md` — classificação estrutural;
5. `docs/MAINTAINER_GUIDE.md` — manutenção prática;
6. `cloudflare/src/README.md` — mapa de módulos;
7. `CONTINUIDADE.md` — decisões duradouras/históricas;
8. `docs/AUDIT_MAIN_2026-08.md` — auditoria anterior preservada como histórico.

Não duplicar a mesma função em todos os documentos. Quando mudar produção, atualizar Arquitetura/Dossiê; quando mudar ordem futura, atualizar Trilha; quando mudar decisão de longo prazo, atualizar Continuidade.

---

# 21. Roadmap oficial

Fonte completa: `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`.

```text
0. 🧹 Arrumar a casa
1. 🗣️ Linguagem natural + conversa real
2. 🎓 Acadêmico + importação
3. 📚 Cursos e trilhas
4. 📥 Caixa de entrada
5. 🗂️ Projetos e trabalho
6. 🧭 Resumo e priorização
7. 🧠 Memória + Library seletiva
8. 🔒 Hardening
```

A Etapa 0 existe para que as próximas funcionalidades entrem em uma base compreensível, e não sobre uma pilha crescente de correções paralelas.

---

# 22. Definition of Done global

Uma mudança no Butler só está concluída quando, conforme aplicável:

- comportamento está no módulo autoritativo;
- persistência é isolada por usuário;
- migration existe;
- callbacks são idempotentes;
- scheduler não duplica entrega;
- Day-off é respeitado conforme política do domínio;
- UX possui cancelamento/voltar quando existe fluxo guiado;
- testes cobrem a mudança;
- CI passa;
- documentação relevante foi sincronizada;
- nenhum recurso preservado é anunciado como ativo sem estar no dispatcher.

---

# 23. Estado ao final da Etapa 0

A base pretendida para iniciar a Etapa 1 é:

```text
✓ produção Cloudflare claramente separada do legado
✓ dispatcher explícito e testável
✓ callback order testável
✓ cron order testável
✓ menu principal com uma autoridade
✓ lembretes de daily_items com uma autoridade
✓ migrations 0001–0008 documentadas
✓ código removido somente com prova de desuso
✓ preservados identificados sem reativação acidental
✓ Dossiê Mestre criado
✓ inventário técnico criado
✓ dívida técnica priorizada
```

A próxima evolução deve ser **Etapa 1 — Linguagem natural + estabilidade de conversa**, sem criar uma NLU ampla e imprevisível. O trabalho deve partir do dispatcher estável, de um corpus de frases reais e de testes de sequência completa.
