# Butler Bot — Cloudflare Worker

Este diretório contém o **runtime de produção** do Butler: Telegram Webhook + Cloudflare Python Worker + D1 + Durable Objects.

## Antes de editar código

Leia nesta ordem:

1. `../docs/BUTLER_DOSSIE_MESTRE.md` — visão completa do produto e manutenção;
2. `../docs/ARCHITECTURE.md` — fonte de verdade do runtime;
3. `../docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md` — roadmap oficial;
4. `../docs/INVENTARIO_ETAPA_0.md` — classificação estrutural após a limpeza;
5. `../docs/MAINTAINER_GUIDE.md` — regras práticas;
6. `src/README.md` — mapa módulo por módulo.

`../docs/AUDIT_MAIN_2026-08.md` permanece como histórico da auditoria anterior.

---

## Estrutura de produção

```text
wrangler.jsonc
  main = src/worker.py

src/worker.py
  → sincroniza Durable Objects
  → herda src/entry.py

src/entry.py
  → GET /health
  → POST /telegram/webhook
  → dispatch_callback()
  → dispatch_message()
  → dispatch_scheduled()

src/app.py
  → núcleo-base/fallback, D1, estados e operações herdadas
```

Branch de produção: `main`.

A ordem de handlers e de instalações em `entry.py` é parte do comportamento. A Etapa 0 tornou a orquestração explícita/testável para reduzir dependência de inspeção textual e monkeypatches implícitos.

---

## Dispatcher operacional

A produção usa fast paths e handlers explícitos. Resumo da precedência:

```text
/start/reset
→ aviso administrativo / diagnósticos
→ despedida prioritária
→ usabilidade / Ler-Ver Depois
→ menu / rotinas / presença / navegação
→ core_fast_path
→ presença / provas / acadêmico
→ lembrete / referência / tarefa / runtime_guard
→ mercado / quality / treino / conversation_layer
→ app.py somente quando botão/estado guiado exigir
→ fallback
```

Callbacks:

```text
admin announcement
→ attendance
→ context/item
```

O antigo desenho `context_router.py + intent_parser.py` continua preservado, mas não governa o webhook principal.

---

## Funcionalidades operacionais

### Interface e identidade

- `/start`;
- menu principal e Cotidiano;
- identificação por `telegram_chat_id`;
- isolamento por `user_id`;
- perfil especial do proprietário por `is_owner(chat_id)`;
- usuário genérico sem grade/protocolo pessoal automático.

### Day-off

Day-off vale para o dia local em que foi ativado e não é automático em sábado/domingo. A expiração acontece antes do dispatcher e antes dos demais subsistemas do cron.

### Tarefas e compromissos

- criação por botão e linguagem natural conservadora;
- conclusão, cancelamento e adiamento;
- agenda de hoje/amanhã/períodos;
- pendências;
- referências curtas;
- compromissos resolvidos saem da tela operacional após janela de UX, sem apagar histórico.

### Lembretes simples

Pedidos explícitos como `me lembra...` usam fast paths conservadores. A entrega temporal é responsabilidade de `reliable_reminders.py`.

### Acadêmico e presença

- matérias, horários e locais;
- importação textual/PDF pesquisável, sem OCR;
- provas e lembretes;
- faltas/presença e limites;
- edição/exclusão controladas;
- alertas de aula prioritários;
- Durable Object para eventos rígidos de presença.

### Mercado

- adicionar/listar itens faltando;
- marcar compra concluída;
- formas claras como `acabou café`/`tô sem detergente` atualizam diretamente a lista segundo a política atual.

### Rotinas e metas

- recorrência e múltiplos checkpoints;
- integração com agenda;
- conclusão pode alimentar meta;
- edição/remoção;
- família `goal_*` instalada pelo menu operacional.

### Musculação

- protocolo pessoal preservado;
- perfil genérico com treino próprio;
- exercício, substituição, séries, cargas, repetições e progresso.

### Ler/Ver Depois

Lista simples por usuário com livro, filme ou categoria customizada. O schema agora possui migration formal `0008_later_items.sql`.

### Clima

- Open-Meteo;
- localização por usuário;
- agenda Hoje/Amanhã + previsão quando aplicável;
- resumo matinal com fallback seguro se a API falhar.

