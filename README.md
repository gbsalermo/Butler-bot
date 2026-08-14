<p align="center">
  <img src="assets/butler.png" alt="Butler - mascote" width="420">
</p>

# Butler Bot

Assistente pessoal via Telegram para organização acadêmica, tarefas, compromissos, casa, metas, musculação, autocuidado e finanças. A proposta é reduzir menus e formulários: o Butler pode ser usado por botões, mas também entende várias frases naturais do cotidiano.

## Execução local

### Butler pessoal

```bash
python -m src.main
```

Mantém grade pessoal, correções manuais, Protocol Mass de 12 semanas e dados em `data/butler.db`.

### Butler genérico / multiusuário

```bash
python -m src.main_generic
```

A versão genérica nasce limpa, pergunta como o usuário quer ser chamado e isola dados por `chat_id`. No rolling local cada chat usa seu próprio SQLite; na futura hospedagem Cloudflare essa regra será preservada com persistência migrada para D1.

## Menu principal

- 🌙 Day-off
- ➕ Adicionar
- 🗓️ Hoje
- 🛒 Item faltando
- 📚 Matérias
- 🏠 Cotidiano
- 🏋️ Musculação

`➕ Adicionar` abre tarefa/compromisso. `🛒 Item faltando` abre adicionar/listar. Tarefas vencidas e não concluídas viram pendências automaticamente.

## Linguagem natural

A camada natural é determinística e reaproveita as mesmas regras dos fluxos por botão. Quando a intenção é clara, age direto; quando existem vários alvos plausíveis, pede confirmação. Não depende de API/LLM externo.

Exemplos:

```text
Butler, amanhã tenho dentista às 15h
sexta tenho reunião 10h
dentista amanhã 15h

me lembra de comprar café
amanhã preciso entregar o relatório às 18h
já fiz o relatório

o que tenho amanhã?
o que tenho daqui a 3 dias?
quais tarefas estão atrasadas?

falta sal, açúcar e café
bota café na lista de mercado
o que falta em casa?
comprei o café

hoje não vou treinar porque estou cansado
não vai dar pra treinar hoje

vou me atrasar para o dentista
estou atrasado para a reunião

gastei 35 com lanche
paguei 20 de uber
recebi 540 de bolsa
quanto gastei esse mês?
quanto sobrou?
```

Se faltar informação, o Butler pede só o necessário. Ex.: `tenho dentista amanhã` → pergunta apenas o horário.

Datas/horas passadas são rejeitadas. Avisos de atraso não alteram automaticamente o horário do compromisso; servem para contexto e personalidade. Reincidências ficam registradas para que o sarcasmo seja baseado em comportamento real.

## Agenda e histórico

`🗓️ Hoje` reúne aulas, tarefas, compromissos, pendências, academia quando aplicável e itens faltando. Também permite:

- amanhã;
- outra data;
- próximos 7 dias;
- histórico diário;
- histórico de tarefas.

O histórico de tarefas separa pendentes, concluídas e canceladas. Remover agora arquiva como cancelado em vez de apagar fisicamente.

## Acadêmico

- grade persistente;
- adicionar/remover/trancar/editar matérias;
- tradução de códigos SIGAA;
- importação por PDF textual ou `.txt`;
- lembretes automáticos de aula.

Não há OCR/Tesseract. Imagens devem ser convertidas antes para PDF com texto pesquisável ou transcritas para `.txt`.

### Horários SIGAA

- `M23` → `08:00–10:00`
- `M45` → `10:00–12:00`
- `T23` → `14:00–16:00`
- `T2345` → `14:00–18:00`
- `N12` → `18:00–20:00`

Correções manuais têm prioridade.

## Resumos e comportamento

O Butler envia resumo matinal (07:30 por padrão) com aulas, locais, tarefas, compromissos, mercado, academia quando aplicável e o que ficou pendente do dia anterior.

Não há fechamento automático noturno. O fechamento semanal continua no domingo às 20:00 por padrão.

A personalidade usa dados reais: adiamentos, tarefas atrasadas, streaks, faltas, evolução de carga e avisos de atraso. Day-off reduz cobranças e sarcasmo.

## Metas e streaks

`🎯 Metas → 🔥 Sequências` acompanha de forma simples:

- 🇬🇧 Inglês
- 💻 Programação
- 💧 Água
- 🥗 Alimentação
- 🏋️ Musculação

Mostra sequência atual, recorde, total de dias e últimos 7 dias. No Butler pessoal, musculação usa treinos realmente concluídos do protocolo.

## Finanças simples

Escopo atual:

- entrada/saída;
- categorias;
- relatório mensal;
- comparação simples;
- alertas de excesso predefinidos.

O Butler deixa claro que só consegue gerar um retrato confiável se o usuário alimentar os movimentos. Não há cartões, parcelas, investimentos ou orçamento complexo nesta fase.

## Musculação — Butler pessoal

O Protocol Mass possui 12 semanas, treino do dia, faltas com motivo, substituições, registro série por série, carga/repetições e histórico. Externamente o Butler fala apenas “treino na academia”. O protocolo só entra em resumos/faltas depois de `🚀 Começar os trabalhos`.

## Grade pessoal inicial

| Matéria | Dia | Horário | Local |
|---|---|---|---|
| Álgebra Linear I | Terça e quinta | 10:00–12:00 | PAV III, Sala 10 |
| Física II | Segunda e quarta | 10:00–12:00 | PAV III, Sala 07 |
| Laboratório de Sistemas Digitais I | Segunda | 14:00–16:00 | PAV Eng., Sala D6 |
| Princípios de Eletrônica Analógica | Terça e quinta | 08:00–10:00 | PAV I, Sala 104 |
| Sistemas Digitais I | Segunda | 08:00–10:00 | PAV I, Sala 11 |
| Sistemas Digitais I | Quarta | 08:00–10:00 | PAV I, Sala 114 |

## Rodar

```bash
git pull origin main
pip install -r requirements.txt
python -m src.main
```

Versão genérica:

```bash
copy .env.generic.example .env.generic
# configure TELEGRAM_BOT_TOKEN
python -m src.main_generic
```

No Linux/macOS, use `cp` no lugar de `copy`.

## Próxima etapa

Preparar produção no Cloudflare: webhook do Telegram, migração SQLite → D1, substituição do polling/JobQueue por mecanismos compatíveis com a plataforma e smoke tests com múltiplos `chat_id`.
