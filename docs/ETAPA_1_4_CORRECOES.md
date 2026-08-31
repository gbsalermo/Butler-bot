# Butler — Etapa 1.4: Correção e Auto-reparo Conversacional

**Data-base:** 30/08/2026  
**Status:** em implementação — auto-reparo temporal validado  
**Anterior:** Etapa 1.3 concluída

## Objetivo

Permitir que o usuário corrija naturalmente o turno anterior sem criar um novo item por engano.

Exemplo central:

```text
Usuário: marca dentista amanhã às 15h
Butler: 📅 Fechado: Dentista — 31/08 às 15:00.
Usuário: não, 16h
Butler: ✏️ Corrigido: Dentista — 31/08 às 16:00.
```

O segundo turno atualiza o mesmo registro.

## Primeira fatia — correção temporal

Formas reconhecidas:

```text
não, 16h
quis dizer terça
na verdade quarta às 14:30
melhor quinta
```

A correção pode substituir:

- apenas horário, preservando a data;
- apenas data, preservando o horário;
- data e horário juntos.

## Alvo seguro

O auto-reparo não usa simplesmente "o último contexto".

Somente um contexto marcado como:

```text
source=created
```

ou:

```text
source=corrected
```

pode sofrer correção silenciosa.

Isso evita:

```text
Butler mostra lista de tarefas
Usuário: melhor quinta
```

ser interpretado como alteração automática da primeira tarefa exibida.

Contextos vindos de listas (`source=task_list`) não são elegíveis.

## Correções sucessivas

Após corrigir, o contexto vira:

```text
source=corrected
```

Portanto:

```text
marca dentista amanhã às 15h
→ não, 16h
→ melhor 16:30
```

continua apontando para o mesmo item enquanto o contexto curto estiver válido.

## Segurança linguística

Uma negação superficial não basta para caracterizar reparo.

```text
não me lembra de estudar hoje às 20h
```

é uma nova intenção linguística negada e não uma correção do item anterior.

Também não entram nesta fatia:

```text
não essa, a outra
 deixa como tava
```

Referências continuam sob a Etapa 1.3 e rollback explícito fica para uma fatia posterior da 1.4.

## Persistência

A correção atualiza diretamente:

```text
daily_items.due_date
daily_items.due_time
```

sem:

- criar nova linha;
- incrementar `postpone_count`;
- tratar a correção como adiamento;
- alterar título;
- mudar conclusão/cancelamento.

## Desempenho

`correction_patch.temporal_correction()` faz o gate linguístico localmente.

Mensagens sem marcador de correção e sem data/hora retornam antes de qualquer consulta ao D1.

## Testes desta fatia

Cobertura adicionada para:

- `não, 16h`;
- `quis dizer terça`;
- data + hora;
- `não me lembra...` não virar correção;
- correção sem duplicar registro;
- contexto de lista não ser corrigido silenciosamente;
- mensagem comum não acessar D1 pelo handler de correção.

## Próximas fatias da 1.4

- correção de título/alvo quando explicitamente indicada;
- `deixa como tava` com rollback seguro da última correção;
- correções em fluxos guiados antes da persistência;
- ampliar sequências de 3–8 turnos;
- manter falso positivo baixo em negações e referências.

## Gate parcial

- [x] correção temporal do item recém-criado;
- [x] horário isolado preserva data;
- [x] data isolada preserva horário;
- [x] correção não cria duplicata;
- [x] item de lista não é alterado silenciosamente;
- [x] nova intenção negada não vira reparo;
- [x] gate linguístico antes do D1;
- [x] regressão completa verde no PR;
- [ ] rollback `deixa como tava`;
- [ ] correção explícita de título/alvo;
- [ ] sequências ampliadas;
- [ ] regressão pós-merge verde na `main`.
