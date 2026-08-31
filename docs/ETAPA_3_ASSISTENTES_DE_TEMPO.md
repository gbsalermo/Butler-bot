# Butler — Etapa 3: Assistentes de Tempo

**Status:** planejamento oficial complementar ao roadmap mestre  
**Data-base:** 30/08/2026  
**Relacionados:** Etapa 1 (linguagem), Etapa 2 (acadêmico), Etapa 3 (Modo Estudo)

## 1. Decisão

A Etapa 3 deixa de ser pensada apenas como um Pomodoro acadêmico e passa a reunir dois usos do mesmo núcleo temporal persistente:

```text
Assistente Geral de Tempo
→ alertas relativos curtos
→ cronômetros
→ contagens regressivas

Auxiliar de Estudos / Modo Estudo
→ ciclos de foco
→ pausas
→ check-ins
→ tópico atual
```

Eles compartilham infraestrutura de tempo, mas **não compartilham regras de domínio**.

O fim de um cronômetro apenas dispara um alerta. O fim de um bloco de estudo também **não conclui tópico**; a conclusão continua explícita.

---

## 2. Assistente Geral de Tempo

### Objetivo

Permitir pedidos rápidos, normalmente no mesmo dia e com horizonte curto, sem obrigar o usuário a criar uma tarefa ou compromisso tradicional.

Exemplos principais:

```text
me lembra de desligar o ovo daqui a 5 minutos
tenho que ligar para alguém daqui a 10 minutos
me lembra daqui a 1 hora de tirar a roupa do varal
cronometra 30 minutos pra mim
inicia um timer de 45 segundos
me avisa em 20 minutos de olhar o forno
```

O comportamento esperado é mais próximo de relógio/cronômetro do que de agenda.

### Diferença para tarefa e compromisso

```text
Tarefa/compromisso
→ planejamento de agenda
→ possui data/horário operacional
→ aparece em listas/resumos quando aplicável

Alerta rápido/cronômetro
→ duração relativa a partir de agora
→ normalmente minutos ou poucas horas
→ não deve poluir a lista de tarefas
→ expira após disparar
```

A frase pode usar linguagem de tarefa (`tenho que`, `preciso`), mas um prazo explicitamente relativo e curto pode mudar o domínio final.

Exemplo:

```text
tenho que ligar para João daqui a 10 minutos
```

Destino desejado:

```text
quick_alert
alvo: ligar para João
delay: 600 segundos
```

não:

```text
tarefa permanente na agenda
```

---

## 3. Formas de linguagem previstas

### Alertas relativos

```text
daqui a 5 minutos
em 10 minutos
daqui a 1 hora
em 2 horas
```

Comandos:

```text
me lembra...
me lembre...
me avisa...
me avise...
não deixa eu esquecer...
me dá um toque...
tenho que ... daqui a X
preciso ... daqui a X
devo ... em X
```

### Cronômetros explícitos

```text
cronometra 30 minutos
cronometre 5 minutos
inicia um timer de 10 minutos
começa um cronômetro de 1 hora
faz um cronômetro de 15 minutos
```

A Etapa 1 já deve reconhecer essas construções estruturalmente, mas **não precisa executar o timer antes da Etapa 3**.

---

## 4. Prioridade semântica futura

Quando a Etapa 3 estiver ativa:

```text
cronômetro explícito
→ timer

pedido de lembrete + tempo relativo
→ quick_alert

linguagem de tarefa + tempo relativo curto
→ quick_alert, quando a intenção temporal estiver clara

horário/data de agenda
→ tarefa/compromisso/lembrete tradicional
```

Casos ambíguos devem confirmar, não adivinhar.

Exemplo:

```text
me lembra de falar com João em 3 horas
```

Pode ser alerta rápido.

Já:

```text
me lembra de falar com João amanhã às 15h
```

continua no mecanismo tradicional de lembrete com data/hora.

---

## 5. Modelo conceitual

```text
QuickTimer
- user_id
- kind: timer | quick_alert
- label
- delay_seconds
- fire_at
- status: active | fired | cancelled
- created_at
- fired_at
- cancelled_at
```

O schema real pode ser diferente, mas precisa permitir:

- persistência;
- cancelamento;
- idempotência;
- isolamento por usuário;
- recuperação após restart;
- múltiplos timers simultâneos.

---

## 6. Infraestrutura

Não usar `sleep()` em memória.

Reutilizar a infraestrutura de Durable Objects/alarmes persistentes já adotada pelo Butler sempre que isso mantiver uma única autoridade temporal confiável.

Requisitos:

- alerta sobrevive a restart do Worker;
- não dispara duas vezes;
- pode ser cancelado;
- usuário A não interfere no usuário B;
- cron principal não é ponto único de falha;
- timer pode ser criado a qualquer momento pelo webhook e já sair armado.

---

## 7. UX futura

Exemplo:

```text
Usuário: me lembra de desligar o ovo daqui a 5 minutos

Butler:
⏱️ Fechado. Em 5 minutos eu te aviso para desligar o ovo.

[❌ Cancelar timer]
```

Disparo:

```text
⏰ 5 minutos.
Desliga o ovo.
```

Cronômetro puro:

```text
Usuário: cronometra 30 minutos pra mim

Butler:
⏱️ Cronômetro iniciado: 30 minutos.

[⏹️ Parar]
```

Final:

```text
⏰ Tempo! 30 minutos encerrados.
```

---

## 8. Integração com Modo Estudo

O Modo Estudo consome o mesmo conceito de alarme persistente, mas cria ciclos estruturados:

```text
focus
break
long_break
```

O Assistente Geral de Tempo não conhece tópicos, progresso ou conclusão acadêmica.

Isso evita misturar:

```text
cronômetro da cozinha
≠
bloco de estudo de Cálculo
```

mesmo que ambos usem um alarme de 25 minutos por baixo.

---

## 9. Gate complementar da Etapa 3

Além do gate já definido para Modo Estudo:

- [ ] criar alerta relativo em minutos/horas;
- [ ] criar cronômetro explícito;
- [ ] vários timers ativos por usuário quando necessário;
- [ ] cancelar timer/alerta;
- [ ] disparo persistente e idempotente;
- [ ] não transformar timer rápido em tarefa permanente;
- [ ] tempo relativo curto possui prioridade semântica testada;
- [ ] restart não perde contagem;
- [ ] dois usuários não compartilham timers;
- [ ] Modo Estudo e timer geral compartilham infraestrutura sem compartilhar regras de progresso.

---

## 10. Preparação já iniciada na Etapa 1

A Etapa 1 passa a possuir corpus específico de tempo relativo e cronômetros.

Arquivos previstos/ativos:

```text
cloudflare/src/temporal_language.py
cloudflare/tests/fixtures/stage1_relative_time_corpus.json
cloudflare/tests/test_stage1_relative_time_corpus.py
```

Nesta fase a camada apenas reconhece intenção e duração. A criação real do timer permanece para a Etapa 3.
