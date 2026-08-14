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

Antes de ativar o webhook em produção, preencher em `src/settings.py`:

```python
OWNER_CHAT_ID: int | None = 123456789
```

com o `chat_id` numérico real do proprietário.

Não existe mais placeholder numérico fingindo ser configuração válida: enquanto o valor estiver `None`, `/health` informa que o proprietário ainda não está configurado.

Quando esse chat fizer `/start`, o Worker associa o perfil pessoal e semeia a grade acadêmica definida em `owner_profile.py`. Qualquer outro chat começa limpo.

## Importação de grade e treino

A regra de arquivos do Butler permanece simples:

- PDF com texto pesquisável/selecionável;
- `.txt`;
- sem OCR/Tesseract;
- imagens e PDFs escaneados precisam ser convertidos antes.

Além da grade acadêmica, a versão genérica agora possui importação de **ficha de musculação** com prévia antes de gravar.

Formato recomendado:

```text
SEGUNDA — Peito
Supino reto | 4x8-10 | 40 kg
Crucifixo | 3x12 | 12 kg

TERÇA — Costas e bíceps
Puxada frente | 4x10 | 45 kg
Rosca direta | 3x8-10 | 20 kg
```

O parser também aceita `;` como separador e formas compactas como `Supino reto 4x8-10 40 kg`.

Ao confirmar, a ficha importada substitui a rotina manual atual daquele usuário; usuários diferentes continuam isolados.

O Worker terá `pypdf` como dependência para preservar a leitura de PDF textual quando o fluxo de upload for portado para o dispatcher HTTP.

## Limpeza pré-deploy

- usuários genéricos não recebem grade/treino pessoal;
- não existem dados fictícios de usuário semeados no D1;
- `OWNER_CHAT_ID` não usa valor de teste;
- o antigo exemplo de treino não faz parte do fluxo planejado de produção;
- **Reiniciar treinos** permanece como funcionalidade real para quem quiser zerar progresso e recomeçar;
- limites financeiros padrão são regras funcionais, não massa de teste.

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

`wrangler.jsonc` possui Cron Trigger de 1 minuto. `entry.py` já expõe `scheduled()`. As regras de lembretes/resumos do JobQueue local devem ser portadas para operações idempotentes em D1, usando `notification_log` para evitar mensagens duplicadas.

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
- `TELEGRAM_BOT_TOKEN` como único secret obrigatório;
- parser/importação de treino no código-base genérico;
- dependência `pypdf` preparada para o Worker.

Ainda precisa ser portado para o dispatcher HTTP antes de chamar a versão Cloudflare de funcionalmente equivalente ao rolling local:

- menus/callbacks;
- tarefas/compromissos;
- grade e upload de arquivo;
- importação de treino pelo webhook;
- linguagem natural;
- mercado;
- metas/streaks;
- musculação e reinício de progresso;
- finanças;
- personalidade comportamental;
- lembretes;
- resumo matinal e semanal.

A regra é portar por paridade com o rolling local, sem redesenhar funcionalidades durante a migração.
