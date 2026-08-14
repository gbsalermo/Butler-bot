# Continuidade do desenvolvimento

## Estado atual

- Desenvolvimento concentrado na `main`.
- Stack: Python, `python-telegram-bot[job-queue]`, SQLite e `python-dotenv`.
- Execução local via polling.
- `/start` registra o `chat_id` e abre o menu geral do Butler.
- Scheduler proativo executa junto ao bot.
- Grade acadêmica base carregada automaticamente.
- Tarefas, compromissos e pendências possuem persistência e lembretes.
- Cotidiano agora possui lista persistente de itens faltando, metas gerais e musculação.
- Finanças continua visível como módulo planejado, ainda sem persistência de valores.

## Menu geral

- `📚 Matérias`
- `✅ Tarefas`
- `📅 Compromissos`
- `📌 Pendências`
- `🏠 Cotidiano`
- `🗓️ Hoje`
- `💰 Finanças`

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

## Scheduler

Implementado em `src/scheduler.py`.

- consulta apenas matérias ativas;
- avisa aproximadamente 10 minutos antes das aulas;
- também considera tarefas/compromissos/pendências com data e hora;
- utiliza o `chat_id` persistido;
- utiliza `BUTLER_TIMEZONE`.

## Tarefas, compromissos e pendências

Persistência em `daily_items`, criada por `src/daily_store.py`.

Cada registro pode ter título, observação, data, hora, antecedência de lembrete e status.

Fluxos atuais:

1. adicionar;
2. listar pendentes;
3. concluir/resolver;
4. lembrar automaticamente antes quando houver data e hora.

## 🗓️ Hoje

A visão diária foi ampliada em `src/assistant_views.py`.

Atualmente reúne:

- aulas do dia em ordem de horário;
- tarefas;
- compromissos;
- pendências;
- treino de musculação correspondente ao dia da semana;
- quantidade de itens que estão faltando em casa.

## 🏠 Cotidiano

Implementado principalmente em `src/home_store.py` e `src/home_handlers.py`.

### Lista persistente de itens faltando

Tabela: `grocery_items`.

Objetivo: não criar uma lista descartável de compras. O usuário vai adicionando itens conforme percebe que estão acabando/faltando, e a lista continua salva até marcar cada item como comprado.

Fluxos:

- `➕ Item faltando`;
- `🛒 O que está faltando?`;
- texto natural `O que está faltando?`;
- `✅ Marcar comprado`.

Cada item pode ter quantidade/tamanho e observação.

### Metas gerais

Tabela: `goals`.

As metas NÃO são somente financeiras. Categorias centrais para o projeto:

- água;
- alimentação;
- inglês;
- programação;
- musculação;
- estudos;
- financeiro;
- outras categorias livres.

Cada meta pode registrar nome, categoria, valor-alvo, unidade e periodicidade.

Exemplos futuros:

- 2 litros de água por dia;
- 5 horas de inglês por semana;
- 7 horas de programação por semana;
- 4 treinos por semana;
- economizar R$ 300 por mês.

Nesta etapa a meta é cadastrada/listada; acompanhamento de progresso vem depois.

### Musculação

Tabelas:

- `workout_days`;
- `workout_exercises`.

Modelo:

- cada dia da semana possui um foco, como `segunda — peito`, `terça — costas e bíceps`, `quarta — perna`;
- cada dia pode ter vários exercícios;
- cada exercício guarda nome, carga, séries e repetições;
- `📋 Ver rotina` mostra a divisão semanal completa;
- a visão `🗓️ Hoje` mostra automaticamente o treino do dia.

## Finanças — visão preservada

Ainda não persistir valores nesta etapa.

Planejado:

- entradas e saídas;
- categorias;
- saldo mensal;
- economia;
- comparação histórica;
- detecção de aumento/exagero de gastos;
- metas financeiras integradas ao sistema geral de metas;
- avisos de ritmo de gasto;
- histórico mensal.

O Butler deve informar e contextualizar sem tom moralista.

## Próximas funcionalidades prioritárias

Continuar priorizando funcionalidade antes de testes automatizados.

1. editar/remover tarefas, compromissos e pendências;
2. antecedência de lembrete configurável por item;
3. botões de `Concluído`, `Adiar` e `Lembrar depois` nas notificações;
4. criar rotinas recorrentes de autocuidado: água, alimentação, remédios, sono e outras;
5. transformar metas em acompanhamento real de progresso e histórico;
6. musculação: editar/remover exercícios, registrar execução do treino e evolução de carga;
7. lista de faltas: categorias e histórico opcional de itens recorrentes;
8. iniciar persistência financeira real e integrar finanças às metas;
9. criar resumo diário automático e resumo semanal;
10. posteriormente integrar ônibus e outras rotinas recorrentes.

## Filosofia do produto

O Butler deve reduzir carga mental. Sempre que possível ele deve:

- lembrar antes que o usuário precise conferir;
- guardar pequenas informações persistentes do cotidiano;
- reunir informações espalhadas em uma única visão;
- distinguir obrigação, compromisso, pendência, meta e rotina;
- manter histórico quando isso trouxer contexto útil;
- iniciar mensagens proativamente quando houver ação relevante;
- evitar notificações inúteis ou excessivas;
- transformar dados em orientação prática.

## Regra de continuidade

Ao concluir uma etapa relevante:

1. atualizar este arquivo com o estado real;
2. atualizar o README quando funcionalidades ou execução mudarem;
3. registrar decisões que afetem etapas futuras;
4. deixar explícito o próximo passo técnico.
