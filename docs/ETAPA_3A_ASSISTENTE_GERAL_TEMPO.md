# Butler — Etapa 3A: Assistente Geral de Tempo

**Data-base:** 31/08/2026  
**Status:** implementação pronta para merge  
**Etapa:** 3 — Auxiliares de Tempo / Modo Estudo

## Objetivo

Executar pedidos temporais curtos sem transformar tudo em tarefa ou compromisso.

Exemplos:

```text
me lembra de desligar o ovo daqui a 5 minutos
tenho que ligar para alguém daqui a 10 minutos
me lembra daqui a 1 hora de tirar a roupa do varal
cronometra 30 minutos pra mim
cronometra o tempo de 45 segundos
```

## Arquitetura

```text
mensagem
→ temporal_language.py (classificação pura)
→ quick_time.py (domínio)
→ quick_timers (D1)
→ PersonalAlarm
→ Telegram
```

`daily_items` não participa deste fluxo.

Migration formal:

```text
0010_quick_timers.sql
```

O módulo mantém um `ensure_schema()` defensivo somente quando o domínio é realmente usado, para tolerar deploy do código antes da migration. A migration continua sendo a fonte formal.

## Prioridade semântica

No Core:

```text
clima/navegação
→ Assistente Geral de Tempo
→ compound router
→ lembrete/tarefa/compromisso tradicionais
```

Assim:

```text
tenho que ligar daqui a 10 minutos
→ quick_alert
```

não:

```text
→ tarefa permanente
```

Negação continua protegida:

```text
não me lembra daqui a 5 minutos de desligar o forno
→ não cria timer
```

## Persistência

`quick_timers` mantém:

```text
user_id
kind: timer | quick_alert
label
delay_seconds
fire_at
status: active | fired | cancelled
created_at
fired_at
cancelled_at
```

Horizonte aceito para este domínio:

```text
1 segundo .. 24 horas
```

Acima disso o Butler orienta usar lembrete normal.

## Cancelamento

Com um timer ativo:

```text
cancelar timer
→ cancela o único ativo
```

Com vários:

```text
cancelar timer
→ lista #IDs

cancelar timer #12
→ cancela somente #12 do usuário atual
```

Um usuário não consegue cancelar timer de outro usuário.

## Entrega e redundância

O `PersonalAlarm` considera o próximo `quick_timer` junto dos demais eventos pessoais.

No alarm:

```text
quick timers vencidos
→ reliable reminders
→ routines
→ summaries
→ rearme
```

A reconciliação do Cron continua sendo fallback: se um alarm persistente não disparar, o próximo sync encontra o timer vencido, rearma para execução imediata e mantém o Cron fora do papel de ponto único de falha.

Idempotência:

```text
quick_timers.status
+
notification_log: quick_timer:<id>
```

## Day-off

Timer rápido não é bloqueado por Day-off.

Motivo: é uma instrução explícita e pontual; um cronômetro de cozinha ou alerta curto não pode ser silenciado porque tarefas/rotinas estão de folga.

## Regressão

`cloudflare/tests/test_stage3_quick_time.py` cobre:

- quatro formas principais de alerta relativo;
- cronômetro explícito;
- falsos positivos;
- negação;
- limite de 24 horas;
- precedência no Core;
- persistência fora de `daily_items`;
- dois usuários;
- cancelamento isolado;
- disparo único/idempotente;
- próximo timer do PersonalAlarm;
- migration formal;
- integração do PersonalAlarm.

Primeiro gate da PR #32:

```text
313 testes passando
```

## Gate 3A

- [x] alerta relativo em segundos/minutos/horas;
- [x] cronômetro explícito;
- [x] prioridade sobre tarefa/lembrete tradicional quando o tempo relativo curto é claro;
- [x] não polui `daily_items`;
- [x] persistência D1;
- [x] múltiplos timers por usuário;
- [x] cancelamento;
- [x] isolamento multiusuário;
- [x] idempotência;
- [x] Durable Object persistente;
- [x] fallback via reconciliação do Cron;
- [x] Day-off definido;
- [x] regressão da PR verde;
- [ ] merge da PR;
- [ ] regressão pós-merge da main.

## Próximo passo

Após os dois últimos gates: **Etapa 3B — Modo Estudo**, reutilizando `PersonalAlarm` como infraestrutura temporal, mas mantendo regras de progresso em domínio separado.
