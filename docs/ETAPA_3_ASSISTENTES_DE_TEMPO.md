# Butler — Etapa 3: Assistentes de Tempo

**Status:** ✅ concluída em 31/08/2026  
**Data-base:** 31/08/2026  
**Entregas:** 3A Assistente Geral de Tempo + 3B Modo Estudo

## 1. Resultado

A Etapa 3 passou a reunir dois domínios que compartilham o mesmo relógio persistente, mas mantêm regras próprias:

```text
Assistente Geral de Tempo
→ alertas relativos curtos
→ cronômetros
→ cancelamento

Modo Estudo
→ focus
→ break
→ long_break
→ tópico atual
→ progresso explícito
```

Infraestrutura compartilhada:

```text
D1
→ PersonalAlarm (Durable Object)
→ Telegram
→ notification_log
```

Não existe `sleep()` no Worker.

---

## 2. 3A — Assistente Geral de Tempo ✅

Documento detalhado: `ETAPA_3A_ASSISTENTE_GERAL_TEMPO.md`.

Exemplos ativos:

```text
me lembra de desligar o ovo daqui a 5 minutos
tenho que ligar para alguém daqui a 10 minutos
me lembra daqui a 1 hora de tirar a roupa do varal
cronometra 30 minutos pra mim
inicia um timer de 45 segundos
```

Prioridade semântica:

```text
timer explícito
→ timer

pedido/ação + tempo relativo curto
→ quick_alert

horário/data de agenda
→ mecanismo tradicional de tarefa/compromisso/lembrete
```

Alertas rápidos não entram em `daily_items`.

Persistência formal:

```text
0010_quick_timers.sql
quick_timers
```

Horizonte do domínio rápido:

```text
1 segundo .. 24 horas
```

Acima disso o Butler orienta usar lembrete normal.

Cancelamento:

```text
cancelar timer
cancelar timer #12
```

Múltiplos timers por usuário são permitidos e um usuário não acessa timers de outro.

Day-off não bloqueia quick timer explicitamente criado.

Merge 3A:

```text
PR #32
1165175c8868ff26a6b278473581519a8463191b
```

Regressão pós-merge da `main`: success, run #247.

---

## 3. 3B — Modo Estudo ✅

Documento detalhado: `ETAPA_3B_MODO_ESTUDO.md`.

Exemplo:

```text
modo estudo Cálculo I: limites, derivadas, integrais
```

Configuração opcional:

```text
modo estudo 50/10/20 Cálculo I: limites, derivadas
```

Padrão:

```text
25 min foco
5 min pausa
15 min pausa longa
a cada 4 blocos → pausa longa
```

Persistência formal:

```text
0011_study_mode.sql
study_sessions
study_topics
study_events
```

### Invariante permanente

**O tópico só avança quando o usuário explicitamente disser que concluiu ou pulou.**

Portanto:

```text
fim do foco
≠ conclusão

fim da pausa
≠ conclusão

restart
≠ conclusão

Day-off
≠ conclusão
```

Fim do foco apenas inicia uma pausa. Se o tópico continuar pendente, o próximo foco volta para ele.

Ações:

```text
concluí o tópico
pular tópico
não terminei
status estudo
pausar estudo
retomar estudo
cancelar estudo
histórico de estudo
```

Pausa, cancelamento e retomada nunca alteram o status do tópico por inferência.

Sessões registram fatos reais em `study_events`, inclusive qual tópico estava ligado ao bloco de foco.

O nome de uma matéria acadêmica existente pode ser reaproveitado quando a correspondência for única, mas o Modo Estudo também aceita assuntos livres e não exige FK com `subjects`.

Uma sessão explicitamente iniciada continua recebendo seus avisos durante Day-off; isso não cria progresso automático.

Merge 3B:

```text
PR #33
83fe6e17a96c8b8734ba211d43f046670b3e9985
```

Regressão da PR após correções: **330 testes passando**.  
Regressão pós-merge da `main`: **success**, run #251.

---

## 4. PersonalAlarm após a Etapa 3

O relógio persistente pessoal considera candidatos de:

```text
tarefas/compromissos/lembretes
quick timers
Modo Estudo
rotinas
resumos
```

No disparo relevante:

```text
quick timers
→ study phases
→ reliable reminders
→ routines
→ summaries
→ rearme
```

O Cron continua participando da reconciliação dos Durable Objects, evitando transformar um único alarm em ponto único de falha.

Idempotência continua baseada em `notification_log`, somada ao status do domínio quando aplicável.

---

## 5. Gate final da Etapa 3

### Assistente Geral de Tempo

- [x] alerta relativo em segundos/minutos/horas;
- [x] cronômetro explícito;
- [x] vários timers ativos;
- [x] cancelamento;
- [x] persistência D1;
- [x] idempotência;
- [x] não polui tarefas;
- [x] prioridade semântica testada;
- [x] isolamento multiusuário;
- [x] Durable Object/rearme persistente;
- [x] Day-off definido.

### Modo Estudo

- [x] foco/pausa/pausa longa;
- [x] configuração de duração;
- [x] tópicos ordenados;
- [x] conclusão explícita;
- [x] pulo explícito;
- [x] fim do timer não conclui conteúdo;
- [x] pausa/retomada/cancelamento seguros;
- [x] histórico persistido;
- [x] dois usuários isolados;
- [x] PersonalAlarm integrado;
- [x] Day-off definido;
- [x] regressão completa verde no PR;
- [x] regressão pós-merge verde na `main`.

## Próximo trabalho oficial

**Etapa 4 — Cursos e trilhas de estudo.**

A categoria `🎓 Cursos` de Ler/Ver Depois continua sendo apenas backlog simples até a implementação da Etapa 4.
