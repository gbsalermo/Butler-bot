# Continuidade do desenvolvimento

## Estado atual

- Desenvolvimento inicial concentrado na `main`.
- Stack: Python, `python-telegram-bot[job-queue]`, SQLite e `python-dotenv`.
- Execução local via polling.
- `/start` registra o `chat_id` e abre o menu geral do Butler.
- Scheduler proativo executa junto ao bot.
- Grade acadêmica base carregada automaticamente.
- Tarefas, compromissos e pendências já possuem persistência e fluxos básicos.
- Finanças já aparece como módulo planejado no menu, sem persistência financeira por enquanto.

## Menu geral

- `📚 Matérias`
- `✅ Tarefas`
- `📅 Compromissos`
- `📌 Pendências`
- `💰 Finanças`
- `🗓️ Hoje`

## Acadêmico

Gerenciamento de matérias:

- `➕ Adicionar`
- `🗑️ Remover`
- `⏸️ Trancar`
- `✏️ Editar`

Regras:

- remover = exclusão definitiva;
- trancar = manter histórico com `active = 0`;
- matérias trancadas são ignoradas pelo scheduler;
- códigos SIGAA são traduzidos em `src/sigaa_schedule.py`;
- horários especiais podem ser cadastrados manualmente.

Grade base:

- Álgebra Linear I: terça/quinta, 10:00–11:40, PAV III Sala 10.
- Física II: segunda/quarta, 10:00–11:40, PAV III Sala 07.
- Laboratório de Sistemas Digitais I: segunda, 14:00–16:00, PAV Eng. Sala D6.
- Princípios de Eletrônica Analógica: terça/quinta, 08:01–09:40, PAV I Sala 104.
- Sistemas Digitais I: segunda 08:01–09:40 Sala 11; quarta 08:01–09:40 Sala 114.

### Scheduler acadêmico

Implementado em `src/scheduler.py`.

- verifica periodicamente os horários;
- consulta apenas matérias ativas;
- envia mensagem ao `chat_id` salvo aproximadamente 10 minutos antes;
- inclui disciplina, horário e sala;
- utiliza `BUTLER_TIMEZONE`.

## Organização cotidiana

Persistência em `daily_items`, criada por `src/daily_store.py`.

Tipos:

- `tarefa`
- `compromisso`
- `pendencia`

Cada registro pode ter:

- título;
- observação;
- data opcional;
- hora opcional;
- antecedência do lembrete;
- status pendente/concluído;
- datas de criação e conclusão.

Fluxos já disponíveis:

1. adicionar;
2. listar pendentes;
3. concluir/resolver;
4. lembrar automaticamente 10 minutos antes quando houver data e hora;
5. `🗓️ Hoje` consolida os itens do dia.

## Finanças — desenho funcional

Ainda não persistir valores nesta etapa, mas preservar esta visão para a implementação.

### Movimentações

- entradas;
- gastos/saídas;
- categoria;
- data;
- descrição;
- forma de pagamento futuramente.

### Visão mensal

- total de entradas;
- total de gastos;
- saldo do mês;
- quanto foi economizado;
- divisão dos gastos por categoria.

### Inteligência de gastos

O Butler deverá comparar o comportamento atual com o histórico e produzir avisos úteis, por exemplo:

- gasto em alimentação acima da média histórica;
- ritmo de gasto do mês incompatível com o orçamento disponível;
- aumento forte em uma categoria;
- gasto recorrente esquecido;
- possibilidade de alcançar ou não uma meta no ritmo atual.

Evitar tom moralista. O papel é informar, contextualizar e ajudar na decisão.

### Metas

Exemplos:

- economizar R$ X até determinada data;
- guardar valor mensal;
- juntar para compra específica;
- acompanhar progresso percentual;
- estimar quanto falta e qual ritmo mensal necessário.

## Próximas funcionalidades prioritárias

A prioridade atual é funcionalidade, não testes automatizados.

1. melhorar o painel `🗓️ Hoje` para incluir também aulas do dia em ordem cronológica;
2. permitir editar/remover tarefas, compromissos e pendências;
3. permitir antecedência de lembrete configurável por item;
4. adicionar adiar/soneca em lembretes;
5. adicionar rotinas e autocuidado (água, remédio, alimentação, sono etc.);
6. iniciar persistência financeira real;
7. criar resumo diário e resumo semanal;
8. posteriormente integrar horários de ônibus e outras rotinas recorrentes.

## Filosofia do produto

O Butler deve evoluir para um assistente que reduz carga mental. Sempre que possível ele deve:

- lembrar antes que o usuário precise conferir;
- reunir informações espalhadas em uma única visão;
- distinguir obrigação, compromisso, pendência e rotina;
- manter histórico quando isso trouxer contexto útil;
- iniciar mensagens proativamente quando houver ação relevante;
- evitar notificações inúteis ou excessivas;
- transformar dados em orientação prática para o cotidiano.

## Regra de continuidade

Ao concluir uma etapa relevante:

1. atualizar este arquivo com o estado real;
2. atualizar o README quando funcionalidades ou execução mudarem;
3. registrar decisões que afetem etapas futuras;
4. deixar explícito o próximo passo técnico.
