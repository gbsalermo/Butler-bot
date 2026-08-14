# Continuidade do desenvolvimento

## Estado ao encerrar o dia

- Desenvolvimento concentrado na `main`.
- Stack: Python, `python-telegram-bot[job-queue]`, SQLite e `python-dotenv`.
- Execução local via polling.
- Butler já possui scheduler proativo e `chat_id` persistido.
- Prioridade atual continua sendo funcionalidade antes de suíte de testes.

## Identidade do bot no Telegram

- Nome: `Butler`
- Username atual: `@ButlerSal_BOT`

Usar esses dados como referência nas próximas etapas, documentação e futura hospedagem.

## Menu principal

O primeiro item é propositalmente:

- `🌙 Day-off`

Depois:

- `📚 Matérias`
- `✅ Tarefas`
- `📅 Compromissos`
- `📌 Pendências`
- `🏠 Cotidiano`
- `🗓️ Hoje`
- `💰 Finanças`

## Day-off

Implementado em `src/assistant_state.py` + `src/wellbeing_handlers.py`.

Objetivo: representar um dia de folga real do usuário e do Butler, inclusive quando o usuário não estiver bem ou simplesmente não quiser pensar em obrigações.

Regras:

- estado persistido em `assistant_state`;
- scheduler consulta esse estado antes de qualquer lembrete;
- em Day-off não há lembretes proativos de aulas, tarefas ou rotinas;
- respostas ficam mínimas e sem cobrança;
- o estado sobrevive a reinício do bot;
- frases de retorno:
  - `Butler, preciso de você!`
  - `Chamar, Butler!`

A sensação desejada é de chamar novamente uma pessoa que estava deixando o usuário descansar.

## Acadêmico

Gerenciamento de matérias:

- adicionar;
- remover;
- trancar;
- editar.

Regras preservadas:

- remover = exclusão definitiva;
- trancar = histórico com `active = 0`;
- matérias trancadas não geram lembretes;
- códigos SIGAA continuam traduzidos automaticamente;
- Laboratório de Sistemas Digitais I permanece manualmente na segunda, 14:00–16:00.

## Tarefas, compromissos e pendências

Persistência em `daily_items`.

A etapa antes pendente foi concluída:

- adicionar;
- listar;
- concluir/resolver;
- editar;
- remover;
- escolher antecedência do lembrete por item;
- adiar um lembrete;
- concluir diretamente pelo lembrete.

### Lembretes interativos

Quando um item chega, o Telegram recebe botões:

- `✅ Concluir`
- `⏰ +10 min`
- `⏰ +30 min`

O adiamento usa `snoozed_until` no SQLite.

## Scheduler

`src/scheduler.py` agora trata:

1. aulas ativas;
2. tarefas, compromissos e pendências;
3. itens adiados;
4. rotinas/autocuidado;
5. Day-off global.

Em Day-off, o scheduler retorna imediatamente sem notificar.

## 🏠 Cotidiano

### Lista persistente de itens faltando

Continua implementada em `grocery_items`.

Fluxos:

- adicionar item faltando;
- consultar por botão;
- perguntar naturalmente `O que está faltando?`;
- marcar comprado.

### Metas gerais

Tabela base: `goals`.

Nova tabela: `goal_progress`.

Agora é possível registrar progresso numérico das metas e consultar progresso acumulado.

Categorias centrais:

- água;
- alimentação;
- inglês;
- programação;
- musculação;
- estudos;
- financeiro;
- outras livres.

Observação para evolução futura: hoje o progresso é acumulado; depois deverá considerar corretamente a periodicidade (`dia`, `semana`, `mês`) e histórico por período.

### 🧘 Rotinas e autocuidado

Novas tabelas:

- `routines`;
- `routine_logs`.

Cada rotina pode ter:

- nome;
- categoria;
- horário;
- dias de recorrência;
- antecedência de lembrete;
- status ativo.

Exemplos:

- beber água;
- tomar remédio;
- refeição;
- horário de dormir;
- inglês;
- programação;
- outros cuidados pessoais.

Também é possível registrar que uma rotina foi cumprida no dia.

### 🏋️ Musculação

Permanece com:

- divisão por dia da semana;
- foco muscular;
- exercícios;
- carga;
- séries;
- repetições;
- exibição automática do treino em `🗓️ Hoje`.

## 🗓️ Hoje

`src/assistant_views.py` reúne:

- aulas;
- tarefas;
- compromissos;
- pendências;
- musculação do dia;
- quantidade de itens faltando em casa.

## Finanças

Continua propositalmente sem persistência real nesta etapa.

Direção preservada:

- entradas/saídas;
- categorias;
- saldo do mês;
- comparação histórica;
- detecção de aumento/exagero;
- economia;
- metas financeiras integradas às metas gerais;
- alertas de ritmo de gasto.

## Arquivos principais novos/alterados nesta etapa

- `src/assistant_state.py`
- `src/wellbeing_handlers.py`
- `src/daily_store.py`
- `src/lifestyle_handlers.py`
- `src/scheduler.py`
- `src/home_menu.py`
- `src/main.py`
- `README.md`

## Próxima retomada sugerida

Ao voltar ao desenvolvimento, não começar por testes ainda. Priorizar:

1. musculação: editar/remover exercícios e registrar execução/evolução de carga;
2. metas: progresso por período real (dia/semana/mês), streak e histórico;
3. rotinas: editar/remover, mais de um horário por rotina e confirmação direto no lembrete;
4. resumo diário automático e resumo semanal;
5. persistência financeira real;
6. inteligência de gastos e comparação histórica;
7. integração futura com ônibus e outras rotinas recorrentes;
8. só depois consolidar testes automatizados e preparar hospedagem 24/7.

## Filosofia do produto

O Butler deve parecer um assistente presente, não um formulário com comandos.

Princípios:

- reduzir carga mental;
- lembrar antes que o usuário precise conferir;
- guardar pequenas informações persistentes;
- conversar de forma natural;
- distinguir obrigação, compromisso, pendência, meta, rotina e descanso;
- respeitar Day-off sem culpa ou cobrança;
- permitir que o usuário literalmente “chame o Butler” quando quiser ajuda novamente;
- evitar notificações inúteis;
- transformar histórico em orientação prática.

## Regra de continuidade

Ao concluir nova etapa:

1. atualizar este arquivo com o estado real;
2. atualizar o README quando funcionalidades ou execução mudarem;
3. registrar decisões que afetem etapas futuras;
4. deixar explícito o próximo passo técnico.
