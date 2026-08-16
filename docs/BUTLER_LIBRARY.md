# Butler Library

## Objetivo

A Butler Library é a camada global de conhecimento do bot. Ela existe para evitar transformar exemplos do usuário em regras individuais de código.

Exemplos como `Walter White`, `Spinoza`, `strogonoff`, `parmegiana` e `Pokémon FireRed` devem ser tratados como dados/fontes de um domínio, não como funcionalidades isoladas.

## Separação de responsabilidades

- **Butler Core:** tarefas, agenda, rotinas, mercado, treino, finanças e demais operações determinísticas.
- **Memória pessoal:** entidades e fatos privados, sempre isolados por `user_id`.
- **Butler Library:** conhecimento global compartilhado entre usuários.
- **Contexto da biblioteca:** últimos assuntos consultados por cada usuário, persistidos em `natural_events` e filtrados por `user_id`.

## Estrutura atual

```text
cloudflare/src/
  butler_library.py
  knowledge/
    __init__.py
    cooking.py
    pop_culture.py
    philosophy.py
    games.py
```

Novos domínios devem preferencialmente entrar em `knowledge/` e ser recuperados pelo roteador, em vez de criar novo `if` no dispatcher principal.

## Recuperação

A primeira versão usa aliases, normalização de português e intenção textual. Não há LLM nem embeddings.

O roteador consegue:

- localizar receitas por aliases;
- localizar séries/personagens e devolver resumo ou detalhe;
- localizar filósofos por diferentes formas de pergunta;
- executar geradores determinísticos apoiados por dados da biblioteca, como times de Pokémon FireRed.

## Contexto e continuidade

Ao responder uma entrada, o Butler persiste `library_context` por usuário.

Isso permite fluxos como:

```text
usuário: me passa uma receita de bolo
Butler: [consulta cooking.py e responde]
usuário: não tenho leite
Butler: quer que eu coloque leite na lista de itens faltando?
usuário: pode
Core: grava no mercado
```

Ou:

```text
usuário: me fala de Supernatural
Butler: [consulta pop_culture.py]
usuário: quero assistir ela toda
Butler: posso criar uma rotina diária; que horas?
usuário: 20h
Butler: confirma rotina diária às 20h?
usuário: pode
Core: cria a rotina
```

## Regra de escrita

A biblioteca nunca escreve diretamente por sugestão implícita.

Ações propostas são persistidas como `library_pending`; somente uma confirmação explícita executa o Core.

Ações iniciais:

- `grocery_add`;
- `routine_create`.

## Dados e direitos autorais

Preferir:

- fatos e resumos próprios;
- dados estruturados;
- material em domínio público;
- fontes abertas/licenciadas;
- documentos fornecidos pelo usuário quando apropriado.

Não copiar livros, revistas, guias ou obras protegidas integralmente para o repositório sem autorização/licença adequada.

## Evolução recomendada

1. ampliar os domínios e aliases de forma curada;
2. criar importadores de documentos/dados abertos;
3. adicionar busca por tags/tokens quando o catálogo crescer;
4. manter o contexto recente no D1;
5. somente considerar embeddings/LLM local quando a recuperação determinística deixar de ser suficiente.

Se uma LLM local for retomada futuramente, ela deve receber os trechos recuperados pela Butler Library e continuar sem autoridade direta sobre o Core.
