# Butler — Etapa 1.3: Referências + Contexto Curto

**Data-base:** 30/08/2026  
**Status:** em implementação  
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

O contexto operacional passa a ter uma autoridade explícita em:

```text
cloudflare/src/short_context.py
```

Ele usa `natural_events.created_at`, já existente no schema, portanto esta primeira fatia não precisa de migration.

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

Contexto de um usuário nunca é candidato para outro.

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

## Referências cobertas nesta fatia

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

`a outra` só é executada sem pergunta quando existir exatamente uma alternativa inequívoca.

## Autoridade de escrita

A Etapa 1.3 resolve o alvo, mas não cria um segundo CRUD.

Fluxo:

```text
texto
→ short_context resolve target_id
→ reference_patch transforma a referência em alvo explícito
→ conversation_layer executa concluir/cancelar/adiar
```

Portanto a resolução de linguagem e a escrita continuam separadas.

## Próximos passos dentro da 1.3

- ampliar testes multiusuário com DB fake;
- validar qualificadores como `aquela de amanhã` antes de resolver;
- consolidar histórico `a anterior` em mais fluxos;
- garantir contexto em listas além de tarefas quando fizer sentido;
- integrar criação/edição que ainda grava contexto no formato antigo;
- testar mudança explícita de assunto em sequências de 3–8 turnos.

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

## Gate desta subetapa

- [x] autoridade de contexto curto criada;
- [x] expiração baseada em timestamp existente;
- [x] lista de tarefas grava ordem visível;
- [x] `a primeira/a segunda/a terceira` possuem resolução estrutural;
- [x] `essa/ela/ele` usam contexto recente;
- [x] `a outra` é conservadora quando há múltiplos candidatos;
- [x] ação nova funciona como barreira de contexto;
- [x] linguagem de tempo relativo possui corpus separado;
- [ ] regressão completa verde;
- [ ] cenários DB multiusuário adicionados;
- [ ] qualificadores temporais de referência validados;
- [ ] regressão pós-merge verde na `main`.
