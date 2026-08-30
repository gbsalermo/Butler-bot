# Butler — Etapa 1: Auditoria de Linguagem Natural

**Data-base:** 30/08/2026  
**Status:** Etapa 1.1 — inventário e contrato inicial  
**Roadmap:** `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`

> Este documento descreve **como a linguagem natural chega ao runtime hoje** e quais responsabilidades precisam ser consolidadas antes de ampliar o repertório. Ele não altera a autoridade do dispatcher definida em `docs/ARCHITECTURE.md`.

---

## 1. Objetivo da auditoria

A Etapa 1 não deve virar uma coleção crescente de regex nem reativar a NLU histórica inteira. Antes de ampliar o repertório, precisamos saber:

- quem normaliza texto;
- quem detecta ações;
- quem interpreta datas/horas;
- quem resolve referências;
- quem mantém contexto curto;
- quem lida com estado guiado;
- quais módulos concorrem pela mesma frase;
- quais frases hoje escapam deliberadamente do Core;
- quais comportamentos precisam virar contrato de regressão.

O modelo de destino permanece:

```text
AÇÃO
ALVO
TEMPO
QUALIFICADORES
RELAÇÕES
CONTEXTO
NÍVEL DE CONFIANÇA
```

---

## 2. Ordem real relevante do dispatcher

Trecho da cadeia ativa com impacto em linguagem:

```text
produção/usabilidade
→ menu operacional
→ rotinas / presença / navegação global
→ core_fast_path
→ acadêmico
→ lembrete explícito simples
→ reference_patch
→ task_context_patch
→ runtime_guard
→ mercado / quality / musculação
→ conversation_layer
→ app.py apenas quando necessário
→ fallback
```

Consequência: uma frase não é interpretada por um parser único. Ela atravessa uma **cadeia de parsers especializados**, e o primeiro que retorna `True` vence.

---

## 3. Mapa dos componentes ativos de linguagem

| Componente | Papel atual | Escrita | Contexto | Risco de sobreposição |
|---|---|---:|---:|---|
| `core_fast_path.py` | gate conservador e roteamento para fast paths | indireta | não | alto: contém hints de vários domínios |
| `nlu.py` | datas, horas, limpeza de título e `interpret()` legado/operacional | não diretamente | não | médio: parte das intenções também existe em fast paths |
| `colloquial_reminder_fastpath.py` | lembretes coloquiais + wizard data/hora | sim | grava referência após criar | alto com `natural_behavior_patch.py` |
| `natural_behavior_patch.py` | lembrete explícito simples + memória do último item criado | sim | sim | alto com parser coloquial e Core gate |
| `operational_informal_fastpath.py` | tarefas e compromissos claros | sim | sim | médio com `nlu.interpret()` e `app.py` |
| `reference_patch.py` | referências e ações específicas por contexto/data | sim | lê/grava `natural_events` | alto com `conversation_layer.py` |
| `conversation_layer.py` | contexto operacional recente e ações sobre item recente | sim | autoridade prática de `natural_events` | alto com reference/task context |
| `task_context_patch.py` | continuação curta para adiar tarefa recente + lista posicional | sim | lê `conversation_layer` | médio |
| `runtime_guard.py` | estados guiados e execução de ações por tarefa/rotina | sim | `user_sessions` | médio: resolve alvo novamente |
| `routine_natural_fastpath.py` | criação natural de rotinas | sim | estado guiado | baixo/médio |
| `grocery_phrase_patch.py` | linguagem informal de mercado | sim | domínio próprio | baixo fora do mercado |
| `exam_phrase_patch.py` | frases naturais de prova | sim | acadêmico | baixo/médio |
| `weather_context.py` | clima + consultas Hoje/Amanhã | não crítico | contextual | baixo |
| `workout_progress_patch.py` | comandos naturais de treino | sim | domínio próprio | baixo |

---

## 4. Duplicações confirmadas

### 4.1 Normalização

Há implementações locais de `_norm()` em vários módulos. Elas não são idênticas:

- algumas removem pontuação;
- outras preservam `:` e `/` para horários/datas;
- algumas apenas removem acento e espaços;
- `nlu.normalize()` possui outra variante.

Isso significa que uma mesma frase pode produzir representações diferentes dependendo do handler que a recebe.

**Decisão da Etapa 1:** criar `language_primitives.py` como fonte comum para novos recursos. Migração dos módulos antigos será incremental e protegida por testes; não substituir tudo de uma vez.

### 4.2 Lembretes

Hoje uma frase de lembrete pode passar por:

```text
core_fast_path
→ natural_behavior_patch.handle_explicit_simple_reminder
→ colloquial_reminder_fastpath
```

E `handle_explicit_simple_reminder` também aparece posteriormente na cadeia principal do dispatcher.

A ordem atual evita parte das duplicações porque handlers retornam `True`, mas a definição de **“o que é pedido de lembrete”** está replicada.

**Destino:** uma família linguística comum identifica o ato de lembrar; o módulo de lembrete continua autoridade da persistência.

### 4.3 Referências

Há quatro mecanismos que resolvem alvo de tarefa/item em graus diferentes:

- `conversation_layer._resolve_item()`;
- `reference_patch.handle_reference()`;
- `task_context_patch._find_task()` / contexto recente;
- `runtime_guard._find_task()`.

Eles usam regras diferentes para:

