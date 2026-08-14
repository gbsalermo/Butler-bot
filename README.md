<p align="center">
  <img src="assets/butler.png" alt="Butler - mascote" width="420">
</p>

# Butler Bot

Assistente pessoal via Telegram para organização acadêmica, tarefas, compromissos, pendências, casa, metas, musculação, autocuidado e finanças pessoais.

O projeto começa em execução local via **polling**, com persistência em **SQLite**, e será preparado posteriormente para hospedagem 24/7.

## Visão do Butler

O Butler deve reduzir carga mental: guardar o que você não quer esquecer, organizar o dia e iniciar conversas quando algo importante estiver chegando — mas também saber a hora de ficar quieto.

Menu principal atual:

- 🌙 Day-off
- 📚 Matérias
- ✅ Tarefas
- 📅 Compromissos
- 📌 Pendências
- 🏠 Cotidiano
- 🗓️ Hoje
- 💰 Finanças

## 🌙 Day-off

O Day-off representa um dia em que agenda, metas e cobranças não importam. Pode ser folga, descanso ou simplesmente um dia ruim.

Ao ativar **🌙 Day-off**:

- o estado fica persistido no SQLite;
- o scheduler para de enviar lembretes de aulas, tarefas e rotinas;
- o Butler evita cobranças e responde de forma mínima;
- o modo continua ativo mesmo se o processo do bot for reiniciado.

Para trazê-lo de volta, basta dizer `Butler, preciso de você!` ou `Chamar, Butler!`.

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

Cada tipo permite adicionar, listar, concluir/resolver, editar, remover e configurar data, horário, observações e antecedência do lembrete. Os fluxos possuem cancelamento visível e os lembretes permitem concluir ou adiar rapidamente.

### 🗓️ Hoje

A visão diária reúne aulas, tarefas, compromissos, pendências, musculação do dia e quantidade de itens faltando em casa.

### 🏠 Cotidiano

#### Lista persistente de itens faltando

A lista não é descartável por ida ao mercado. Itens ficam salvos até serem marcados como comprados. Também é possível perguntar naturalmente `O que está faltando?`.

#### Metas gerais

Metas podem ser de água, alimentação, inglês, programação, musculação, estudos, financeiro ou outras categorias. Já é possível registrar progresso e consultar o acumulado.

#### 🧘 Rotinas e autocuidado

Rotinas recorrentes podem representar água, remédio, alimentação, sono, inglês, programação e autocuidado em geral, com horário, recorrência e registro de cumprimento.

#### 🏋️ Musculação — Protocol Mass

O Butler possui as **12 semanas do Protocol Mass** cadastradas com os treinos de segunda a sábado.

Fluxo principal:

- `🚀 Começar os trabalhos` — inicia ou retoma o protocolo e marca o treino do dia como iniciado;
- `📅 Treino de hoje` — mostra os exercícios da semana/dia atual com séries/repetições, descanso, velocidade e técnica disponíveis na planilha;
- `✅ Finalizar treino` — registra o dia como cumprido;
- `📈 Progresso Protocol Mass` — mostra o cumprimento dos seis dias da semana;
- `🔁 Substitutos` — permite escolher um exercício do treino atual e consultar somente as alternativas presentes na tabela de substituições do protocolo.

Uma semana só avança depois de **6/6 treinos concluídos**. Ao concluir a Semana 12, o programa é marcado como finalizado. O antigo cadastro manual de exercícios permanece no banco para evoluções futuras.

### Finanças

O módulo financeiro continua preparado para uma próxima frente. A direção inclui entradas/saídas, categorias, saldo mensal, comparação histórica, detecção de exageros, economia, metas e alertas de ritmo de gasto.

## Grade inicial cadastrada

| Matéria | Dia | Horário | Local |
|---|---|---|---|
| Álgebra Linear I | Terça e quinta | 10:00–11:40 | PAV III, Sala 10 |
| Física II | Segunda e quarta | 10:00–11:40 | PAV III, Sala 07 |
| Laboratório de Sistemas Digitais I | Segunda | 14:00–16:00 | PAV Eng., Sala D6 |
| Princípios de Eletrônica Analógica | Terça e quinta | 08:01–09:40 | PAV I, Sala 104 |
| Sistemas Digitais I | Segunda | 08:01–09:40 | PAV I, Sala 11 |
| Sistemas Digitais I | Quarta | 08:01–09:40 | PAV I, Sala 114 |

> Laboratório de Sistemas Digitais I usa manualmente 14:00–16:00.

## Estrutura

```text
Butler-bot/
├── assets/
├── CONTINUIDADE.md
├── README.md
├── requirements.txt
└── src/
    ├── academic_navigation.py
    ├── assistant_state.py
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
    ├── protocol_mass_data.py
    ├── protocol_mass_handlers.py
    ├── protocol_mass_navigation.py
    ├── protocol_mass_store.py
    ├── scheduler.py
    ├── sigaa_schedule.py
    └── wellbeing_handlers.py
```

## Como executar

```bash
git pull origin main
pip install -r requirements.txt
python -m src.main
```

Configure o `.env` a partir do `.env.example` com seu token do BotFather.

## Direção de desenvolvimento

A prioridade continua sendo funcionalidade antes de suíte de testes. O estado real e o próximo bloco estão em `CONTINUIDADE.md`.
