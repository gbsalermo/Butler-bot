# Butler — Etapa 1.5: Frases compostas e conjunções

**Data-base:** 31/08/2026  
**Status:** em implementação — análise/preview + confirmação segura em lote

## Objetivo

Entender mensagens com mais de uma oração sem usar `split(" e ")` ingênuo e sem transformar contexto causal, condição, alternativa ou complemento nominal em CRUD.

Exemplo-alvo:

```text
Amanhã tenho aula às 8,
depois quero estudar Java
e às 18 tenho dentista.
```

A estrutura esperada é:

```text
1. scheduled_event — aula às 8
2. planned_activity — estudar Java
   relação: sequência
3. create_appointment — dentista às 18
   relação: adição
```

## Primeira fatia — análise e preview

O antigo `compound_router.py`, que misturava acadêmico, culinária, pets e memória, foi substituído por uma camada neutra.

Ela:

- não acessa D1 para analisar;
- reutiliza `language_primitives.detect_relations()`;
- remove molduras temporais iniciais somente para revelar o verbo principal;
- identifica os atos linguísticos de cada segmento;
- classifica a relação entre os blocos;
- impede que um parser de ação única salve apenas o primeiro pedaço de uma mensagem composta.

## Relações

São consideradas estruturalmente:

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

## Regra de segurança

Conector não é sinônimo de nova ação.

```text
Tenho aula, mas estou cansado.
```

Só há uma ação reconhecida.

```text
Me lembra de comprar pão e leite amanhã.
```

`e leite` é conteúdo do lembrete, não uma segunda ação.

```text
Tenho reunião com João e Maria amanhã.
```

`e Maria` não cria outro compromisso.

```text
Tenho aula porque tenho que trabalhar.
```

A oração `tenho que trabalhar` aparece como contexto causal e não é candidata a CRUD automático.

```text
Tenho aula ou tenho dentista às 18h.
```

`ou` representa escolha; não executamos as duas alternativas.

## Segunda fatia — confirmação explícita do lote

Quando há 2 a 5 ações independentes e **todas** já podem ser resolvidas de forma determinística, o Butler monta um plano e pergunta antes de persistir.

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

O primeiro subconjunto liberado para lote é:

- tarefa com data definida;
- compromisso com data definida;
- lembrete simples com data **e horário** definidos.

Ainda não entram no lote:

- rotina;
- evento acadêmico;
- atividade planejada sem autoridade de persistência definida;
- temporizador rápido da futura Etapa 3;
- cancelamento/conclusão/reagendamento em massa;
- qualquer ação incompleta;
- alternativas com `ou`;
- cláusulas causais/condicionais/concessivas.

## Sem gravação parcial

O Butler não chama dois handlers independentes em sequência.

Depois da pré-validação de todos os blocos, o conjunto é persistido por um **único `INSERT` multi-values** em `daily_items`.

Com isso, o caminho normal não fica sujeito a:

```text
salvar ação 1
→ abrir wizard
→ falhar ação 2
→ deixar metade do pedido gravada
```

Se algum bloco não estiver completamente definido antes da confirmação, nenhum item do lote é criado.

## Revalidação na confirmação

Antes do `INSERT`, datas/horários são validados novamente.

Se o usuário deixar a confirmação aberta e um horário já tiver passado, o lote é cancelado e precisa ser recalculado.

Além disso, a confirmação pendente expira após **10 minutos**. Um botão antigo de `Registrar tudo` não pode registrar silenciosamente um lote esquecido horas ou dias depois.

## Contexto após criação

Depois de registrar o lote, a ordem dos IDs retornados é gravada no `short_context` com `source=compound_created`.

Isso prepara sequências futuras como:

```text
Butler registra:
1. pagar boleto
2. dentista

Usuário:
conclui a primeira
```

A resolução posicional continua pertencendo à Etapa 1.3; a 1.5 apenas fornece a lista criada na ordem exibida.

## Desempenho

Mensagens comuns continuam sendo analisadas localmente e retornam antes de acessar D1.

D1 só entra quando:

- há um lote determinístico a ser guardado para confirmação;
- o usuário pressiona `✅ Registrar tudo`;
- o usuário pressiona `❌ Cancelar lote`.

## Gate parcial

- [x] substituir `compound_router` histórico por camada neutra;
- [x] segmentação guiada por relações da base comum;
- [x] prefixos temporais não escondem a ação principal;
- [x] `e` em conteúdo não vira automaticamente nova ação;
- [x] causa/condição/concessão não viram CRUD secundário;
- [x] alternativa não executa os dois lados;
- [x] preview simples não acessa D1;
- [x] confirmação explícita do conjunto interpretado;
- [x] pré-validação completa antes de oferecer `Registrar tudo`;
- [x] tarefa + compromisso + lembrete simples suportados no lote seguro;
- [x] persistência do lote em um único INSERT multi-values;
- [x] revalidação temporal antes da confirmação;
- [x] confirmação expira após 10 minutos;
- [x] contexto posicional registrado após criação;
- [ ] ampliar corpus de frases compostas e combinações de 3–5 ações;
- [ ] testar dois usuários com lotes simultâneos;
- [ ] validar sequências pós-lote (`a primeira`, `a segunda`, correções e cancelamentos);
- [ ] fechar gate completo da 1.5.

## Próxima fatia

Ampliar o corpus para combinações de 3–5 ações e validar isolamento entre usuários, sequência pós-lote e falsos positivos adicionais. Não ampliar o conjunto de domínios persistidos até que cada domínio tenha contrato transacional equivalente.

A Etapa 1.6 continuará sendo o gate final de conversas longas, dois usuários, falsos positivos e regressão completa.
