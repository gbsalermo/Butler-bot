# Butler — Etapa 1.2: Base Linguística Comum

**Data-base:** 30/08/2026  
**Status:** implementação da subetapa 1.2  
**Origem:** `docs/ETAPA_1_AUDITORIA_LINGUAGEM.md`

## Objetivo

Fazer os parsers operacionais compartilharem um contrato linguístico mínimo sem criar uma NLU central que execute ações.

A divisão de responsabilidade passa a ser:

```text
language_primitives.py
→ normaliza e reconhece sinais linguísticos
→ NÃO acessa D1
→ NÃO envia Telegram
→ NÃO executa CRUD

módulo do domínio
→ resolve dados específicos
→ valida tempo/alvo
→ persiste quando autorizado
```

## Integrações realizadas

### Lembretes

`colloquial_reminder_fastpath.py` passa a ser a autoridade única de criação natural de lembretes.

`natural_behavior_patch.handle_explicit_simple_reminder()` permanece apenas como wrapper de compatibilidade para pontos antigos do dispatcher e delega para o módulo autoritativo. Ele não possui mais `INSERT INTO daily_items`.

A família `reminder` cobre o repertório já aceito, incluindo:

- me lembra / me lembre;
- me avisa / me avise;
- me recorda / me recorde;
- não deixa eu esquecer;
- me dá um toque;
- cria/criar um lembrete;
- anota/anotar um lembrete;
- formas equivalentes já existentes no fast path.

A polaridade agora é explícita:

```text
não me lembra de estudar
→ família: reminder
→ polaridade: negative
→ não cria lembrete

me lembra de não estudar
→ família: reminder
→ polaridade: positive
→ negação pertence ao conteúdo

não deixa eu esquecer
→ negação superficial idiomática
→ polaridade: positive
```

### Tarefas

`operational_informal_fastpath.py` deixa de manter outra lista independente de verbos e usa a família `create_task`.

`preciso` deixa de ser gatilho genérico. A base só aceita construções operacionais suficientemente claras, como `preciso pagar`, `preciso terminar`, `preciso revisar`, etc.

Assim:

```text
preciso pagar a conta
→ tarefa

preciso de ajuda com cálculo
→ não é tarefa
```

Também se corrige uma ambiguidade antiga: `criar uma tarefa ...` não pode ser transformado em lembrete simples por um parser concorrente.

### Compromissos

`operational_informal_fastpath.py` usa a família `create_appointment` para frases claras como:

- tenho dentista;
- tenho consulta;
- tenho reunião;
- criar/cria um compromisso;
- reunião sexta 10h.

### Gate do Core

`core_fast_path.py` usa famílias comuns para ações operacionais:

- reminder;
- create_task;
- create_appointment;
- create_routine;
- complete;
- cancel;
- reschedule.

`CORE_HINTS` fica reservado a consultas e domínios específicos que ainda não pertencem ao contrato de ato linguístico comum.

Isso reduz a necessidade de repetir `me lembra`, `cria tarefa`, `tenho dentista`, `cria rotina` em vários arquivos.

## O que não foi feito

A 1.2 não resolve ainda:

- `essa`, `ela`, `a anterior` entre vários turnos;
- correção `não, 16h` do item recém-criado;
- expiração/barreira de contexto;
- segmentação de múltiplas intenções;
- conjunções como roteamento operacional;
- elipse ampla.

Esses pontos pertencem às subetapas 1.3–1.5.

## Invariantes

1. `language_primitives.py` continua sem efeitos colaterais.
2. Reconhecer família linguística não autoriza escrita por si só.
3. Negação da ação nunca deve virar escrita positiva.
4. `não deixa eu esquecer` permanece pedido positivo de lembrete.
5. Tarefa explícita continua tarefa; não pode ser reclassificada como lembrete simples.
6. Falsos positivos deliberados do corpus continuam protegidos.
7. Módulos de domínio continuam autoridades da persistência.

## Gate da 1.2

- [x] lembretes usam família comum;
- [x] tarefas usam família comum;
- [x] compromissos usam família comum;
- [x] Core usa famílias comuns para ações principais;
- [x] duplicação de criação natural de lembrete foi removida;
- [x] polaridade de lembrete possui teste;
- [x] `preciso de ajuda` não vira tarefa;
- [x] `criar uma tarefa` não vira lembrete;
- [x] regressão completa verde no PR;
- [ ] regressão pós-merge verde na `main`.

Próxima subetapa após o gate: **1.3 — referências + contexto curto com expiração e barreira de assunto**.
