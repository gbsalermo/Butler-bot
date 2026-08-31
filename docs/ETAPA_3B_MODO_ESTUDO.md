# Butler — Etapa 3B: Modo Estudo

**Data-base:** 31/08/2026  
**Status:** implementação pronta para merge  
**Etapa:** 3 — Auxiliares de Tempo / Modo Estudo

## Objetivo

Criar sessões de estudo persistentes com foco, pausa e tópicos sem transformar tempo decorrido em progresso fictício.

Invariante principal:

> **O tópico só avança quando o usuário explicitamente disser que concluiu ou pulou.**

Fim do foco, fim da pausa, restart, Day-off ou passagem do tempo nunca concluem conteúdo.

## Uso

Exemplo direto:

```text
modo estudo Cálculo I: limites, derivadas, integrais
```

Configuração customizada:

```text
modo estudo 50/10/20 Cálculo I: limites, derivadas
```

interpreta:

```text
50 min foco
10 min pausa
20 min pausa longa
pausa longa a cada 4 blocos de foco
```

Também aceita:

```text
quero estudar Cálculo agora: limites, derivadas
```

Mas não sequestra planejamento futuro:

```text
quero estudar Cálculo amanhã
→ continua fora do Modo Estudo
```

Quando matéria/tópicos não são fornecidos, usa setup guiado. `sessão livre` cria um único tópico livre.

## Persistência

Migration formal:

```text
0011_study_mode.sql
```

Estruturas:

```text
study_sessions
study_topics
study_events
```

`study_sessions` guarda configuração, fase e próximo instante.

`study_topics` guarda ordem e estado real:

```text
pending
completed
skipped
```

`study_events` registra fatos da sessão, como início/fim de foco, pausa, retomada, conclusão/pulo e cancelamento.

## Ciclo temporal

```text
focus
→ timer termina
→ break / long_break
→ timer termina
→ focus no tópico que ainda estiver pendente
```

Mensagem de fim de foco deixa a regra explícita:

```text
O relógio acabou; o tópico não.
Não marquei nada como concluído.
```

Se o usuário concluir o tópico antes do fim do foco, o foco é encerrado naquele tópico real e uma pausa começa antes do próximo.

## Ações explícitas

```text
concluí o tópico
→ completed

pular tópico
→ skipped

não terminei
→ continua pending

pausar estudo
→ sessão pausada; tópico intacto

retomar estudo
→ novo foco no mesmo tópico pendente

cancelar estudo
→ encerra sessão sem concluir nada

status estudo
→ mostra fase, tópico, progresso e tempo restante

histórico de estudo
→ últimas sessões com progresso persistido
```

## Matérias acadêmicas

Se o nome enviado corresponder de forma única a uma matéria ativa existente, o Butler reutiliza a grafia oficial do nome.

O Modo Estudo não cria FK obrigatória com `subjects`; também pode estudar assunto livre.

## PersonalAlarm e Day-off

O próximo fim de foco/pausa entra no mesmo `PersonalAlarm` usado pelos demais eventos temporais.

Ordem relevante:

```text
quick timers
→ study phases
→ reminders
→ routines
→ summaries
```

Uma sessão de estudo já iniciada continua durante Day-off porque foi explicitamente iniciada pelo usuário. Day-off não cria progresso; apenas não silencia o relógio ativo.

Idempotência das transições temporais usa:

```text
notification_log
key = study:<session_id>:<phase>:<phase_ends_at>
```

## Regressão

`cloudflare/tests/test_stage3_study_mode.py` cobre:

- proteção contra `quero estudar amanhã`;
- início natural e `modo estudo`;
- ciclo padrão e customizado;
- tópicos com vírgula + `e`;
- `comeca` sem acento;
- limites de configuração;
- matéria acadêmica canônica;
- persistência da sessão/tópicos;
- fim do foco sem concluir tópico;
- fim da pausa voltando ao mesmo tópico;
- conclusão explícita;
- pulo explícito;
- conclusão da sessão somente após tópicos resolvidos;
- pausa/retomada/cancelamento sem progresso falso;
- dois usuários isolados;
- próximo evento no PersonalAlarm;
- idempotência de disparo;
- histórico persistido;
- associação correta do fim de foco ao tópico realmente estudado;
- ordem Core antes do compound router;
- migration 0011 formal.

Gate corrigido da PR #33:

```text
330 testes passando
```

## Gate 3B

- [x] foco/pausa persistentes;
- [x] pausa longa;
- [x] duração configurável;
- [x] tópicos ordenados;
- [x] tópico atual persistente;
- [x] fim de timer não conclui tópico;
- [x] conclusão explícita;
- [x] pulo explícito;
- [x] `não terminei` preserva pendência;
- [x] pausa/retomada/cancelamento seguros;
- [x] histórico baseado em fatos persistidos;
- [x] isolamento multiusuário;
- [x] integração com PersonalAlarm;
- [x] Day-off definido;
- [x] regressão completa da PR verde;
- [ ] merge da PR #33;
- [ ] regressão pós-merge da main.

## Fechamento da Etapa 3

Após os dois últimos gates, 3A + 3B encerram a Etapa 3. O próximo roadmap oficial passa a ser **Etapa 4 — Cursos e trilhas de estudo**.
