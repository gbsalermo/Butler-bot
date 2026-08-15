# Butler Bot — Cloudflare Worker

Produção do Butler via Telegram Webhook + Cloudflare Python Worker + D1.

## Estrutura de produção

- branch de produção: `main`;
- fallback local preservado: `local`;
- Worker: `salbutler-bot`;
- root directory do build: `cloudflare/`;
- deploy command: `uv run pywrangler deploy`;
- D1: `butler-db`;
- único secret obrigatório: `TELEGRAM_BOT_TOKEN`;
- identificação do proprietário por `chat_id = 7882764998`;
- cron Cloudflare a cada minuto.

## Arquivos centrais

```text
src/entry.py
→ HTTP, /health, webhook e scheduled()

src/app.py
→ menus, regras, D1, linguagem funcional e scheduler

src/nlu.py
→ interpretação determinística de texto natural

src/telegram_api.py
→ Bot API + download de arquivos

src/owner_profile.py
→ grade e dados iniciais do proprietário

src/protocol_mass_data.py
→ protocolo pessoal de treino preservado da versão local

src/runtime_schema.py
→ cria de forma idempotente as tabelas incrementais necessárias
```

## D1

O schema inicial foi aplicado em `0001_initial.sql`.

Também existe:

```text
migrations/0002_app_state.sql
```

com estado conversacional e histórico de treino. O Worker possui `runtime_schema.py` para garantir essas tabelas de forma idempotente mesmo antes de uma aplicação manual da migration.

Aplicação manual, quando desejado:

```bash
npx wrangler d1 execute butler-db --remote --file=migrations/0002_app_state.sql
```

## Funcionalidades portadas ao Worker

### Interface e identidade

- `/start`;
- menu principal;
- Cotidiano;
- identificação individual por `chat_id`;
- usuário proprietário recebe o perfil pessoal;
- usuário comum começa vazio e informa como quer ser chamado;
- alteração posterior do nome preferido.

### Day-off

- `🌙 Day-off` silencia cobranças daquele usuário;
- reativação com `Chamar, Butler!`;
- estado isolado por usuário.

### Tarefas e compromissos

- fluxo curto por botão;
- validação de data/horário;
- agenda de hoje;
- amanhã;
- outra data;
- próximos 7 dias;
- pendências;
- histórico de tarefas;
- conclusão por linguagem natural;
- personalidade contextual baseada em adiamentos/eventos existentes no D1.

### Acadêmico

- grade pessoal semeada somente para o proprietário;
- usuário comum começa sem matérias;
- listar matérias;
- adicionar;
- trancar;
- remover;
- importação por PDF textual ou `.txt`;
- sem OCR/Tesseract;
- tradução básica dos blocos SIGAA para horas completas;
- horário e local na agenda e nos lembretes.

### Mercado

- adicionar item;
- listar itens faltando;
- marcar item como comprado por texto;
- `preciso comprar café` é tratado como mercado quando o objeto é doméstico.

### Metas / streaks

Categorias-base:

- Inglês;
- Programação;
- Água;
- Alimentação;
- Musculação.

A versão Cloudflare registra progresso e mostra sequência atual, recorde, total e os últimos 7 dias.

### Finanças

- entrada;
- saída;
- categoria;
- descrição opcional;
- relatório mensal;
- saldo registrado;
- agrupamento por categoria;
- limites simples;
- alertas de excesso;
- frases naturais como `gastei 35 com lanche`.

### Musculação

- dados estáticos das 12 semanas do proprietário levados para o Worker;
- `🚀 Começar os trabalhos`;
- treino do dia;
- registro série por série com carga/repetições;
- falta com motivo;
- finalizar treino;
- progresso;
- reiniciar treinos sem apagar o plano;
- importação de treino por PDF textual/`.txt` para usuários que precisam cadastrar ficha;
- usuários comuns mantêm plano próprio em D1.

### Linguagem natural

O dispatcher reconhece, entre outras formas:

```text
Butler, amanhã tenho dentista às 15h
me lembra de entregar o relatório amanhã às 18h
preciso comprar café
falta sal, açúcar e café
o que tenho daqui a 3 dias?
o que ficou pendente?
já fiz o relatório
vou me atrasar para o dentista
hoje não vou treinar porque estou cansado
gastei 35 com lanche
recebi 540 de bolsa
quanto gastei esse mês?
```

A regra continua sendo: agir quando estiver claro e evitar inventar quando houver ambiguidade.

## Scheduler Cloudflare

O cron roda a cada minuto e utiliza `notification_log` para idempotência.

Atualmente cobre:

- aula: aviso 10 minutos antes;
- compromisso: aviso 10 minutos antes;
- tarefa com horário: aviso no horário;
- resumo matinal: 07:30, horário local configurado;
- fechamento semanal: domingo 20:00;
- Day-off bloqueia esses envios.

Não existe fechamento automático noturno.

## Saúde

```text
GET /health
```

Versão funcional deve retornar também:

```json
"dispatcher": "functional-v1"
```

## Segurança

O token não deve entrar no GitHub. `wrangler.jsonc` usa `keep_vars` e declara `TELEGRAM_BOT_TOKEN` como secret obrigatório.

## Fluxo normal daqui para frente

```text
alteração em main
→ Cloudflare Build detecta o push
→ pywrangler deploy
→ Worker atualizado
```

A branch `local` permanece como referência/fallback de polling e SQLite.
