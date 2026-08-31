# Butler — Etapa 1.6: Conversas completas e gate final

**Data-base:** 31/08/2026  
**Status:** concluída

## Objetivo

Validar a Etapa 1 como um sistema conversacional coerente, não como uma coleção de frases que passam isoladamente.

A 1.6 não introduz uma nova NLU ampla. Ela combina os contratos das subetapas 1.1–1.5 em sequências reais e corrige conflitos encontrados entre essas peças.

## Cenários validados

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

A primeira ação não apaga mais a lista necessária para resolver os turnos seguintes.

Correção encontrada na 1.6: `short_context.remember()` preserva `candidate_ids` quando o novo foco já pertence à mesma lista recente. Um item novo fora daquela lista não herda candidatos antigos.

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

A nova consulta não é tratada como continuação/correção do item anterior.

### 3. Contexto expirado

Referências após a janela de contexto curto não ressuscitam um item antigo por pronome/ordinal.

### 4. Dois usuários

Contexto, listas e lotes simultâneos continuam isolados por `user_id` durante sequências de vários turnos.

### 5. Negação e auto-reparo

Permanece a diferença entre:

```text
não me lembra de estudar       -> ação negada
me lembra de não faltar        -> lembrete positivo com conteúdo negado
não deixa eu esquecer de pagar -> pedido positivo de lembrete
```

Correções e rollback continuam restritos a contexto seguro.

### 6. Frases compostas

Causa, condição e alternativa continuam sem promover contexto a CRUD secundário. Lotes seguros preservam ordem exibida e grafia original.

### 7. Assistente de Tempo futuro

As construções preparadas na Etapa 1:

```text
me lembra daqui a 5 minutos...
cronometra 30 minutos...
```

continuam classificadas como `relative_alert`/`timer`, sem serem persistidas como tarefas normais nesta etapa. A execução pertence à Etapa 3.

## Gate de saída

- [x] listas/lotes sobrevivem a referências sequenciais;
- [x] item novo não herda lista velha;
- [x] mudança de assunto interrompe contexto implícito;
- [x] contexto vencido não é reutilizado;
- [x] dois usuários permanecem isolados em sequências;
- [x] negação mantém escopo correto;
- [x] causa/alternativa não geram ação indevida;
- [x] temporizadores rápidos permanecem apenas no contrato linguístico;
- [x] lote composto preserva acentos/grafia original;
- [x] regressão completa verde;
- [x] subetapas 1.1–1.6 possuem contratos/regressões próprios.

## Resultado da Etapa 1

Com a 1.6, o gate técnico de **Etapa 1 — Linguagem natural + estabilidade de conversa real** está fechado.

A escrita crítica continua sob autoridades determinísticas de domínio; linguagem, contexto, correção e segmentação apenas resolvem intenção/alvo e aplicam confirmação quando necessário.

O próximo estágio oficial é **Etapa 2 — Acadêmico completo + importação robusta**.
