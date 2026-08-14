# Butler Bot

Assistente pessoal via Telegram para organização acadêmica, tarefas, compromissos, pendências, casa, metas, musculação, autocuidado e finanças pessoais.

O projeto começa em execução local via **polling**, com persistência em **SQLite**, e será preparado posteriormente para hospedagem 24/7.

## Visão do Butler

O Butler deve reduzir carga mental: guardar o que você não quer esquecer, organizar o dia e iniciar conversas quando algo importante estiver chegando.

Menu principal atual:

- 📚 Matérias
- ✅ Tarefas
- 📅 Compromissos
- 📌 Pendências
- 🏠 Cotidiano
- 🗓️ Hoje
- 💰 Finanças

## Funcionalidades atuais

### Acadêmico

- `/start` registra o `chat_id`;
- grade do semestre cadastrada automaticamente;
- gerenciamento de matérias: adicionar, remover, trancar e editar;
- tradução automática de códigos SIGAA (`3T23`, `35M45`, `24M23` etc.);
- modo manual para horários especiais;
- aviso automático aproximadamente 10 minutos antes das aulas;
- matérias trancadas são ignoradas pelos lembretes.

### Tarefas, compromissos e pendências

Cada tipo permite cadastrar título, data, horário e observações, listar pendentes e concluir/resolver. Itens com data e horário podem gerar aviso automático antes do compromisso.

### 🗓️ Hoje

A visão diária reúne:

- aulas do dia;
- tarefas;
- compromissos;
- pendências;
- musculação programada para aquele dia;
- quantidade de itens marcados como faltando em casa.

### 🏠 Cotidiano

#### Lista persistente de itens faltando

Não é uma lista descartável de uma ida ao mercado. O Butler mantém uma lista permanente do que está faltando em casa.

Você pode adicionar itens conforme percebe que acabaram e, quando estiver no mercado, consultar pelo botão **🛒 O que está faltando?** ou simplesmente enviar:

```text
O que está faltando?
```

Ao comprar algo, use **✅ Marcar comprado** para retirá-lo da lista de faltas.

#### Metas gerais

Metas não ficam restritas a dinheiro. O módulo aceita qualquer categoria, incluindo bases pessoais como:

- água;
- alimentação;
- inglês;
- programação;
- musculação;
- estudos;
- financeiro.

Cada meta pode ter alvo numérico, unidade e periodicidade, como `2 litros por dia`, `5 horas por semana` ou `4 treinos por semana`.

#### Musculação

O Butler armazena uma rotina semanal por dia e foco muscular. Dentro de cada dia podem ser cadastrados exercícios com:

- nome;
- carga;
- séries;
- repetições.

Exemplo conceitual:

```text
Segunda-feira — Peito
• Supino reto — 4x10 — 20 kg cada lado
• Supino inclinado — 4x12 — 16 kg cada lado

Terça-feira — Costas e bíceps
• Remada baixa — 4x12 — 50 kg
• Rosca direta — 3x10 — 20 kg
```

### Finanças

O módulo financeiro ainda está em evolução. A direção planejada inclui entradas/saídas, categorias, saldo mensal, comparação histórica, detecção de exageros, economia, metas e alertas de ritmo de gasto.

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

## Estrutura

```text
Butler-bot/
├── CONTINUIDADE.md
├── README.md
├── requirements.txt
└── src/
    ├── assistant_views.py
    ├── bot_handlers.py
    ├── config.py
    ├── daily_store.py
    ├── database.py
    ├── home_handlers.py
    ├── home_menu.py
    ├── home_store.py
    ├── lifestyle_handlers.py
    ├── main.py
    ├── scheduler.py
    └── sigaa_schedule.py
```

## Como executar

```bash
git pull origin main
pip install -r requirements.txt
python -m src.main
```

Configure o `.env` a partir do `.env.example` com seu token do BotFather.

## Direção de desenvolvimento

A prioridade atual é funcionalidade antes de suíte de testes. As decisões e o próximo bloco estão registrados em `CONTINUIDADE.md`.
