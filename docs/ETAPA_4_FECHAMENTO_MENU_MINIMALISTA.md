# Fechamento da Etapa 4 — Menu minimalista aprovado

**Status:** ▶️ em andamento  
**Direção escolhida:** versão minimalista  
**Objetivo:** reduzir a raiz do Butler sem esconder funcionalidades, mantendo atalhos frequentes e agrupando o restante por contexto humano.

## Decisão aprovada

O menu principal passa a seguir esta direção:

```text
➕ Adicionar          🗓️ Hoje
🎓 Faculdade          📋 Minha vida
🏋️ Treino             ⚙️ Mais
🌙 Day-off
```

`🌙 Day-off` continua sozinho na última linha.

## Estrutura-alvo

### 🏠 Início

```text
➕ Adicionar          🗓️ Hoje
🎓 Faculdade          📋 Minha vida
🏋️ Treino             ⚙️ Mais
🌙 Day-off
```

### 🎓 Faculdade

```text
📚 Matérias           🍽️ RU
🧠 Modo Estudo        📘 Cursos
⬅️ Início
```

Regras:

- `📚 Matérias` continua sendo a porta para matérias, provas, faltas e importação da grade;
- `🍽️ RU` continua sendo consulta acadêmica compartilhada;
- `🧠 Modo Estudo` funciona como descoberta/atalho do domínio já existente, sem alterar suas regras;
- `📘 Cursos` permanece em **standby** e só aparece para o proprietário enquanto não for reestabilizado;
- usuários comuns não devem ver ações administrativas do RU nem Cursos estruturados em standby.

### 📋 Minha vida

```text
✅ Tarefas            📅 Compromissos
🧘 Rotinas            🎯 Metas
🛒 Casa               📌 Interesses
⬅️ Início
```

### 🛒 Casa

```text
🛒 O que está faltando?   ➕ Item faltando
⬅️ Minha vida
```

Clima continua prioritariamente por linguagem natural e nos resumos; não ganha um botão novo apenas para preencher a categoria.

### 📌 Interesses

Reaproveita o domínio persistente `Ler/ver depois`:

```text
➕ Adicionar à lista   📚 Livros
🎬 Filmes             🎓 Cursos
🗂️ Outras
✏️ Editar item        🗑️ Remover item
⬅️ Minha vida
```

`🎓 Cursos` aqui continua significando **cursos salvos para ver depois**, não o domínio estruturado `📘 Cursos`.

### 🏋️ Treino

Abre diretamente o menu de musculação já existente. Não será criada uma camada intermediária vazia.

O menu preserva as ações atuais de treino e termina em:

```text
⬅️ Início
```

Ações pessoais exclusivas do proprietário continuam protegidas para usuários comuns.

### ⚙️ Mais

```text
👤 Como me chamar      📖 Manual
⬅️ Início
```

Não será criado um botão `Configurações` vazio. Novas configurações só entram quando houver funcionalidade real.

### ➕ Adicionar

Continua como captura rápida, sem obrigar o usuário a navegar por áreas:

```text
✅ Tarefa              📅 Compromisso
🧘 Rotinas             🎯 Metas
➕ Item faltando
⬅️ Início
```

## Inventário funcional preservado

| Domínio atual | Destino na nova navegação | Observação |
|---|---|---|
| Hoje / agenda | raiz | atalho frequente preservado |
| Adicionar | raiz | captura rápida preservada |
| Tarefas | Minha vida | regras inalteradas |
| Compromissos | Minha vida | regras inalteradas |
| Rotinas | Minha vida | regras inalteradas |
| Metas | Minha vida | regras inalteradas |
| Itens faltando | Minha vida → Casa | atalho de adicionar também continua em `➕ Adicionar` |
| Ler/ver depois | Minha vida → Interesses | domínio persistente preservado |
| Matérias | Faculdade | inclui gestão acadêmica |
| Provas | Faculdade → Matérias | adicionar/listar/editar/cancelar preservados |
| Faltas/presença | Faculdade → Matérias | regras de presença não mudam |
| RU | Faculdade | atualização continua owner-only |
| Modo Estudo | Faculdade | regras e persistência não mudam |
| Cursos estruturados | Faculdade | standby; owner-only |
| Musculação | Treino | abre direto; sem camada extra |
| Manual | Mais | preservado |
| Como me chamar | Mais | preservado |
| Day-off | raiz, última linha | proteção preservada |
| Comandos admin/diagnóstico | sem botão público novo | continuam por comandos/rotas existentes |

## Compatibilidade de transição

Durante a migração, textos antigos devem continuar aceitos quando possível:

```text
🏠 Cotidiano
🏋️ Musculação
🏠 Menu principal
⬅️ Voltar ao cotidiano
```

Eles podem redirecionar para a nova área correspondente, mas não devem continuar sendo os rótulos principais exibidos.

## Regras de implementação

1. `operational_menu.py` continua sendo a autoridade da raiz e dos menus de áreas.
2. Não duplicar regras de negócio dentro do menu.
3. `Voltar` deve retornar à área imediatamente anterior; `⬅️ Início` retorna à raiz.
4. `❌ Cancelar ação` continua limpando apenas o fluxo guiado em andamento.
5. Linguagem natural permanece independente dos menus.
6. Botões antigos continuam aceitos durante a transição para não quebrar teclados já renderizados no Telegram.
7. `📘 Cursos` continua filtrado na fronteira do Telegram para usuários comuns.
8. Cada mudança de navegação deve ter regressão determinística.

## Ordem de execução

1. ✅ escolha da proposta: minimalista;
2. ✅ inventário e estrutura-alvo documentados;
3. ⏳ implementar raiz + áreas sem remover aliases antigos;
4. ⏳ alinhar botões `Voltar` dos domínios;
5. ⏳ atualizar manual/README/documentação de uso;
6. ⏳ regressões completas de navegação;
7. ⏳ validar em produção e fechar oficialmente a Etapa 4.
