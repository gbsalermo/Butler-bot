# Butler Bot — Cloudflare Worker

Esta pasta é a adaptação de produção do Butler para Cloudflare Workers, seguindo o mesmo princípio usado no BusiVS: a versão local permanece separada e o Worker recebe updates do Telegram via HTTP/webhook.

## Branches

- `local`: rolling local atual, com polling/SQLite e dados pessoais existentes.
- `cloudflare`: adaptação limpa para Worker/D1. Usuários comuns começam vazios. Os dados pessoais do proprietário só são semeados quando o `chat_id` recebido corresponde a `OWNER_CHAT_ID`.

## Segurança/configuração

O único secret obrigatório do Worker é:

```text
TELEGRAM_BOT_TOKEN
```

O `chat_id` do proprietário não é considerado segredo e fica em `src/settings.py`.

Não colocar o token no repositório. Configure-o com Wrangler:

```bash
cd cloudflare
uv sync
uv run pywrangler secret put TELEGRAM_BOT_TOKEN
```

## D1

Crie o banco:

```bash
npx wrangler d1 create butler-db
```

Copie o `database_id` retornado para `wrangler.jsonc`, substituindo:

```text
REPLACE_AFTER_D1_CREATE
```

Aplique o schema:

```bash
npx wrangler d1 execute butler-db --remote --file=migrations/0001_initial.sql
```

O D1 usa um único banco com `user_id` em todas as entidades relevantes. `telegram_chat_id` identifica cada perfil e impede que dados de usuários diferentes sejam misturados.

## Proprietário

Antes do deploy, substituir em `src/settings.py`:

```python
OWNER_CHAT_ID = 0
```

pelo `chat_id` numérico real do proprietário.

Quando esse chat fizer `/start`, o Worker associa o perfil pessoal e semeia a grade acadêmica definida em `owner_profile.py`. Qualquer outro chat começa limpo.

## Desenvolvimento

```bash
cd cloudflare
uv sync
uv run pywrangler dev
```

Saúde:

```bash
curl http://localhost:8787/health
```

Webhook local/manual:

```text
POST /telegram/webhook
```

## Deploy

```bash
uv run pywrangler deploy
```

Depois valide:

```text
https://<worker>.workers.dev/health
```

Somente após `/health` responder corretamente, registre no Telegram:

```text
https://<worker>.workers.dev/telegram/webhook
```

## Scheduler

`wrangler.jsonc` possui Cron Trigger de 1 minuto. `entry.py` já expõe `scheduled()`. A próxima etapa é portar as regras atuais de lembretes/resumos do JobQueue local para operações idempotentes em D1, usando `notification_log` para evitar mensagens duplicadas.

## Estado da migração

Já preparado:

- Python Worker;
- `/health`;
- `/telegram/webhook`;
- envio direto pela Telegram Bot API;
- binding D1;
- schema multiusuário;
- perfil proprietário condicionado a `chat_id`;
- usuários comuns limpos;
- Cron Trigger/scheduled handler;
- `TELEGRAM_BOT_TOKEN` como único secret obrigatório.

Ainda precisa ser portado antes de produção funcional completa:

- menus/callbacks;
- tarefas/compromissos;
- grade e importação;
- linguagem natural;
- mercado;
- metas/streaks;
- musculação;
- finanças;
- personalidade comportamental;
- lembretes;
- resumo matinal e semanal.

A regra é portar por paridade com o rolling local, sem redesenhar funcionalidades durante a migração.