### Administração

Somente proprietário:

- status/listagem de usuários;
- `/aviso` com prévia;
- confirmação/cancelamento por botão;
- envio geral ou direcionado a ID interno;
- estado pendente idempotente no D1.

---

## Scheduler consolidado

O cron configurado em `wrangler.jsonc` roda a cada minuto.

`worker.py` sincroniza primeiro:

- alarmes de presença;
- alarmes pessoais.

Depois `entry.dispatch_scheduled()` executa isoladamente:

```text
day_off
→ attendance
→ daily_items / reliable_reminders
→ routines
→ reliable_summaries
→ app.scheduled_tick (compatibilidade/legado)
```

### Política temporal de `daily_items`

Após a Etapa 0, **`reliable_reminders.py` é a autoridade única**:

- tarefa com horário: no horário;
- compromisso: 5 minutos antes;
- lembrete pessoal: no horário, com tolerância curta;
- `notification_log`: idempotência;
- supressão das chaves equivalentes do scheduler legado;
- confirmação de entrega em canais críticos quando aplicável.

Foram eliminados o scheduler temporal duplicado de `conversation_layer.py`, a política duplicada de `quality_patch.py` e o arquivo `reminder_policy.py`, que existia apenas para neutralizar a duplicidade.

---

## D1 e migrations

A evolução formal do banco está em `migrations/`:

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

Alguns módulos executam `CREATE TABLE/INDEX IF NOT EXISTS` defensivamente para implantação incremental. Isso não substitui migration.

`src/runtime_schema.py` é helper preservado e **não é o bootstrap geral do runtime**.

### Aplicar migrations

Produção/remoto, somente depois de validação:

```bash
npx wrangler d1 migrations apply butler-db --remote
```

Local:

```bash
npx wrangler d1 migrations apply butler-db --local
```

Migration destrutiva exige snapshot/export e plano de rollback. Nunca usar `--remote` apenas para testar uma migration não validada.

---

## `/health`

```text
GET /health
```

O manifesto operacional após a Etapa 0 se identifica como:

```json
"dispatcher": "butler-operational-core-v4",
"stage_zero_consolidation": true
```

Também mantém flags explícitas para NLU ampla, Library genérica, sugestões transversais e memória pessoal genérica desabilitadas.

---

## Arquitetura preservada

`src/knowledge/` e módulos de Library/contexto/memória continuam preservados para as Etapas 1 e 7.

Não implementar correção de produção apenas em `context_router.py`, `intent_parser.py`, `suggestion_engine.py`, `library_catalog_handler.py` etc. sem primeiro conectar/testar o caminho real no dispatcher.

A raiz `../src/` também permanece como runtime histórico polling/SQLite e não deve receber correções de produção por padrão.

---

## Testes

```bash
pytest -q
```

GitHub Actions executa:

```bash
python -m compileall -q src
pytest -q
```

A suíte CPython usa stubs mínimos de `js`, `pyodide` e `workers`. Esses stubs permitem testar funções determinísticas/orquestração; não simulam integração real de rede.

A Etapa 0 acrescentou regressões para:

- ordem de callbacks;
- precedência administrativa;
- ordem do cron;
- Day-off antes do restante;
- autoridade única de menu principal;
- ausência das antigas políticas concorrentes de lembretes.

---

## Desenvolvimento local e segurança

Ao testar Telegram, use bot separado e túnel/webhook temporário. Não substitua o token oficial só para validar branch.

- `TELEGRAM_BOT_TOKEN` permanece secret;
- webhook aceita `TELEGRAM_WEBHOOK_SECRET` quando configurado;
- queries pessoais devem limitar por usuário;
- tokens não entram em logs/repositório;
- callbacks administrativos revalidam autorização/estado no servidor.

---

## Regra para expansão

Antes de criar outro módulo/patch, responda:

1. qual módulo já é dono desse domínio?
2. por que a mudança não cabe nele?
3. quem importa/chama o novo código?
4. qual posição precisa no dispatcher?
5. qual símbolo será sobrescrito?
6. como a camada será removida depois?
7. qual teste demonstra o comportamento final de produção?

O objetivo após a Etapa 0 é **crescer em capacidade sem voltar a crescer em desordem arquitetural**.
