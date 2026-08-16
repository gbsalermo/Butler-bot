<p align="center">
  <img src="assets/butler.png" alt="Butler - mascote" width="420">
</p>

# Butler Bot

**Butler** é um assistente pessoal via Telegram voltado a organização cotidiana, memória contextual e companhia funcional. Ele combina tarefas, compromissos, estudos, casa, musculação, metas e finanças com uma camada conversacional determinística, personalidade contextual e uma biblioteca de conhecimento própria.

A proposta não é ser apenas um menu de CRUD nem tentar imitar uma IA geral. O Butler deve parecer familiar: lembrar pessoas, animais e coisas mencionadas pelo usuário, conversar de forma natural, usar humor com contexto e transformar conversas em ações úteis quando fizer sentido — sempre mantendo o Core determinístico como autoridade.

Bot pessoal: **Butler** — `@ButlerSal_BOT`.

## Princípios

- texto natural e botões convivem;
- dados e operações continuam determinísticos;
- nenhuma sugestão conversacional altera dados sem confirmação quando houver ambiguidade ou ação derivada;
- personalidade usa contexto e histórico real, não fatos inventados;
- memória pessoal é isolada por `user_id`/`chat_id`;
- conhecimento cultural é global e compartilhado;
- Day-off reduz cobranças;
- NLU determinística continua sendo a base oficial; o laboratório de LLM foi arquivado para possível retomada futura.

## Capacidades principais

O Butler atualmente cobre tarefas, compromissos, agenda, pendências, matérias/grade, importação de grade textual, lembretes, lista persistente de itens faltando, metas/streaks, rotinas, finanças simples, musculação genérica e um protocolo pessoal de treino de 12 semanas com acompanhamento por exercício/série, carga, repetições e substitutos.

A linguagem natural entende construções comuns como `amanhã tenho dentista às 15h`, `preciso comprar café`, `o que tenho sexta?`, `já fiz o relatório`, `gastei 35 com lanche` e `hoje não consigo treinar`. Quando falta informação, pergunta apenas o necessário; quando há mais de um alvo plausível, confirma antes de alterar registros.

## 🧠 Memória pessoal determinística

O Butler mantém memória estruturada de entidades pessoais por usuário. A memória é isolada: fatos de um `user_id` nunca devem ser usados para outro.

Domínios atuais incluem pets, familiares, amigos/colegas, relacionamentos, veículos e objetos pessoais. Isso permite conversas como:

```text
tenho um gato chamado Jake
Jake tá sem ração
qual o nome do meu gato?
minha mãe se chama Ana
meu carro é um Corsa 2008
```

A memória pessoal tem prioridade apenas quando a pergunta realmente aponta para uma entidade do usuário. Nomes culturais compostos conhecidos não devem ser sequestrados por coincidência de primeiro nome: `quem é Jake?` pode ser pessoal; `quem é Jake Peralta?` é cultura pop.

## 📚 Butler Library

A **Butler Library** é a biblioteca global de conhecimento do assistente. Conhecimento não deve crescer como centenas de `if`s no dispatcher; novos domínios são alimentados como catálogos/documentos pesquisáveis.

Arquitetura atual:

```text
cloudflare/src/
├── butler_library.py
└── knowledge/
    ├── cooking.py
    ├── games.py
    ├── pop_culture.py
    ├── philosophy.py
    └── books.py
```

A busca usa normalização, aliases, termos, tags e metadados do domínio. O contexto recente é salvo por usuário para permitir continuidade da conversa.

### 🍳 Culinária

Receitas possuem ingredientes, preparo, porções, dicas, tags e ingredientes pesquisáveis. A biblioteca aceita tanto pedido direto quanto consulta por ingredientes, por exemplo `receita de strogonoff` ou `tenho carne moída e batata, o que dá pra fazer?`.

Uma receita pode gerar uma **sugestão de ação**: se o usuário disser `não tenho leite`, o Butler pode oferecer colocar leite na lista de itens faltando. A escrita só ocorre após confirmação.

### 🎮 Jogos

O catálogo permite recomendação por plataforma, gênero, modo, peso aproximado e estilo. Exemplos: `me indica um jogo leve pra PC`, `quero um RPG`, `algum coop pra jogar com amigos`.

Pokémon FireRed possui também dados/gerador próprio para montar times aleatórios a partir do catálogo disponível.

