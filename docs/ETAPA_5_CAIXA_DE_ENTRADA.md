# Etapa 5 — 📥 Caixa de entrada / captura rápida

**Status desta implementação:** funcional + regressão verde na branch; aguarda merge/deploy para fechamento oficial.

## Objetivo

Permitir capturar alguma coisa agora sem obrigar o usuário a decidir imediatamente se aquilo é tarefa, compromisso ou outro domínio.

Princípio central:

```text
capturar
≠
classificar
≠
executar
```

A Inbox não transforma texto em tarefa ou compromisso automaticamente.

## Entrada

Pelo menu:

```text
📋 Minha vida
→ 📥 Inbox
```

ou pelo fluxo rápido:

```text
➕ Adicionar
→ 📥 Capturar na Inbox
```

Também há captura textual explícita:

```text
joga na inbox: revisar autenticação do SGL
anota estudar cálculo pra eu organizar depois
```

A palavra `anota` sozinha não é tratada como Inbox. Isso preserva tarefas, lembretes e demais intenções já existentes.

## Persistência

Migration formal:

```text
cloudflare/migrations/0015_inbox.sql
```

Tabela:

```text
inbox_items
```

Estados:

```text
pending
converted
archived
```

Campos de conversão registram o domínio e o ID do alvo criado para manter rastreabilidade.

Autoridade:

```text
cloudflare/src/inbox_domain.py
```

A interface Telegram fica em:

```text
cloudflare/src/inbox_operational.py
```

## Processamento

Um item pendente pode ser:

```text
🧭 Processar
🗄️ Arquivar
```

Nesta primeira versão, processamento explícito permite:

```text
✅ Virar tarefa
📅 Virar compromisso
```

A tarefa pode ficar sem data. Compromisso exige data. Horário é opcional conforme o fluxo atual.

Depois da conversão, o item sai da lista de pendentes e permanece rastreável como `converted`.

## Anti-duplicação

`daily_items` recebe `source_inbox_id`, protegido por índice único.

Fluxo:

```text
Inbox #12
→ Tarefa #48
```

Se a mesma atualização do Telegram for repetida depois de uma falha parcial, o gateway reutiliza a tarefa/compromisso já criado em vez de gerar outro.

A criação de alvos passa por:

```text
cloudflare/src/core_actions.py
```

A Inbox não replica INSERTs de tarefas/compromissos em sua própria camada operacional.

## Arquivamento

Arquivar significa decidir que aquele registro não precisa ser transformado agora.

```text
🗄️ Arquivar
```

não cria tarefa, compromisso ou qualquer outro objeto.

Itens arquivados podem ser reabertos:

```text
🗄️ Arquivados
→ item
→ ♻️ Reabrir
```

## Multiusuário

Toda consulta e alteração usa `user_id`.

Um usuário não pode listar, abrir, arquivar, reabrir ou converter item pertencente a outro usuário.

## Menu

A Etapa 5 preserva a raiz minimalista concluída na Etapa 4.

A raiz continua:

```text
➕ Adicionar | 🗓️ Hoje
🎓 Faculdade | 📋 Minha vida
🏋️ Treino | ⚙️ Mais
🌙 Day-off
```

A Inbox entra apenas dentro de `Minha vida` e `Adicionar`.

## Gate oficial

Critérios do roadmap:

- [x] captura por botão/texto;
- [x] listar/processar/arquivar;
- [x] conversão segura para domínios;
- [x] sem duplicação ao converter;
- [x] isolamento multiusuário.

Regressão da branch após correções:

```text
420 testes passando
```

O fechamento oficial depende ainda de:

1. merge da PR da Etapa 5;
2. regressão pós-merge;
3. validação separada do `Workers Builds: salbutler-bot`;
4. sincronização do snapshot/roadmap para liberar a Etapa 6.

## Fora do escopo

A Etapa 5 não:

- classifica automaticamente a Inbox;
- usa IA/LLM;
- cria projetos automaticamente;
- substitui tarefas, compromissos ou Ler/Ver Depois;
- transforma toda frase com `anota` em captura.

A trilha de IA permanece pós-roadmap e pós-gate de estabilidade.
