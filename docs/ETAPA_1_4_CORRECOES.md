# Butler — Etapa 1.4: Correção e Auto-reparo Conversacional

**Data-base:** 31/08/2026  
**Status:** concluída  
**PRs:** #16 (primeira fatia) e #23 (fechamento)

## Objetivo

Permitir que o usuário corrija naturalmente o item recém-criado/corrigido sem gerar um segundo registro e sem usar contexto antigo ou ambíguo como alvo silencioso.

## Comportamentos cobertos

### Correção temporal curta

```text
Tenho dentista amanhã às 15h
→ não, 16h
```

```text
Me lembra sexta às 18h de entregar o relatório
→ melhor quinta
```

```text
→ quis dizer terça
→ na verdade quarta às 14:30
```

Data e horário podem ser corrigidos juntos ou separadamente, preservando o valor não alterado.

### Elipse de substituição

O lado posterior à negação é o valor novo:

```text
quinta não, sexta
15h não, 16h
amanhã não, terça
```

Isso evita interpretar a primeira data/hora como destino da correção.

### Correção de título/conteúdo

```text
Tenho dentista amanhã às 15h
→ não é dentista, é oftalmo
```

Também são aceitas formas como:

```text
dentista não, oftalmo
quis dizer oftalmo
na verdade é oftalmo
```

Quando a frase informa o valor antigo (`dentista não, oftalmo`), ele precisa bater com o título do item atual. Se o contexto estiver apontando para outro item, Butler não altera nada silenciosamente.

### Rollback da última correção

```text
Tenho dentista amanhã às 15h
→ não, 16h
→ deixa como tava
```

O item volta para 15h.

Formas suportadas incluem:

```text
deixa como tava
deixa como estava
desfaz
desfaz isso
volta pro anterior
```

O rollback usa apenas o snapshot da **correção imediatamente anterior**. Repetir `desfaz` não fica alternando infinitamente entre dois estados.

## Persistência

A Etapa 1.4 continua usando a mesma linha de `daily_items`.

Uma correção pode alterar:

```text
title
due_date
due_time
```

Ela não:

- cria uma nova tarefa/compromisso/lembrete;
- incrementa `postpone_count`;
- transforma correção em adiamento;
- altera conclusão/cancelamento;
- cria uma segunda memória de conversa.

O contexto permanece autoritativo em `short_context.py`.

Após uma correção, o contexto guarda somente o snapshot necessário:

```text
source=corrected
previous_title
previous_date
previous_time
undo_available=true
```

Após rollback:

```text
source=reverted
undo_available=false
```

Uma nova correção depois do rollback volta a criar um novo snapshot normal.

## Segurança de alvo

A correção silenciosa só aceita contexto recente com origem:

```text
created
corrected
reverted
```

Contexto de lista continua inelegível. Portanto:

```text
Butler mostra uma lista de tarefas
→ melhor quinta
```

não altera a primeira tarefa da lista por acidente.

Da mesma forma:

```text
Contexto atual: Dentista
→ não é relatório, é consulta
```

não renomeia Dentista para Consulta. O Butler informa que a correção parece apontar para outro alvo.

## Negação não é automaticamente correção

```text
não me lembra de estudar hoje às 20h
```

continua sendo uma nova intenção negada e não um reparo do turno anterior.

Referências como:

```text
não essa, a outra
```

continuam pertencendo à Etapa 1.3, não ao mecanismo de correção.

## Desempenho

Mensagens comuns são rejeitadas pelo gate linguístico antes de qualquer acesso ao D1.

A resolução de usuário também aproveita o cache por update introduzido em `performance_patch.py` quando disponível no caminho do dispatcher.

## Regressão

A suíte cobre:

- `não, 16h`;
- `quis dizer terça`;
- data + hora;
- `quinta não, sexta`;
- `15h não, 16h`;
- correção explícita de título;
- título antigo divergente não ser alterado;
- rollback da correção imediatamente anterior;
- sequência de várias correções + rollback;
- ausência de duplicata;
- contexto de lista protegido;
- dois usuários isolados pelas camadas anteriores;
- mensagem comum sem acesso ao D1.

## Gate da 1.4

- [x] correção temporal do item recém-criado;
- [x] horário isolado preserva data;
- [x] data isolada preserva horário;
- [x] correção elíptica usa o valor novo;
- [x] correção explícita de título/conteúdo;
- [x] validação do alvo antigo quando informado;
- [x] rollback `deixa como tava` / `desfaz`;
- [x] correções sucessivas sem duplicata;
- [x] item de lista não é alterado silenciosamente;
- [x] nova intenção negada não vira reparo;
- [x] gate linguístico antes do D1;
- [x] regressão completa verde;
- [x] gate da Etapa 1.4 concluído.

## Próximo passo

**Etapa 1.5 — Frases compostas e conjunções.**

O objetivo seguinte é interpretar múltiplos blocos sem dividir texto de forma ingênua:

```text
Amanhã tenho aula às 8,
depois quero estudar Java
e às 18 tenho dentista.
```

Conjunções (`e`, `mas`, `porque`, `se`, `quando`, `depois`, `antes`, `enquanto`, `ou`) devem carregar relação sem transformar toda oração em tarefa.

A Etapa 1 só será encerrada depois da 1.5 e do gate final 1.6.
