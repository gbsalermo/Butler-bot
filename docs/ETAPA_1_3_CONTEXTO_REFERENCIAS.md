# Butler — Etapa 1.3: Referências + Contexto Curto

**Data-base:** 30/08/2026  
**Status:** concluída  
**Anterior:** Etapa 1.2 concluída

## Objetivo

Fazer referências curtas funcionarem em conversas reais sem permitir que contexto velho ou de outro usuário altere a entidade errada.

Casos-alvo:

```text
cria uma tarefa terminar o relatório amanhã
muda ela pra sexta

mostra minhas tarefas
conclui a segunda

tenho dentista amanhã às 15h
cancela esse

essa não, a outra

a anterior pode deixar
```

## Contrato de contexto

O contexto operacional possui uma autoridade explícita em:

```text
cloudflare/src/short_context.py
```

Ele usa `natural_events.created_at`, já existente no schema, portanto a Etapa 1.3 não exige migration própria.

### Janela inicial

```text
30 minutos
```

Após essa janela, pronomes e follow-ups curtos deixam de poder resolver silenciosamente o item anterior.

Exemplo:

```text
20:00 → Butler mostra tarefa X
20:05 → "adia"
→ pode usar X

22:00 → "adia"
→ não pode ressuscitar X apenas pelo contexto antigo
```

A duração é uma política conservadora inicial e pode ser calibrada pelo corpus/uso real.

## Isolamento

Toda busca de contexto continua condicionada a:

```text
user_id
```

O alvo final também é buscado com `id + user_id`.

Contexto de um usuário nunca é candidato para outro. A regressão inclui dois usuários simultâneos com contextos e listas diferentes.

## Barreira de assunto

Contexto só pode ser consumido quando há:

- referência explícita (`essa`, `ela`, `a segunda` etc.); ou
- follow-up curto permitido (`adia`, `depois`, `mais tarde` etc.).

Nova criação explícita é barreira:

```text
cria uma tarefa...
tenho dentista...
me lembra...
cria uma rotina...
```

Essas frases não podem ser interpretadas como continuação do item anterior.

Perguntas de outro domínio também não abrem contexto apenas por conter `hoje`:

```text
qual meu treino hoje?
```

## Lista posicional

Ao renderizar `✅ Tarefas`, o Butler grava os IDs na mesma ordem exibida.

Assim:

```text
1. Relatório
2. Mercado
3. README

"conclui a segunda"
→ Mercado
```

A resolução usa a lista que o usuário viu, e não uma consulta nova cuja ordem possa ter mudado.

## Referências cobertas

```text
essa / esse / isso
ela / ele
a primeira / o primeiro
a segunda / o segundo
a terceira / o terceiro
a outra / o outro
a anterior / o anterior
a última / o último
```

`a terceira/o terceiro` também pertence ao detector comum de `language_primitives`, portanto não depende de um caminho específico do dispatcher.

`a outra` só é executada sem pergunta quando existir exatamente uma alternativa inequívoca.

## Qualificador temporal

Referências como:

```text
cancela aquela de amanhã
```

usam `amanhã` para validar o alvo atual.

Já:

```text
muda ela pra sexta
```

trata `sexta` como destino da alteração. A data não pode ser usada para rejeitar a referência antes do reschedule.

## Contexto legado unificado

Durante a primeira fatia ainda existiam chamadores que usavam:

```text
conversation_layer._remember
conversation_layer._context
```

A segunda entrega elimina a divergência sem exigir uma migração big-bang dos chamadores:

```text
short_context.install()
→ conversation_layer._remember = short_context.legacy_remember
→ conversation_layer._context = short_context.legacy_context
```

Assim todos esses caminhos passam a herdar:

- expiração de 30 minutos;
- `context_version = 2`;
- histórico de alvos recentes;
- isolamento por usuário;
- mesma política de referência.

## Sequências reais protegidas

A regressão cobre, entre outros, o fluxo de cinco turnos:

```text
1. foco em tarefa A
2. "muda ela pra sexta"        → A
3. novo foco em compromisso B
4. "cancela esse"              → B
5. "cancela a anterior"        → A
```

Também cobre:

- lista `[A, B, C]` → `conclui a segunda` → B;
- lista `[A, B, C]` → `cancela a terceira` → C;
- dois usuários com `ela` apontando para IDs diferentes;
- criação explícita bloqueando o reaproveitamento do contexto anterior.

## Autoridade de escrita

A Etapa 1.3 resolve o alvo, mas não cria um segundo CRUD.

Fluxo:

```text
texto
→ short_context resolve target_id
→ reference_patch transforma a referência em alvo explícito
→ conversation_layer / módulo de domínio executa a ação
```

Portanto a resolução de linguagem e a escrita continuam separadas.

## Desempenho

Durante a Etapa 1.3 foi identificada lentidão no caminho interativo. A correção foi separada na PR #14:

- reconciliação de Durable Objects pós-webhook sai do caminho crítico da resposta;
- handler de referências possui gate lexical antes do D1;
- DDL defensivo de presença saiu do dispatcher geral, pois a migration 0003 já é a fonte formal do schema.

A regressão de desempenho estrutural impede que mensagens irrelevantes consultem contexto dentro do handler de referências.

## Adição de produto registrada durante a 1.3

Foi aprovado também um **Assistente Geral de Tempo** para a Etapa 3, ao lado do Modo Estudo.

Documento:

```text
docs/ETAPA_3_ASSISTENTES_DE_TEMPO.md
```

A Etapa 1 já prepara a linguagem com:

```text
daqui a 5 minutos
em 1 hora
cronometra 30 minutos
inicia um timer de 45 segundos
```

mas a execução persistente do timer permanece para a Etapa 3.

## Gate da subetapa

- [x] autoridade de contexto curto criada;
- [x] expiração baseada em timestamp existente;
- [x] lista de tarefas grava ordem visível;
- [x] `a primeira/a segunda/a terceira` possuem resolução estrutural;
- [x] `a terceira/o terceiro` pertencem ao detector comum;
- [x] `essa/ela/ele` usam contexto recente;
- [x] `a outra` é conservadora quando há múltiplos candidatos;
- [x] `a anterior` possui histórico consistente entre focos sucessivos;
- [x] ação nova funciona como barreira de contexto;
- [x] linguagem de tempo relativo possui corpus separado;
- [x] contexto legado redirecionado para `short_context`;
- [x] sequência real de 5 turnos coberta;
- [x] cenários DB multiusuário adicionados;
- [x] qualificadores temporais de referência validados;
- [x] correção de latência estrutural mesclada e verde na `main`;
- [x] regressão completa verde no PR de contexto unificado.

Próxima subetapa: **1.4 — correção e auto-reparo conversacional**, cobrindo respostas como `não, 16h`, `quis dizer terça`, `melhor quinta`, sem duplicar o item recém-criado.