- `essa` / `ela` / `isso`;
- número/posição;
- título parcial;
- único item pendente;
- último contexto.

**Destino:** separar `resolver referência` de `executar ação`. A resolução deve produzir candidato + confiança; o domínio decide se pode escrever.

### 4.4 Datas e horas

`nlu.parse_date()` e `nlu.parse_time()` são a base mais reutilizada, mas rotinas, treino e outros fluxos ainda têm regex próprios.

**Destino da Etapa 1:** não reescrever todo parser temporal. Primeiro padronizar linguagem geral e preservar `nlu` como autoridade temporal até existir motivo testado para ampliá-lo.

---

## 5. Lacunas de conversa real confirmadas

### 5.1 Correção após criação

Não existe hoje uma política única para:

```text
marca dentista amanhã às 15h
não, 16h
```

O segundo turno pode cair em parser temporal/estado dependendo do fluxo, mas não há contrato geral dizendo que é **correção do item recém-criado**.

### 5.2 Elipse

Casos como:

```text
e de tarde?
a outra
essa também
depois do almoço
melhor sexta
```

só funcionam em fluxos pontuais. Não há camada comum de elipse/contexto.

### 5.3 Escopo de negação

Precisamos distinguir:

```text
não me lembra de estudar hoje
me lembra de não estudar hoje
```

No primeiro, a negação atinge a ação. No segundo, atinge o conteúdo do lembrete.

### 5.4 Frases compostas

`core_fast_path._looks_compound()` hoje usa uma heurística de múltiplos grupos + comprimento e, quando considera a frase composta, **retira a mensagem do fast path**. Isso é uma defesa contra falso positivo, não uma solução de segmentação.

Exemplo-alvo:

```text
Amanhã tenho aula às 10, mas depois quero mexer no SGL e às 21h estudar inglês.
```

O Butler ainda precisa decompor a mensagem em blocos antes de decidir o que pode ou não ser persistido.

### 5.5 Relação não é ação

Conectores precisam carregar semântica:

```text
não vou treinar porque estou viajando
```

`porque estou viajando` é causa. Não autoriza criar compromisso `viajar`.

### 5.6 Barreira de mudança de assunto

Contexto recente deve ajudar referências curtas, mas uma ação explícita nova precisa vencer contexto antigo.

Exemplo:

```text
[contexto anterior: tarefa relatório]
qual é meu treino hoje?
```

Não pode interpretar `hoje` como continuação da tarefa anterior.

---

## 6. Código preservado que NÃO será reativado automaticamente

Existem módulos históricos úteis como referência:

- `compound_router.py`;
- `context_router.py`;
- `intent_parser.py`;
- `action_policy.py`;
- `context_memory.py`;
- `language_context.py`.

`compound_router.py`, por exemplo, já experimenta segmentação, porém mistura acadêmico, culinária, memória e pets. Ele não é adequado para virar o roteador central apenas por já existir.

**Regra:** reaproveitar ideias e testes, não religar a pilha histórica inteira.

---

## 7. Contrato da nova camada linguística

A nova camada `language_primitives.py` começa propositalmente **sem acesso a D1 e sem enviar mensagens**.

Responsabilidades permitidas:

- normalizar texto;
- remover vocativo `Butler`;
- reconhecer famílias verbais de ação;
- identificar conectores e relações;
- detectar referências explícitas;
- detectar marcadores de correção;
- estimar escopo simples de negação;
- oferecer sinais estruturais para parsers de domínio.

Responsabilidades proibidas:

- criar/editar/apagar registros;
- decidir presença;
- decidir conclusão;
- inferir compromisso a partir de comentário;
- consultar Library/memória cultural;
- escolher silenciosamente um item ambíguo.

---

## 8. Corpus inicial da Etapa 1

O corpus versionado deve crescer a partir de erros reais. As classes mínimas são:

```text
simple_action
reminder_variant
reference
correction
negation
connector
compound
false_positive
conversation_sequence
```

Meta final do gate da Etapa 1:

- 100 frases simples;
- 100 frases com conjunções;
- 50 referências contextuais;
- 50 correções/negações;
- 50 múltiplas intenções;
- 50 falsos positivos deliberados;
- sequências de 3–8 turnos;
- cenários com dois usuários.

A Etapa 1.1 não precisa atingir toda a meta imediatamente; precisa estabelecer o **formato, a fonte de verdade e a primeira bateria executável**.

---

## 9. Ordem de implementação validada pela auditoria

```text
1.1 auditoria + corpus inicial
↓
1.2 language_primitives comum
↓
1.3 referências + contexto curto com expiração/barreira de assunto
↓
1.4 correções, negação e elipse
↓
1.5 segmentação de frases compostas
↓
1.6 integração no dispatcher + conversas completas + multiusuário
```

A migração será incremental. Em cada subetapa, o módulo de domínio continua sendo a autoridade da escrita.

---

## 10. Gate da Etapa 1.1

A subetapa 1.1 pode ser fechada quando:

- [x] cadeia ativa de linguagem foi mapeada;
- [x] duplicações principais foram identificadas;
- [x] lacunas de correção, elipse, negação e composto foram registradas;
- [x] código preservado foi separado do runtime ativo;
- [ ] `language_primitives.py` existe sem efeitos colaterais;
- [ ] corpus inicial executável existe e passa no CI;
- [ ] nenhum comportamento de produção foi alterado apenas para “passar no corpus”.
