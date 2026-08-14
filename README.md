# Butler Bot

Assistente pessoal via Telegram para organização acadêmica, tarefas, compromissos, pendências, autocuidado e, futuramente, finanças pessoais.

O projeto começa em execução local via **polling**, com persistência em **SQLite**, e será preparado posteriormente para hospedagem 24/7.

## Visão do Butler

O Butler deve funcionar como um assistente cotidiano de verdade: não apenas responder comandos, mas lembrar horários, organizar responsabilidades e iniciar conversas quando houver algo importante chegando.

Áreas principais do menu:

- 📚 Matérias
- ✅ Tarefas
- 📅 Compromissos
- 📌 Pendências
- 💰 Finanças
- 🗓️ Hoje

## Funcionalidades atuais

### Acadêmico

- registro do `chat_id` no `/start`;
- grade do semestre carregada automaticamente no primeiro uso;
- consulta de matérias;
- gerenciamento com **Adicionar**, **Remover**, **Trancar** e **Editar**;
- tradução automática de horários SIGAA como `3T23`, `35M45` e `24M23`;
- modo manual para horários especiais;
- aviso automático **10 minutos antes das aulas**;
- matérias trancadas ficam no histórico, mas são ignoradas pelos lembretes.

### Tarefas, compromissos e pendências

Cada categoria possui fluxo para:

- adicionar;
- listar itens pendentes;
- marcar como concluído/resolvido;
- informar data opcional;
- informar horário opcional;
- registrar observações;
- enviar aviso automático 10 minutos antes quando houver data e horário.

O botão **🗓️ Hoje** reúne tarefas, compromissos e pendências marcados para o dia atual.

### Finanças

O módulo já aparece no Butler como área planejada, mas ainda não registra valores.

A evolução prevista inclui:

- entradas e saídas;
- gastos por categoria;
- saldo e gastos do mês;
- comparação com meses anteriores;
- identificação de aumento ou exagero de gastos;
- valor economizado;
- metas de economia e compras;
- alertas quando o ritmo de gasto estiver acima do normal;
- histórico financeiro.

## Grade inicial cadastrada

| Matéria | Dia | Horário | Local |
|---|---|---|---|
| Álgebra Linear I | Terça e quinta | 10:00–11:40 | PAV III, Sala 10 |
| Física II | Segunda e quarta | 10:00–11:40 | PAV III, Sala 07 |
| Laboratório de Sistemas Digitais I | Segunda | 14:00–16:00 | PAV Eng., Sala D6 |
| Princípios de Eletrônica Analógica | Terça e quinta | 08:01–09:40 | PAV I, Sala 104 |
| Sistemas Digitais I | Segunda | 08:01–09:40 | PAV I, Sala 11 |
| Sistemas Digitais I | Quarta | 08:01–09:40 | PAV I, Sala 114 |

> Laboratório de Sistemas Digitais I usa manualmente 14:00–16:00, substituindo o horário inconsistente exibido no SIGAA.

## Tradução dos horários do SIGAA

- números antes da letra: dias (`2` segunda, `3` terça, ..., `7` sábado);
- `M`: manhã;
- `T`: tarde;
- `N`: noite;
- números depois da letra: blocos de aula.

Exemplos:

- `3T23` → terça à tarde, aproximadamente 14h–16h; exato `14:01–15:40`;
- `35M45` → terça e quinta, aproximadamente 10h–12h; exato `10:00–11:40`;
- `24M23` → segunda e quarta, aproximadamente 8h–10h; exato `08:01–09:40`.

## Estrutura

```text
Butler-bot/
├── .env.example
├── .gitignore
├── CONTINUIDADE.md
├── README.md
├── requirements.txt
└── src/
    ├── __init__.py
    ├── bot_handlers.py
    ├── config.py
    ├── daily_store.py
    ├── database.py
    ├── lifestyle_handlers.py
    ├── main.py
    ├── scheduler.py
    └── sigaa_schedule.py
```

## Como executar

```bash
git clone https://github.com/gbsalermo/Butler-bot.git
cd Butler-bot
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Depois:

```bash
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e informe:

```env
TELEGRAM_BOT_TOKEN=seu_token
BUTLER_TIMEZONE=America/Bahia
DATABASE_PATH=data/butler.db
```

Execute:

```bash
python -m src.main
```

No Telegram, envie `/start`.

## Direção de desenvolvimento

A prioridade é ampliar as funcionalidades do Butler antes de investir em suíte de testes. A sequência planejada e as decisões atuais estão em `CONTINUIDADE.md`.
