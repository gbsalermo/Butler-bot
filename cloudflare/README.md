# Butler Bot — Cloudflare Worker

Este diretório contém o **runtime de produção** do Butler: Telegram Webhook + Cloudflare Python Worker + D1 + Durable Objects.

Para entender o projeto antes de editar código, leia também:

- `../docs/ARCHITECTURE.md` — arquitetura real;
- `../docs/MAINTAINER_GUIDE.md` — regras de manutenção;
- `src/README.md` — mapa de módulos;
- `../docs/AUDIT_MAIN_2026-08.md` — inconsistências encontradas na auditoria.

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
  → dispatcher de mensagens
  → scheduled()

src/app.py
  → núcleo-base/fallback, D1, estados e operações herdadas
```

Branch de produção: `main`.

## O que é fonte de verdade

A ordem de handlers e de `install_*()` em `src/entry.py` é parte do comportamento. Muitos módulos fazem monkeypatch sobre `app.py`, `conversation_layer.py`, `routine_integration.py` e outros.

Não altere uma função em `app.py` supondo automaticamente que ela é a versão executada. Primeiro confira se algum patch posterior a substitui.

Veja `src/README.md` para a classificação de cada módulo como ativo, transitivo, base ou preservado.

## Dispatcher operacional

A produção usa fast paths e handlers explícitos. Resumo da prioridade:

```text
/start/reset
→ diagnóstico
→ usabilidade/menu/navegação
→ Core fast path
→ presença/provas/acadêmico
→ lembretes/referências/tarefas/mercado/treino/contexto
→ app.py somente quando botão/estado guiado exigir
→ fallback
```

O antigo desenho de `context_router.py` + `intent_parser.py` continua no repositório, mas não governa atualmente o webhook principal.

## D1 e migrations

A evolução formal do banco está em `migrations/`:

```text
0001_initial.sql
0002_app_state.sql
0003_attendance.sql
0004_conversation_context.sql
0005_goal_profiles.sql
```

Alguns módulos também executam `CREATE TABLE/INDEX IF NOT EXISTS` defensivamente. Isso é proteção de implantação incremental, não substituto de migration.

`src/runtime_schema.py` é um helper preservado e **não é chamado como bootstrap geral pelo dispatcher atual**.

### Aplicar migrations

Produção/remoto, somente quando a mudança tiver sido preparada para isso:

```bash
npx wrangler d1 migrations apply butler-db --remote
```

Ambiente local:

```bash
npx wrangler d1 migrations apply butler-db --local
```

Nunca use `--remote` só para testar uma migration ainda não validada.

## Funcionalidades operacionais

### Interface e identidade

- `/start`;
- menu principal e Cotidiano;
- identificação por `telegram_chat_id`;
- isolamento por `user_id`;
- perfil especial do proprietário separado por `is_owner(chat_id)`;
- usuário genérico começa sem grade/protocolo pessoal.

### Day-off

Day-off reduz/silencia os avisos compatíveis daquele usuário. O estado fica em `assistant_state`.

### Tarefas e compromissos

- criação por botão e linguagem natural conservadora;
- conclusão, cancelamento e adiamento;
- agenda de hoje, amanhã e períodos;
- pendências;
- referências curtas como “essa tarefa”;
- compromissos resolvidos saem da tela operacional após uma janela, sem apagar histórico.

### Lembretes simples

Pedidos claros como `me lembra...` seguem fast path próprio e usam `reliable_reminders.py` para entrega temporal.

### Acadêmico e presença

- matérias, horários e locais;
- importação textual/PDF sem OCR;
- provas e lembretes de prova;
- faltas/presença;
- limites por matéria;
- edição/exclusão controladas;
- alertas de aula em subsistema prioritário;
- Durable Object para eventos rígidos de presença.

### Mercado

- adicionar/listar itens faltando;
- marcar compra concluída por texto;
- formas claras como `acabou café`, `falta açúcar`, `tô sem detergente` atualizam diretamente a lista no comportamento atual.

Essa última regra difere de um desenho antigo de “sugerir antes de salvar”. Se a política for alterada no futuro, deve ser uma mudança funcional com regressão própria.

### Rotinas e metas

- cadastro de rotina;
- recorrência e múltiplos checkpoints;
- rotina aparece na agenda quando aplicável;
- conclusão pode alimentar meta compatível;
- edição e remoção;
- metas possuem família própria `goal_*`, instalada pelo menu operacional.

### Musculação

- perfil pessoal com protocolo preservado;
- perfil genérico com treino próprio;
- exercício, substituição, séries, carga, repetições e progresso;
- histórico/referências de carga.

### Ler/Ver Depois

`production_usability_patch.py` mantém uma lista simples por usuário com:

- livro;
- filme;
- outra categoria informada pelo usuário;
- adicionar;
- listar;
- editar;
- remover.

### Finanças

O Core de finanças permanece no projeto. A interface operacional atual prioriza outras áreas e não apresenta Finanças como item principal em todos os caminhos de menu; ao alterar menus, confira `operational_menu.py` e os fallbacks em `app.py`.

## Scheduler

O cron configurado em `wrangler.jsonc` roda a cada minuto.

`worker.py` sincroniza primeiro:

- alarmes de presença;
- alarmes pessoais.

Depois `entry.py` executa isoladamente:

```text
attendance
→ reliable_reminders
→ routines
→ reliable_summaries
→ app.scheduled_tick (compatibilidade/legado)
```

A falha de um subsistema não deve impedir os demais.

### Política temporal atual

- tarefa com horário: aviso no horário;
- compromisso: 5 minutos antes;
- lembrete pessoal: no horário, sem aceitar atraso grande;
- resumo matinal: 07:00;
- fechamento semanal: domingo 20:00;
- presença/aulas: política própria do subsistema acadêmico.

`notification_log` fornece idempotência.

`scheduled_delivery_guard.py` exige confirmação real da API do Telegram em entregas críticas antes de aceitá-las como sucesso.

## `/health`

```text
GET /health
```

O endpoint é também um manifesto operacional. O dispatcher atual se identifica como:

```json
"dispatcher": "butler-operational-core-v3"
```

Ele também registra flags importantes como NLU ampla, Library genérica, sugestões transversais e memória genérica desabilitadas.

Se uma feature dessas for reativada, o `/health` e a documentação devem mudar junto com o código.

## Butler Library / arquitetura preservada

`src/knowledge/` e vários módulos de Library/contexto continuam no repositório para preservar dados, testes e evolução futura.

Hoje, porém, o dispatcher genérico da Library não está habilitado no webhook de produção.

Não implemente uma correção de produção apenas em `library_catalog_handler.py`, `context_router.py`, `intent_parser.py` ou `suggestion_engine.py` sem primeiro conectar/testar o caminho no dispatcher.

## Testes

```bash
pytest -q
```

A suíte roda em CPython 3.13. O runtime de produção usa Pyodide e disponibiliza `js`/`pyodide.ffi`.

`tests/conftest.py` fornece stubs mínimos somente para permitir importação em testes determinísticos; integração real de rede continua fora desses stubs.

O GitHub Actions também executa:

```bash
python -m compileall -q src
pytest -q
```

## Desenvolvimento local

O Worker pode ser executado localmente com D1 local. Ao testar com Telegram, use um bot separado e um túnel/webhook temporário; nunca substitua o token do bot oficial só para validar uma branch.

Estado local do Wrangler e secrets locais não devem ser commitados.

## Segurança

- `TELEGRAM_BOT_TOKEN` deve permanecer secret;
- o webhook aceita `TELEGRAM_WEBHOOK_SECRET` quando configurado;
- hoje o webhook secret não é obrigatório no `wrangler.jsonc`, portanto endurecê-lo deve ser feito em uma mudança preparada de segurança;
- não registrar tokens em logs;
- queries pessoais devem sempre limitar por usuário.

## Regra para expansão

Antes de criar outro módulo/patch, responda:

1. qual módulo já é dono desse domínio?
2. por que a mudança não cabe nele?
3. quem importa/chama o novo código?
4. qual é a posição no dispatcher?
5. qual símbolo será sobrescrito, se houver monkeypatch?
6. qual teste demonstra o comportamento final de produção?

O objetivo de manutenção agora é consolidar camadas, não criar uma nova camada para cada exceção.
