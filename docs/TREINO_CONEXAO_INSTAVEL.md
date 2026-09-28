# Treino — registro rápido com conexão instável

## Problema

O Butler roda remotamente em Telegram → Cloudflare Worker. Sem internet, o
Worker não recebe a mensagem e portanto não consegue manter uma fila local no
celular.

## Solução aplicada

Cada série pode ser enviada como uma mensagem autossuficiente:

```text
Supino reto | 40 kg | 12 reps
Supino reto | 45 kg | 10 reps
Supino reto | 50 kg | 8 reps
```

Quando essas mensagens chegarem ao Telegram/Worker, cada uma é processada
independentemente e na ordem recebida. O usuário não precisa manter o wizard
"Registrar série" aberto entre uma mensagem e outra.

O nome do exercício precisa corresponder ao treino do dia. Isso evita gravar
silenciosamente uma série em um exercício digitado errado.

## Idempotência

A migration `0016_workout_quick_log.sql` adiciona `source_message_id` às duas
fontes atuais de séries e índices únicos por usuário. Se o mesmo update do
Telegram for entregue novamente, a série não é duplicada.

## Limite arquitetural

Isto não transforma o Worker em aplicativo offline. Se o cliente Telegram não
conseguir armazenar/enviar uma mensagem sem conexão, o Butler não tem acesso a
ela. A melhoria garante processamento seguro quando a mensagem efetivamente
for entregue ao bot.
