# Butler Library

**Data-base:** 31/08/2026  
**Roadmap:** reativação seletiva prevista para a **Etapa 8**

> **Status atual:** arquitetura e acervo preservados. O dispatcher genérico da Library **não está habilitado no webhook operacional de produção**. Para o estado do projeto consulte `docs/STATUS_ATUAL.md`; para o fluxo ativo, `docs/ARCHITECTURE.md` e `cloudflare/src/entry.py`.

## Objetivo original e ainda válido

A Butler Library foi criada como camada global de conhecimento para evitar transformar cada exemplo em um `if` de código.

Entidades como personagens, filósofos, receitas, jogos e livros devem preferencialmente existir como dados/metadata de um domínio, e não como nova funcionalidade isolada.

## Separação conceitual

- **Butler Core:** operações determinísticas — tarefas, agenda, mercado, treino, rotinas, metas etc.;
- **memória pessoal:** fatos privados, sempre isolados por usuário;
- **Butler Library:** conhecimento global compartilhável;
- **contexto da Library:** continuidade curta das consultas daquele usuário.

Essa separação continua sendo uma boa direção arquitetural caso a Library seja reativada.

O `short_context.py` da Etapa 1 é hoje a autoridade de contexto operacional do Core. Uma futura Library não deve criar outra memória genérica que concorra silenciosamente com esse contrato.

## Estrutura preservada

Os principais arquivos permanecem no repositório:

```text
cloudflare/src/
  butler_library.py
  cooking_library.py
  library_catalog_handler.py
  library_context_bridge.py
  library_index.py
  library_recipe_queries.py
  knowledge/
    books.py
    brazilian_traditional_foods.py
    cooking.py
    cooking_books.py
    cooking_pasta.py
    games.py
    library_manifest.py
    meat_cuts.py
    philosophy.py
    pop_culture.py
    portuguese_conversation.py
```

O mapa completo está em `cloudflare/src/README.md`.

## Estado no runtime atual

O `/health` da produção declara explicitamente o dispatcher genérico da Library e o background cultural como desabilitados.

Isso significa que:

- editar uma entrada em `knowledge/` não garante que o webhook a responderá;
- `library_catalog_handler.py` não deve ser tratado como fallback final de produção hoje;
- testes de `library_index.py` preservam a qualidade do acervo, mas não provam integração com `entry.py`;
- uma futura reativação precisa escolher posição e precedência no dispatcher;
- a categoria `🎓 Cursos` em Ler/Ver Depois não é uma ativação da Library nem do domínio completo de Cursos/Trilhas.

## Recuperação preservada

A implementação existente usa normalização, aliases, tags e metadata. Não depende de LLM ou embeddings.

O desenho permite:

- busca de receitas e ingredientes;
- busca de jogos;
- filmes, séries e personagens;
- livros/literatura;
- filosofia;
- conhecimento culinário estruturado.

## Contexto preservado

A arquitetura anterior conseguia registrar assuntos recentes e continuar diálogos como:

```text
receita de bolo
→ não tenho leite
```

ou:

```text
me fala de uma série
→ quero assistir ela toda
```

Se essa continuidade for reativada, deve respeitar:

```text
mensagem explícita atual > contexto antigo
```

Uma consulta cultural nunca pode sequestrar uma tarefa, compromisso, ausência acadêmica ou outra operação clara do Core.

## Regra de escrita

A Library não deve ganhar autoridade para escrever silenciosamente no Core.

Se for reativada:

- consulta pode responder;
- comentário pode gerar proposta;
- ação derivada precisa de confirmação quando não foi pedida explicitamente;
- escrita confirmada deve passar por API/gateway do domínio correspondente;
- toda escrita deve ser limitada ao usuário correto.

## Dados e direitos autorais

Preferir:

- fatos e resumos próprios;
- dados estruturados;
- material em domínio público;
- fontes abertas/licenciadas;
- documentos fornecidos pelo usuário quando apropriado.

Não armazenar obras comerciais completas sem autorização/licença.

## Como reativar com segurança — Etapa 8

Uma reativação futura deve ser trabalho explícito, não import casual.

Checklist:

1. definir quais domínios entram primeiro;
2. justificar valor real para o produto;
3. definir em que ponto de `entry.py` a Library roda;
4. garantir prioridade do Core/fast paths;
5. decidir política de contexto, expiração e invalidação;
6. garantir isolamento de qualquer contexto pessoal;
7. conectar escritas somente por gateways do Core;
8. exigir confirmação para ação derivada;
9. adicionar testes do dispatcher final, não apenas do índice;
10. atualizar flags do `/health`;
11. atualizar `STATUS_ATUAL.md`, README, Dossiê e Arquitetura.

## Gate mínimo da Etapa 8 para Library

- [ ] domínios reativados possuem casos de uso claros;
- [ ] nenhuma consulta cultural captura intenção operacional explícita;
- [ ] contexto pessoal é isolado por usuário;
- [ ] nenhuma escrita silenciosa fora do Core;
- [ ] testes de integração cobrem precedência/falsos positivos;
- [ ] flags do `/health` refletem o runtime real.

## Direção recomendada

Não ampliar o catálogo apenas porque os arquivos existem. Primeiro estabilizar as etapas anteriores e, na Etapa 8, decidir quais partes da Library justificam voltar ao runtime.

Quando voltar, a prioridade deve ser recuperação orientada a dados e cobertura de integração, evitando o retorno de uma cadeia de `if`s por exemplo.
