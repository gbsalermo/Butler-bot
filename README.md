# Butler Bot

Assistente pessoal via Telegram para organização diária, tarefas, compromissos, cronograma de aulas e rotinas de autocuidado.

O projeto começa em execução local via **polling**, com persistência em **SQLite**, e será preparado posteriormente para hospedagem 24/7.

## Estado atual

A versão inicial já possui:

- `/start` com registro do `chat_id` do usuário;
- persistência local em SQLite;
- grade do semestre carregada automaticamente no primeiro uso;
- `/materias` para consultar a grade;
- botão **📚 Minhas matérias**;
- botão **⚙️ Gerenciar matérias**;
- submenu com **📚 Ver matérias**, **➕ Adicionar matéria** e **⬅️ Voltar**;
- cadastro guiado de novas matérias pelo Telegram;
- tradução automática de códigos de horário do SIGAA, como `3T23`, `35M45` e `24M23`;
- modo manual para horários fora do padrão do SIGAA;
- prevenção de duplicidade pelo nome da matéria.

## Tradução dos horários do SIGAA

O Butler entende códigos no padrão usado pelo SIGAA:

- números antes da letra: dias da semana (`2` segunda, `3` terça, ..., `7` sábado);
- `M`: manhã;
- `T`: tarde;
- `N`: noite;
- números depois da letra: blocos de aula daquele turno.

Exemplos:

- `3T23` → terça-feira à tarde, aproximadamente das 14h às 16h; horário exato: `14:01–15:40`;
- `35M45` → terça e quinta pela manhã, aproximadamente das 10h às 12h; horário exato: `10:00–11:40`;
- `24M23` → segunda e quarta pela manhã, aproximadamente das 8h às 10h; horário exato: `08:01–09:40`.

O Butler usa os horários exatos internamente para permitir lembretes precisos, mas apresenta uma tradução mais natural durante o cadastro.

## Grade inicial cadastrada

| Matéria | Dia | Horário | Local |
|---|---|---|---|
| Álgebra Linear I | Terça e quinta | 10:00–11:40 | PAV III, Sala 10 |
| Física II | Segunda e quarta | 10:00–11:40 | PAV III, Sala 07 |
| Laboratório de Sistemas Digitais I | Segunda | 14:00–16:00 | PAV Eng., Sala D6 |
| Princípios de Eletrônica Analógica | Terça e quinta | 08:01–09:40 | PAV I, Sala 104 |
| Sistemas Digitais I | Segunda | 08:01–09:40 | PAV I, Sala 11 |
| Sistemas Digitais I | Quarta | 08:01–09:40 | PAV I, Sala 114 |

> O horário de Laboratório de Sistemas Digitais I foi corrigido manualmente para 14:00–16:00, conforme a rotina real da disciplina, em vez do código exibido no SIGAA.

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
    ├── database.py
    ├── main.py
    └── sigaa_schedule.py
```

## Como executar localmente

### 1. Clonar o projeto

```bash
git clone https://github.com/gbsalermo/Butler-bot.git
cd Butler-bot
```

### 2. Criar o ambiente virtual

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar o token

Copie `.env.example` para `.env` e substitua o valor de `TELEGRAM_BOT_TOKEN` pelo token fornecido pelo BotFather.

```env
TELEGRAM_BOT_TOKEN=seu_token
BUTLER_TIMEZONE=America/Bahia
DATABASE_PATH=data/butler.db
```

O arquivo `.env` não deve ser commitado.

### 5. Executar

Na raiz do projeto:

```bash
python -m src.main
```

Depois, abra o bot no Telegram e envie:

```text
/start
```

O Butler criará o banco local e cadastrará automaticamente a grade inicial na primeira execução.

## Próximas etapas

A sequência planejada está registrada em `CONTINUIDADE.md`. O próximo núcleo do projeto será o sistema proativo de lembretes para aulas, compromissos, tarefas e autocuidado.