### 🎬 Filmes, séries e cultura pop

O acervo contém obras, personagens, gêneros, clima e metadados úteis para perguntas e recomendações. Exemplos: Walter White, Jake Peralta, Palpatine, Breaking Bad, Supernatural, Brooklyn Nine-Nine, Star Wars e outras entradas.

Séries podem produzir uma sugestão prática. Após conversar sobre uma série, `quero assistir ela toda` pode levar o Butler a oferecer uma rotina diária; o horário é solicitado e a rotina só é criada após confirmação.

### 📖 Filosofia e livros

O catálogo de livros é propositalmente abrangente, com peso especial em literatura brasileira, clássicos, filosofia, Geração Beat, contracultura e dirty realism.

Inclui autores/obras de Machado de Assis, Graciliano Ramos, Clarice Lispector, Guimarães Rosa, Jorge Amado, Dostoiévski, Kafka, Camus, Orwell, Hesse, Platão, Spinoza, Nietzsche, Marco Aurélio, Kerouac, Bukowski e John Fante, entre outros.

A recomendação cruza autor, país, tipo e tags. Exemplos: `me indica um livro brasileiro`, `quero algo curto e existencial`, `algo parecido com Bukowski`, `algo na vibe de On the Road`, `quero começar filosofia`.

## 🔗 Biblioteca → Core

A Library pode **sugerir** operações, mas não é autoridade sobre dados. Fluxo consolidado:

```text
conversa
→ Butler Library / memória
→ contexto e sugestão
→ confirmação do usuário
→ Core determinístico
→ persistência
```

Exemplos já previstos: ingrediente faltante → lista de mercado; série que o usuário quer acompanhar → rotina diária. Esse padrão deve ser reutilizado em futuras integrações.

## 🕴️ Personalidade e conversa

O Butler deve responder saudações, comentários cotidianos, agradecimentos, risadas e estados simples sem transformar toda conversa em produtividade. Humor, gírias e postura podem variar com contexto, horário e histórico, mas não devem soar como frases prontas repetidas.

Sarcasmo comportamental só ganha força quando há evidência real: adiamentos recorrentes, atrasos repetidos, streaks, faltas de treino ou evolução registrada. A primeira ocorrência não vira hábito inventado.

## 🌙 Day-off

Day-off representa folga/indisponibilidade. Enquanto ativo, cobranças e lembretes compatíveis são reduzidos/silenciados. A reativação pode ocorrer chamando novamente o Butler. O estado é isolado por usuário.

## 🏋️ Musculação

No Butler pessoal existe um protocolo de 12 semanas iniciado por `🚀 Começar os trabalhos`, com treino do dia/semana, exercícios, substitutos, registro série por série, carga, repetições, faltas e evolução. Antes da ativação, o protocolo não deve interferir nos resumos.

Usuários genéricos começam sem o protocolo pessoal e podem cadastrar a própria rotina.

## ☁️ Produção

A produção usa a arquitetura Cloudflare/Webhook/D1. O desenvolvimento histórico local utilizou Python, polling, SQLite e JobQueue; essas decisões locais não devem ser confundidas com a implementação de produção.

O Core continua determinístico e multiusuário. A memória pessoal e os contextos da Library são sempre associados ao usuário correto.

## 🧪 LLM

Foi testado um laboratório com Workers AI como camada de linguagem/persona/memória, mantendo o Core determinístico. A experiência apresentou problemas de integração e latência e foi removida da `main`.

- experimento preservado: `archive/llm-experiment`;
- referência pré-LLM: `backup/nlu-only`;
- direção oficial atual: NLU + memória + Butler Library determinísticas;
- possibilidade futura: LLM local/privada em serviço/container, apenas como camada de linguagem/contexto, nunca como autoridade de escrita.

## Regra para expansão

Quando surgir um novo exemplo — receita, personagem, livro, jogo, filme — evitar criar uma feature específica para aquele exemplo. Primeiro perguntar se ele pertence a um **domínio de conhecimento reutilizável**. A expansão preferida é alimentar/importar dados para a Butler Library e melhorar os mecanismos de recuperação/generalização.

Materiais externos devem respeitar direitos autorais e licenças: preferir dados abertos, domínio público, documentos próprios e resumos/metadados produzidos para o projeto em vez de copiar obras protegidas integralmente.
