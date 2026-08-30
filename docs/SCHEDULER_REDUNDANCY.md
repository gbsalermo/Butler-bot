# Butler — Redundância do Scheduler

**Data-base:** 30/08/2026  
**Incidente de referência:** ausência total de notificações em 30/08, com último heartbeat do cron em 29/08 às 21:32.

## 1. Problema identificado

O Butler utilizava o Cloudflare Cron Trigger (`* * * * *`) como relógio global primário. Havia Durable Object Alarms para presença e alguns eventos pessoais, mas o `PersonalAlarm` ainda dependia do próprio cron para ser sincronizado e cobria apenas parte dos eventos.

Isso deixava um ponto único de falha: se o Cron Trigger parasse, tarefas, compromissos, rotinas e resumos poderiam deixar de ser processados.

## 2. Arquitetura após a correção

```text
Linha primária
Cloudflare Cron Trigger (a cada minuto)
→ worker.py
→ dispatch_scheduled()
→ attendance
→ daily_items
→ routines
→ summaries
→ legado

Linha persistente de contingência
Webhook/cron
→ sync_personal_alarms()
→ PersonalAlarm por usuário
→ próximo evento persistido no Durable Object
→ alarm()
→ dispatchers autoritativos
```

O `PersonalAlarm` agora considera:

- tarefa com horário;
- compromisso, com aviso 5 minutos antes;
- lembrete pessoal simples;
- checkpoint de rotina;
- resumo da manhã;
- fechamento semanal.

`AttendanceAlarm` continua separado para eventos de presença/aula.

## 3. Rearme após webhook

`worker.Default.fetch()` rearma os Durable Objects depois de qualquer POST processado. Isso é deliberado: quando o usuário cria ou edita uma tarefa, compromisso, rotina, lembrete ou matéria, o novo estado já está salvo no D1 antes de o alarm persistente ser recalculado.

Assim, um evento novo não precisa esperar o próximo Cron Trigger para ganhar proteção persistente.

## 4. Alarm sempre vivo

Mesmo quando o usuário não tem tarefas, compromissos ou rotinas, o `PersonalAlarm` mantém pelo menos o próximo resumo matinal como evento futuro.

Isso evita que o Durable Object fique sem alarm e dependa do cron para acordar novamente.

No domingo, o fechamento semanal das 20:00 pode ser o próximo evento antes do resumo de segunda-feira.

## 5. Idempotência

A redundância não deve gerar mensagens duplicadas.

Os dispatchers finais continuam sendo autoridades e usam `notification_log` para decidir se um evento já foi entregue. Cron e Durable Object podem acordar próximos um do outro sem transformar isso em dois avisos válidos.

## 6. Janelas úteis

A camada persistente respeita as mesmas ideias dos schedulers autoritativos:

- tarefa: pode recuperar atraso no mesmo dia enquanto continuar pendente;
- compromisso: não recuperar além da janela útil;
- lembrete simples: tolerância curta;
- rotina: não mandar checkpoint velho como se ainda fosse atual;
- resumo matinal: janela de recuperação da manhã;
- resumo semanal: janela própria no domingo.

Tempo perdido não autoriza spam tardio.

## 7. Day-off

Antes de processar um alarm persistente, estados antigos de Day-off são expirados.

Day-off ativo do dia continua bloqueando eventos compatíveis. Lembretes pessoais explícitos mantêm a política própria já existente.

## 8. Diagnóstico

Comando:

```text
status alertas
```

Sinais principais:

- itens `vencido sem notificação` indicam que o evento não possui chave de entrega em `notification_log`;
- o heartbeat de presença é uma evidência de passagem do Cron Trigger;
- heartbeat muito antigo com vários itens vencidos aponta falha do cron/trigger, não de uma frase individual.

O incidente de 30/08 apresentou exatamente esse padrão: todos os itens vencidos e heartbeat congelado em 29/08 às 21:32.

## 9. Testes de regressão

`cloudflare/tests/test_persistent_scheduler_fallback.py` cobre:

- compromisso armado em T-5;
- tarefa recuperável no mesmo dia;
- lembrete simples velho não recuperado;
- alarm persistente mesmo sem outros itens;
- prioridade do fechamento semanal no domingo;
- Day-off sem matar o alarm do dia seguinte;
- rearme de alarms depois de POST/webhook.

## 10. Limite operacional

Esta correção reduz o Cron Trigger de ponto único de falha para primeira linha de agendamento. Ainda é importante investigar no painel/observabilidade da Cloudflare por que o Cron Trigger específico parou em 29/08 às 21:32.

CI verde e `main` atualizada não provam, sozinhos, que a versão foi publicada na Cloudflare. A validação de produção deve confirmar o deploy e observar novo heartbeat/alarm real.
