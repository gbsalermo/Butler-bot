<p align="center">
  <img src="assets/butler.png" alt="Butler - mascote" width="420">
</p>

# Butler Bot

**Butler** é um assistente pessoal via Telegram voltado a organização cotidiana, memória contextual e companhia funcional. Ele combina tarefas, compromissos, estudos, casa, musculação, metas e finanças com linguagem determinística, memória pessoal e uma biblioteca opcional de conhecimento.

A proposta não é ser um CRUD com personalidade nem uma IA geral. O objetivo é que as funções pareçam partes de **um único assistente pessoal**, mantendo o Core determinístico como autoridade.

Bot pessoal: **Butler** — `@ButlerSal_BOT`.

## Princípios

- Core funcional sempre vence Library, background e contexto antigo;
- texto natural e botões convivem;
- a mensagem atual define o assunto; contexto anterior só ajuda quando realmente existe continuidade;
- comentário não vira ação automaticamente;
- problema pode gerar ajuda + sugestão;
- ação derivada/ambígua exige confirmação;
- escrita sugerida passa pelo gateway do Core;
- memória e contexto são isolados por `user_id`;
- conhecimento cultural é global, opcional e separado da memória pessoal;
- novos exemplos alimentam domínios reutilizáveis, não novos `if`s.

## 🧠 Arquitetura de conversa

A produção usa um dispatcher em tiers:

```text
mensagem
   ↓
Context Router + Intent Parser
   ↓
1. Core funcional
   ↓
2. memória/contexto pessoal
   ↓
2.5 sugestões confirmáveis
   ↓
3. Butler Library opcional
   ↓
4. linguagem / conversa / fallback
```

`context_router.py` classifica domínio, tier, formato da fala, intenção, alvo e pista temporal. `intent_parser.py` reconhece famílias estruturais em vez de depender apenas de frases prontas.

Domínios protegidos incluem matérias/aulas/provas/faltas, tarefas, compromissos/agenda, mercado, musculação, finanças, metas e rotinas. Se a mensagem pertence ao Core, nenhum acervo pode disputá-la.

Exemplos que devem convergir para o mesmo domínio acadêmico:

```text
segunda eu não vou pra Sistemas
quero faltar Sistemas segunda
acho que vou matar Sistemas segunda
```

## 🗣️ Português informal e política de ação

`knowledge/portuguese_conversation.py` funciona como background linguístico, não como chatbot. Ele normaliza abreviações e fala coloquial (`oq`, `pq`, `vc`, `tbm`, `hj`, `dps`, `tô`, `facul`, `trampo` etc.) para ajudar NLU e roteamento.

`action_policy.py` formaliza:

```text
comentário → conversa
pedido explícito → ação pelo Core
problema/necessidade → ajuda + possível sugestão
ação derivada → confirmação antes de escrita
```

Por isso `comprar café` pode ser ação direta, enquanto `acabou o café` oferece colocar café na lista e espera confirmação. `tô cansado hoje` continua sendo conversa, não uma tarefa inventada.

## 🧩 Contexto recente

`context_memory.py` mantém até poucos tópicos recentes por usuário em D1. A tabela possui migration própria (`0004_conversation_context.sql`).

`context_sync.py` registra mudanças explícitas de domínio e invalida contextos opcionais legados. `library_context_bridge.py` faz os acervos alimentarem a mesma memória operacional central.

Isso permite continuidade como:

```text
receita de carbonara
não tenho bacon
```

sem permitir que carbonara reapareça depois de:

```text
queria faltar essa aula de Sistemas Digitais I
```

## 👤 Memória pessoal determinística

O Butler mantém um mapa pessoal isolado por usuário. Entidades atuais incluem pets, familiares, amigos/colegas, relacionamentos, veículos e objetos. `personal_profile.py` acrescenta preferências explícitas como gostos, desgostos, preferências, time e cidade, sem inferir fatos que o usuário não disse.

Exemplos:

```text
tenho um gato chamado Jake
meu gato tá sem ração
minha mãe se chama Ana
meu carro é um Corsa 2008
eu gosto de ficção científica
o que você sabe sobre mim?
```

A consulta do mapa pessoal reúne apenas fatos realmente estruturados daquele `user_id`.

## ⚙️ Core determinístico

O Core cobre tarefas, compromissos, agenda, pendências, matérias/grade, faltas, provas, lembretes, lista persistente de itens faltando, metas/streaks, rotinas, finanças simples e musculação.

`core_actions.py` é o gateway usado por camadas auxiliares quando uma sugestão foi confirmada. Library, memória e sugestões não mantêm mais uma segunda implementação de escrita para mercado/rotina/tarefa.

