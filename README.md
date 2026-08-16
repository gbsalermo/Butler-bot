<p align="center">
  <img src="assets/butler.png" alt="Butler - mascote" width="420">
</p>

# Butler Bot

**Butler** é um assistente pessoal via Telegram voltado a organização cotidiana, memória contextual e companhia funcional. Ele combina tarefas, compromissos, estudos, casa, musculação, metas e finanças com conversa determinística, memória pessoal e uma biblioteca opcional de conhecimento.

A proposta não é ser um CRUD com personalidade nem uma IA geral. O objetivo é que as funções pareçam partes de **um único assistente pessoal**, mantendo o Core determinístico como autoridade.

Bot pessoal: **Butler** — `@ButlerSal_BOT`.

## Princípios

- Core funcional sempre vence Library/background/contexto antigo;
- texto natural e botões convivem;
- dados e operações continuam determinísticos;
- comentário não vira ação automaticamente;
- problema pode gerar ajuda + sugestão;
- ação derivada/ambígua exige confirmação;
- memória pessoal é isolada por usuário;
- contexto recente é curto e não pode perseguir o usuário após mudança de assunto;
- conhecimento cultural é global, opcional e separado da memória pessoal;
- novos exemplos alimentam domínios reutilizáveis, não novos `if`s.

## 🧠 Arquitetura de conversa

O dispatcher passa a seguir uma hierarquia única:

```text
mensagem
   ↓
Context Router
   ↓
Core funcional
   ↓
Memória pessoal
   ↓
Butler Library (opcional)
   ↓
Linguagem / conversa / fallback
```

O `context_router.py` classifica domínio, tier, formato da fala e confiança antes das camadas opcionais. Matérias/aulas/provas/faltas, tarefas, compromissos/agenda, mercado, musculação, finanças, metas e rotinas são domínios protegidos.

A regra é: **a mensagem atual determina o domínio; contexto anterior apenas desempata continuidade plausível**.

## 🗣️ Português informal e intenção

`knowledge/portuguese_conversation.py` funciona como background linguístico, não como chatbot. Normaliza abreviações e fala coloquial (`oq`, `pq`, `vc`, `tbm`, `hj`, `dps`, `tô`, `facul`, `trampo` etc.) e auxilia separação de assunto.

`action_policy.py` diferencia três comportamentos:

```text
comentário → conversa
pedido explícito → ação pelo Core
problema/necessidade → ajuda + possível sugestão
```

Assim `tô cansado hoje` não precisa virar tarefa; `me lembra de dormir cedo` é pedido; `acabou a ração do Jake` pode oferecer adicionar ração ao mercado.

## 🧩 Contexto recente

`context_memory.py` fornece memória operacional curta por usuário, limitada a poucos tópicos recentes. Ela existe para follow-ups como `não tenho bacon` depois de carbonara ou `quero assistir ela toda` depois de Supernatural, sem deixar o assunto antigo sequestrar mensagens futuras.

Isso é diferente da memória pessoal permanente.

## 👤 Memória pessoal determinística

O Butler mantém entidades pessoais isoladas por `user_id`: pets, familiares, amigos/colegas, relacionamentos, veículos e objetos pessoais. Exemplos:

```text
tenho um gato chamado Jake
Jake tá sem ração
qual o nome do meu gato?
minha mãe se chama Ana
meu carro é um Corsa 2008
```

A direção é formar um pequeno mapa pessoal estruturado, sem salvar indiscriminadamente qualquer conversa.

## ⚙️ Core

O Core cobre tarefas, compromissos, agenda, pendências, matérias/grade, faltas, provas, lembretes, lista persistente de itens faltando, metas/streaks, rotinas, finanças simples e musculação.

A linguagem natural deve convergir diferentes formulações para a mesma operação. Ex.: `segunda eu não vou pra Sistemas`, `quero faltar SD1 segunda` e `segunda vou matar Sistemas` pertencem ao mesmo problema acadêmico; regras de negócio continuam no módulo acadêmico.

## 📚 Butler Library

A Library é **extra e opcional**. O manifesto está em `knowledge/library_manifest.py`. Ela pode enriquecer conversa e sugerir ações, mas não compete com Core e não grava operações silenciosamente.

Acervos atuais:

- 🍳 culinária: massas, carnes/cortes, salgados, arroz/feijão, legumes, saladas, frango, doces e cozinha brasileira tradicional;
- 🎮 jogos e Pokémon FireRed;
- 🎬 filmes, séries e cultura pop;
- 📖 literatura e filosofia;
- 🗣️ português informal como background não respondente.

A culinária inclui pratos tradicionais como moquecas, vatapá, baião de dois, acarajé, bobó, feijão tropeiro, galinhada, barreado, cuscuz nordestino, caruru e vaca atolada, além de conhecimento de cortes e preparações bovinas.

A Library cresce preferencialmente como **dados estruturados, tags, aliases e documentos pesquisáveis**, separando conteúdo do mecanismo.

## 🔗 Sugestões → Core

Sugestões são transversais, mas escrita pertence ao Core:

```text
conversa/problema
→ contexto ou Library
→ sugestão
→ confirmação quando necessário
→ Core
→ D1
```

Exemplos: ingrediente ausente → sugerir mercado; série longa → sugerir rotina; pet sem ração → sugerir mercado; duas provas próximas → futuramente sugerir plano de estudo. Nunca criar silenciosamente.

## 🕴️ Personalidade

O Butler aceita conversa simples sem responder sempre com produtividade. Humor e gírias podem variar com contexto, horário e histórico real. Sarcasmo comportamental só usa evidência registrada; primeira ocorrência não vira hábito inventado.

## 🌙 Day-off

Day-off reduz/silencia cobranças compatíveis. Reativação pode ocorrer chamando novamente o Butler. Estado isolado por usuário.

## 🏋️ Musculação

No perfil pessoal existe protocolo de 12 semanas iniciado por `🚀 Começar os trabalhos`, com exercício, substitutos, séries, carga, repetições, faltas e evolução. Usuários genéricos começam sem esse protocolo e cadastram a própria musculação.

## 🧪 Qualidade de conversa

`cloudflare/tests/test_context_router.py` inicia uma suíte de regressão entre domínios. Testes devem crescer com cenários completos, especialmente trocas bruscas de assunto. Um acervo novo não pode quebrar Core antigo.

Exemplo obrigatório:

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

Materiais externos devem respeitar licenças e direitos autorais; preferir dados abertos, domínio público, documentos próprios e resumos/metadados produzidos para o projeto.
