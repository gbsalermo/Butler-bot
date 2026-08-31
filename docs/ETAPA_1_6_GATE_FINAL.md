# Butler — Etapa 1.6: Conversas completas e gate final

**Data-base:** 31/08/2026  
**Status:** em validação

## Objetivo

Validar a Etapa 1 como um sistema conversacional coerente, não como uma coleção de frases que passam isoladamente.

A 1.6 não deve introduzir uma nova NLU ampla. Ela combina os contratos das subetapas 1.1–1.5 em sequências reais e corrige apenas conflitos encontrados entre essas peças.

## Cenários obrigatórios

### 1. Lista/lote → múltiplas referências

```text
Butler registra/exibe:
1. Pagar boleto
2. Dentista
3. Enviar relatório

Usuário: conclui a primeira
Usuário: cancela a segunda
Usuário: muda a terceira pra sexta
```

A primeira ação não pode apagar a lista necessária para resolver os turnos seguintes.

Correção encontrada na 1.6: `short_context.remember()` agora preserva `candidate_ids` quando o novo foco já pertence à mesma lista recente. Um item novo fora daquela lista não herda candidatos antigos.

### 2. Mudança de assunto

```text
cria tarefa X
→ qual meu treino hoje?
```

ou:

```text
cria compromisso Y
→ tempo amanhã
```

A nova consulta não pode ser interpretada como continuação/correção do item anterior.

### 3. Contexto expirado

Referências após a janela de contexto curto não podem ressuscitar um item antigo por pronome/ordinal.

### 4. Dois usuários

Contexto, listas e lotes simultâneos devem continuar isolados por `user_id`.

### 5. Negação e auto-reparo

Manter a diferença entre:

```text
não me lembra de estudar
me lembra de não faltar
não deixa eu esquecer de pagar
```

E manter correções/rollback restritos a contexto seguro.

### 6. Frases compostas

Causa, condição e alternativa continuam sem promover contexto a CRUD secundário. Lotes seguros preservam a ordem exibida e a grafia original.

### 7. Assistente de Tempo futuro

As construções já preparadas na Etapa 1:

```text
me lembra daqui a 5 minutos...
cronometra 30 minutos...
```

continuam classificadas como `relative_alert`/`timer`, sem serem persistidas como tarefas normais nesta etapa. A execução pertence à Etapa 3.

## Gate de saída

- [ ] listas/lotes sobrevivem a referências sequenciais;
- [ ] item novo não herda lista velha;
- [ ] mudança de assunto interrompe contexto implícito;
- [ ] contexto vencido não é reutilizado;
- [ ] dois usuários permanecem isolados em sequências;
- [ ] negação mantém escopo correto;
- [ ] causa/alternativa não geram ação indevida;
- [ ] temporizadores rápidos permanecem apenas no contrato linguístico;
- [ ] regressão completa verde;
- [ ] roadmap mestre atualizado para Etapa 1 concluída.

## Próximo passo após o gate

Somente após todos os itens acima: **Etapa 2 — Acadêmico completo + importação robusta**.