## 💡 Sugestões transversais

`suggestion_engine.py` transforma problemas em propostas, não em ações automáticas.

Exemplos:

- `acabou o café` → pergunta se deve colocar café na lista;
- pet conhecido sem ração → resolve o pet pela memória e oferece salvar ração;
- ingrediente ausente após receita → oferece mercado;
- série que o usuário quer assistir inteira → oferece rotina;
- duas provas no mesmo dia → oferece montar plano de estudo.

`study_plan_flow.py` completa o fluxo das duas provas para qualquer usuário: identifica matérias do próprio usuário, mostra a proposta e, após confirmação, cadastra provas ausentes e distribui blocos de teoria/resumo, exercícios e revisão.

## 📚 Butler Library

A Library é **extra e opcional**. `knowledge/library_manifest.py` registra seus acervos e `library_index.py` fornece um índice comum orientado a dados.

Acervos atuais:

- 🍳 culinária: massas, carnes/cortes, salgados, arroz/feijão, legumes, saladas, frango, doces e cozinha brasileira tradicional;
- 🎮 jogos e Pokémon FireRed;
- 🎬 filmes, séries e cultura pop;
- 📖 literatura e filosofia;
- 🗣️ português informal como background não respondente.

A culinária inclui pratos tradicionais como moquecas, vatapá, baião de dois, acarajé, bobó, feijão tropeiro, galinhada, barreado, cuscuz nordestino, caruru e vaca atolada, além de conhecimento de cortes e preparações bovinas.

`library_catalog_handler.py` é um fallback genérico sobre o índice comum: novas entradas podem herdar busca por nome, aliases, tags, gênero, autor, resumo e metadados sem ganhar um dispatcher exclusivo.

A Library pode sugerir ações, mas escritas confirmadas passam pelo `core_actions.py`.

## 🕴️ Personalidade e cotidiano

O Butler aceita saudação, agradecimento, risada, cansaço, fome, desânimo e comentários sem responder sempre com produtividade. Humor e gírias podem variar com contexto, horário e histórico real. Sarcasmo comportamental só usa evidência registrada; primeira ocorrência não vira hábito inventado.

## 🌙 Day-off

Day-off reduz/silencia cobranças compatíveis. Reativação pode ocorrer chamando novamente o Butler. O estado é isolado por usuário.

## 🏋️ Musculação

No perfil pessoal existe protocolo de 12 semanas iniciado por `🚀 Começar os trabalhos`, com exercício, substitutos, séries, carga, repetições, faltas e evolução. Usuários genéricos começam sem esse protocolo e cadastram a própria musculação.

## 🧪 Regressão automática

A arquitetura conversacional agora possui proteção automática:

```text
cloudflare/tests/test_context_router.py
cloudflare/tests/test_library_index.py
.github/workflows/butler-regression.yml
```

A suíte cobre dezenas de formulações de acadêmico, tarefas, mercado, agenda, musculação, finanças, rotinas, culinária, jogos, livros, filmes/séries e conversa, além de colisões da Library.

Todo push relevante na `main` compila `cloudflare/src` e executa `pytest` no GitHub Actions. Uma regressão já foi encontrada pela própria suíte (`oi butler` recebia resultados irrelevantes do índice de livros) e corrigida exigindo evidência semântica antes do bônus por domínio.

Regressão obrigatória:

```text
receita de carbonara
queria faltar essa aula de Sistemas Digitais I
```

A segunda mensagem é acadêmica, nunca culinária.

## ☁️ Produção e LLM

Produção usa Cloudflare Worker/Webhook/D1. A camada oficial permanece determinística.

O laboratório Workers AI foi removido da `main` e preservado em `archive/llm-experiment`; `backup/nlu-only` mantém referência anterior. Uma LLM local/privada pode ser reconsiderada no futuro apenas como linguagem/contexto. Core, memória oficial e escrita continuam pertencendo ao Butler.

## Regra para expansão

Antes de adicionar funcionalidade, perguntar: isso melhora o trabalho de **assistente pessoal** ou só aumenta o catálogo?

Prioridade atual:

```text
1. estabilidade do Core
2. roteamento/contexto
3. memória pessoal
4. linguagem natural
5. sugestões úteis
6. Library
7. novas funcionalidades
```

A fase atual concluiu a fundação e integração dessas sete frentes. A próxima evolução deve ser principalmente ampliar cobertura/testes e corrigir casos reais, não criar uma nova camada paralela.

Materiais externos devem respeitar licenças e direitos autorais; preferir dados abertos, domínio público, documentos próprios e resumos/metadados produzidos para o projeto.
