# Butler — Etapa 1.5: Frases compostas e conjunções

**Data-base:** 31/08/2026  
**Status:** em implementação — primeira fatia de análise/preview

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

## Primeira fatia

O antigo `compound_router.py`, que misturava acadêmico, culinária, pets e memória, foi substituído por uma camada neutra.

Ela:

- não acessa D1 para analisar;
- reutiliza `language_primitives.detect_relations()`;
- remove molduras temporais iniciais somente para revelar o verbo principal;
- identifica os atos linguísticos de cada segmento;
- classifica a relação entre os blocos;
- não executa múltiplas escritas automaticamente nesta primeira fatia.

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

## Preview no Core

Quando existem pelo menos duas ações independentes e seguras, o Core mostra um preview estrutural antes dos parsers de ação única.

Nesta primeira fatia o Butler informa o que entendeu e **não registra tudo automaticamente**. Isso impede que uma mensagem composta seja parcialmente salva pelo primeiro handler que reconhecer um fragmento.

## Gate parcial

- [x] substituir `compound_router` histórico por camada neutra;
- [x] segmentação guiada por relações da base comum;
- [x] prefixos temporais não escondem a ação principal;
- [x] `e` em conteúdo não vira automaticamente nova ação;
- [x] causa/condição/concessão não viram CRUD secundário;
- [x] alternativa não executa os dois lados;
- [x] preview não acessa D1;
- [ ] confirmação explícita do conjunto interpretado;
- [ ] execução sequencial das ações confirmadas;
- [ ] rollback transacional/lógico quando uma das ações falhar;
- [ ] ampliar corpus de frases compostas;
- [ ] fechar gate completo da 1.5.

## Próxima fatia

Adicionar **confirmação explícita** para conjuntos totalmente determinísticos. O Butler deverá mostrar o que pretende registrar e só depois executar cada ação pela autoridade de domínio já existente.

A Etapa 1.6 continuará sendo o gate final de conversas longas, dois usuários, falsos positivos e regressão completa.
