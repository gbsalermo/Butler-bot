# Butler — Etapa 1.5: Frases compostas e conjunções

**Data-base:** 31/08/2026  
**Status:** concluída

## Objetivo

Entender mensagens com mais de uma oração sem usar `split(" e ")` ingênuo e sem transformar contexto causal, condição, alternativa ou complemento nominal em CRUD.

## Resultado

A Etapa 1.5 substituiu o `compound_router` histórico por uma camada neutra de linguagem e adicionou confirmação explícita para conjuntos totalmente determinísticos.

O Butler agora distingue relações como:

```text
e / também / além disso -> adição
mas / porém / só que -> contraste
porque / pois -> causa/contexto
então / por isso -> consequência
se / caso -> condição
depois / antes / em seguida -> sequência
quando -> temporal
enquanto -> simultaneidade
embora -> concessão
ou -> alternativa
```

Conector nunca é tratado sozinho como autorização de escrita.

## Proteções linguísticas

```text
Me lembra de comprar pão e leite amanhã.
```

continua sendo um lembrete, não duas ações.

```text
Tenho reunião com João e Maria amanhã.
```

continua sendo um compromisso.

```text
Tenho aula porque tenho que trabalhar.
```

`tenho que trabalhar` é contexto causal e não vira automaticamente tarefa.

```text
Tenho aula ou tenho dentista às 18h.
```

é alternativa; os dois lados não são executados.

## Preview e confirmação em lote

Quando existem de 2 a 5 ações independentes e todas já possuem os dados mínimos, o Butler mostra o plano antes de persistir.

Exemplo:

```text
Usuário:
tenho que pagar o boleto amanhã e tenho dentista sexta às 15h

Butler:
🧩 Entendi mais de uma ação na mesma mensagem:
1. ✅ tarefa — pagar o boleto — 01/09
2. 📅 compromisso — dentista — 04/09 às 15:00

Está tudo definido. Confirma que eu registre o lote inteiro?

[✅ Registrar tudo] [❌ Cancelar lote]
```

O subconjunto liberado nesta etapa é:

- tarefa com data definida;
- compromisso com data definida;
- lembrete simples com data e horário definidos.

Continuam fora da execução em lote:

- rotina;
- evento acadêmico;
- atividade planejada sem autoridade de persistência definida;
- temporizador rápido da futura Etapa 3;
- cancelamento/conclusão/reagendamento em massa;
- ações incompletas;
- alternativas;
- cláusulas causais/condicionais/concessivas.

## Persistência sem metade do lote

Depois de pré-validar todos os blocos, o conjunto é persistido por um **único `INSERT` multi-values** em `daily_items`.

Assim o fluxo não chama handlers independentes em sequência e não entra em wizard entre uma ação e outra.

Antes da confirmação:

- todas as datas/horários são validadas;
- lembrete precisa de horário exato;
- a confirmação expira após 10 minutos;
- horários são revalidados quando o botão é pressionado.

## Texto original preservado

A decisão linguística usa texto normalizado, mas o conteúdo persistido usa o segmento original reconstruído.

Portanto:

```text
comprar café
reunião
entregar relatório
```

não são degradados para:

```text
comprar cafe
reuniao
entregar relatorio
```

## Contexto pós-lote

Os IDs retornados são armazenados em `short_context` na mesma ordem exibida.

Isso mantém compatibilidade com:

```text
conclui a primeira
cancela a segunda
muda a terceira pra sexta
```

A resolução continua pertencendo à autoridade de contexto da Etapa 1.3.

## Desempenho

A análise de mensagens comuns continua local. D1 só entra quando existe lote determinístico para confirmação ou quando o usuário confirma/cancela esse lote.

## Gate final

- [x] substituir `compound_router` histórico por camada neutra;
- [x] segmentação guiada por relações da base comum;
- [x] prefixos temporais não escondem a ação principal;
- [x] `e` em conteúdo não vira automaticamente nova ação;
- [x] causa/condição/concessão não viram CRUD secundário;
- [x] alternativa não executa os dois lados;
- [x] preview simples sem acesso ao D1;
- [x] confirmação explícita;
- [x] pré-validação completa;
- [x] tarefa + compromisso + lembrete simples em lote seguro;
- [x] um único INSERT para o conjunto;
- [x] revalidação temporal;
- [x] confirmação expira após 10 minutos;
- [x] contexto posicional após criação;
- [x] combinações de 3 a 5 ações cobertas;
- [x] 6+ ações recusadas pelo gate de lote;
- [x] dois usuários com lotes simultâneos isolados;
- [x] `a primeira / a segunda / a terceira` validado após lote;
- [x] texto original/acentos preservados;
- [x] regressão completa verde.

## Próximo passo

**Etapa 1.6 — Conversas completas e gate final da Etapa 1.**

Ela deve combinar em sequências reais tudo que foi construído em 1.1–1.5: criação, correção, referências, mudança de assunto, mensagens compostas, dois usuários, falsos positivos e desempenho.
