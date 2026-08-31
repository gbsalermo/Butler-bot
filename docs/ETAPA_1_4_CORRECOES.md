# Butler — Etapa 1.4: Correção e Auto-reparo Conversacional

**Data-base:** 31/08/2026  
**Status:** em implementação — primeira fatia temporal mesclada na `main`  
**PR da primeira fatia:** #16  
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

## Estado atual da subetapa

A primeira fatia foi implementada e mesclada na `main` em 31/08/2026 pela PR #16.

Ela cobre **auto-reparo temporal do item recém-criado/corrigido**. A subetapa 1.4 ainda não está encerrada: rollback, correção de título/alvo e sequências maiores permanecem abertos.

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

A autoridade de contexto continua sendo `short_context.py`; a 1.4 não deve criar uma memória paralela.

## Segurança linguística

Uma negação superficial não basta para caracterizar reparo.

```text
não me lembra de estudar hoje às 20h
```

é uma nova intenção linguística negada e não uma correção do item anterior.

Também não entram nesta primeira fatia:

```text
não essa, a outra
deixa como tava
```

Referências continuam sob o contrato da Etapa 1.3 e rollback explícito permanece para uma fatia posterior da 1.4.

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

O Core/domínio continua sendo a autoridade da escrita; `correction_patch.py` não autoriza uma NLU genérica a editar qualquer item.

## Posição no dispatcher

`correction_patch` fica antes dos parsers de criação/fallback:

```text
acadêmico
→ correction_patch
→ lembrete explícito
→ referência curta
→ contexto de tarefa
→ ...
```

A ordem é deliberada: uma frase de reparo válida deve corrigir o turno anterior antes que outro handler tente interpretá-la como uma nova criação.

## Desempenho

`correction_patch.temporal_correction()` faz o gate linguístico localmente.

Mensagens sem marcador de correção e sem data/hora retornam antes de qualquer consulta ao D1.

A resolução `telegram_chat_id → user_id` também participa do cache local por update introduzido em `performance_patch.py`; isso não cria cache persistente entre mensagens.

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
- manter falso positivo baixo em negações e referências;
- validar regressão completa após cada fatia e atualizar `docs/STATUS_ATUAL.md`.

## Gate parcial

- [x] correção temporal do item recém-criado;
- [x] horário isolado preserva data;
- [x] data isolada preserva horário;
- [x] correção não cria duplicata;
- [x] item de lista não é alterado silenciosamente;
- [x] nova intenção negada não vira reparo;
- [x] gate linguístico antes do D1;
- [x] primeira fatia mesclada na `main` via PR #16;
- [ ] rollback `deixa como tava`;
- [ ] correção explícita de título/alvo;
- [ ] correções de fluxo guiado quando aplicável;
- [ ] sequências ampliadas;
- [ ] gate completo da 1.4 validado;

## Depois da 1.4

Concluir a 1.4 **não encerra automaticamente a Etapa 1**. Permanecem os gates globais de conjunções, mensagens compostas/múltiplas intenções, corpus ampliado, sequências reais, dois usuários e falsos positivos.

Não iniciar a Etapa 2 enquanto o gate global da Etapa 1 estiver aberto.
