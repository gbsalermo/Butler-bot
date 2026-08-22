# Butler — teste local isolado

Este guia executa o **Worker atual** do Butler localmente, com D1 local e um bot do Telegram separado. Ele não usa o banco D1 de produção e não exige trocar o token do bot oficial.

## 1. Entrar na branch da Etapa 0

```bash
git fetch origin
git switch feat/stability-conversation-real
git pull origin feat/stability-conversation-real
```

## 2. Preparar o bot de teste

Crie outro bot no BotFather e copie o token dele.

Dentro de `cloudflare/`, copie `.dev.vars.example` para `.dev.vars` e preencha:

```env
TELEGRAM_BOT_TOKEN=TOKEN_DO_BOT_DE_TESTE
TELEGRAM_WEBHOOK_SECRET=um-segredo-local-qualquer
```

`.dev.vars` está no `.gitignore`. Nunca use o token do Butler oficial neste arquivo durante os testes da branch.

## 3. Instalar dependências

Requisitos: Node/npm e `uv` disponíveis no terminal.

Se ainda não tiver `uv`:

```bash
python -m pip install uv
```

Depois:

```bash
cd cloudflare
uv sync --dev
```

## 4. Criar o D1 local

Ainda dentro de `cloudflare/`:

```bash
npx wrangler d1 migrations apply butler-db --local
```

O `--local` é obrigatório: ele aplica as migrations somente no banco local usado pelo ambiente de desenvolvimento.

## 5. Rodar o Worker atual

Terminal 1, dentro de `cloudflare/`:

```bash
uv run pywrangler dev
```

O Worker ficará disponível normalmente em `http://localhost:8787`.

Teste de saúde opcional:

```text
http://localhost:8787/health
```

## 6. Dar uma URL pública temporária ao Telegram

O Telegram precisa alcançar o webhook pela internet. Abra um Terminal 2 e rode:

```bash
npx wrangler tunnel quick-start http://localhost:8787
```

Copie a URL `https://...trycloudflare.com` exibida pelo comando.

## 7. Apontar somente o bot de teste para o Worker local

No Terminal 3, na raiz do repositório:

```bash
python scripts/telegram_test_webhook.py set https://SUA-URL.trycloudflare.com
python scripts/telegram_test_webhook.py info
```

O script acrescenta `/telegram/webhook` automaticamente e usa o token/secret de `cloudflare/.dev.vars`.

Agora fale normalmente com o bot de teste no Telegram.

## 8. Bateria manual da Etapa 0

Teste estas mensagens como mensagens separadas:

```text
/start
cria um lembrete hoje 21h de encontrar um lugar para armazenar jogos e emuladores
amanhã tenho que entregar o relatório do estágio
preciso revisar swagger amanhã
preciso comprar café
me lembra de comprar café amanhã às 18h
segunda eu não vou pra Sistemas Digitais I
hoje não vou conseguir treinar
ameanhã tenho dentista às 15h
gastei 27 reais no almoço
```

Também teste mudanças bruscas de assunto:

```text
receita de carbonara
queria faltar essa aula de Sistemas Digitais I
```

```text
pokemon fire red
me lembra de entregar o relatório amanhã às 18h
```

```text
me recomenda uma série curta
preciso comprar arroz
```

A segunda mensagem de cada sequência deve obedecer ao novo domínio explícito e nunca ser sequestrada pelo contexto anterior.

> Observação: se usar o exemplo de lembrete com `hoje 21h` depois desse horário, troque por um horário futuro.

## 9. Regressão automática

Dentro de `cloudflare/`:

```bash
uv run pytest -q
```

A Etapa 0 acrescenta regressões de frases reais e isolamento de memória entre usuários.

## 10. Encerrar o teste

Antes de fechar o ambiente, remova o webhook do bot de teste:

```bash
python scripts/telegram_test_webhook.py delete
```

Depois encerre o Quick Tunnel e o `pywrangler dev` com `Ctrl+C`.

## Como reportar um caso quebrado

Guarde somente:

```text
Mensagem enviada:
Resposta recebida:
O que deveria ter acontecido:
```

Não envie token, `.dev.vars` ou arquivos da pasta `.wrangler`.
