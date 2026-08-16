# Continuidade do desenvolvimento — Butler

> Documento consolidado em agosto/2026. Mantém as decisões históricas que continuam relevantes e registra a arquitetura atual de produção, memória e Butler Library.

## 1. Visão do produto

Butler é um assistente pessoal via Telegram. Não deve ser apenas CRUD/menu e também não tenta ser uma IA geral. O objetivo é unir organização cotidiana, memória contextual, conversa familiar e conhecimento útil, mantendo operações críticas determinísticas.

Princípios permanentes:

1. ações frequentes exigem poucos passos;
2. botões continuam disponíveis, mas texto natural deve ser confortável;
3. personalidade é sarcástica/provocativa de forma favorável ao usuário, sem humilhação;
4. sarcasmo comportamental nasce de fatos registrados;
5. ambiguidade de escrita exige confirmação;
6. não inventar presença, conclusão, treino, gasto, compromisso ou memória;
7. não prometer lembrete sem informação suficiente;
8. Day-off reduz cobranças;
9. cada usuário possui dados e memória isolados;
10. conhecimento global pertence à Butler Library, não à memória pessoal;
11. exemplos novos devem alimentar domínios reutilizáveis, não virar `if`s específicos;
12. **Library, cultura e backgrounds são extras opcionais: enriquecem a experiência, mas nunca têm prioridade sobre Core funcional.**

## 2. Estado técnico atual

A `main` usa produção Cloudflare com webhook Telegram e D1. A camada oficial de linguagem é determinística/contextual, sem LLM externa ativa.

Componentes recentes importantes em `cloudflare/src/`:

- `butler_library.py` — roteamento/busca da biblioteca e ponte de sugestões para o Core;
- `deterministic_memory.py` / memória pessoal — fatos estruturados por usuário;
- `companion_safe_fallback.py` — conversa básica/fallback contextual sem o bug de continuadores por substring;
- `language_context.py` — normalização informal e proteção de domínios do Core;
- `knowledge/portuguese_conversation.py` — acervo linguístico auxiliar, não respondente;
- `knowledge/cooking.py` / `knowledge/cooking_books.py`;
- `knowledge/brazilian_traditional_foods.py`;
- `knowledge/meat_cuts.py`;
- `knowledge/games.py`;
- `knowledge/pop_culture.py`;
- `knowledge/philosophy.py`;
- `knowledge/books.py`.

## 3. Core determinístico

O Core permanece autoridade sobre dados e operações. Linguagem, memória e biblioteca podem interpretar, contextualizar e **propor** ações, mas não devem criar uma segunda regra de negócio.

Contrato:

```text
mensagem
→ Core/fast paths funcionais
→ memória pessoal
→ proteção de domínio
→ Library/backgrounds somente quando não houver intenção funcional protegida
→ resposta ou sugestão
→ confirmação quando houver escrita derivada/ambígua
→ Core
→ D1
```

Domínios protegidos incluem, no mínimo: matérias/aulas/provas/faltas, tarefas, compromissos/agenda, mercado/lista, musculação, finanças, metas e rotinas. Se uma mensagem apontar claramente para um desses domínios, acervos de culinária/cultura/conversa não disputam a mensagem, mesmo que exista contexto recente de outra área.

Exemplos aprovados: receita + ingrediente ausente → sugerir item de mercado; série que o usuário quer acompanhar → sugerir rotina diária. A Library não grava essas ações diretamente.

## 4. Multiusuário e memória pessoal

A memória determinística foi propagada para usuários genéricos. Todo dado pessoal deve ser resolvido pelo `chat_id → user_id` e filtrado por esse usuário.

Domínios atuais: pets, familiares, amigos/colegas, relacionamentos, veículos e objetos pessoais. A memória deve crescer por entidades/relações claras, não tentar salvar qualquer frase aberta.

Exemplos:

```text
tenho um gato chamado Jake
Jake tá sem ração
qual o nome do meu gato?
minha mãe se chama Ana
meu carro é um Corsa 2008
```

Regra de conflito: memória pessoal não pode sequestrar entidade cultural composta. `quem é Jake?` pode consultar o contexto pessoal; `quem é Jake Peralta?` deve ir para cultura pop.

## 5. Butler Library

A Butler Library é conhecimento global compartilhado por todos os usuários. Ela substitui a estratégia de cadastrar cada exemplo no dispatcher.

### 5.1 Culinária

Receitas são dados estruturados com aliases, ingredientes, porções, preparo, dicas, tags e chaves de despensa. Busca direta, busca por ingrediente, categoria, sobras e fala informal são suportadas.

A culinária está organizada em áreas/livros como massas, carnes/cortes, salgados, arroz/feijão, legumes, saladas, frango, doces e cozinha brasileira tradicional.

O acervo tradicional inclui, entre outros: moqueca baiana/capixaba, vatapá, baião de dois, acarajé, bobó de camarão, feijão tropeiro, galinhada, barreado, cuscuz nordestino, caruru e vaca atolada.

O acervo de carnes diferencia corte de preparação/conservação e inclui filé mignon, contrafilé, alcatra, picanha, patinho, acém, músculo, costela, cupim, coxões, lagarto, fraldinha, maminha, peito, ossobuco, tutano, carne do sol e charque/carne-seca/jabá.

Objetivo de generalização: `receita de carne moída`, `tenho carne moída e batata`, `queria fazer um macarrão`, `sobrou arroz de ontem`, `como faço strogonoff?` devem ser consultas do mesmo domínio, sem novas features individuais.

Follow-up: `não tenho X` após uma receita pode oferecer salvar X em itens faltando; escrita só após confirmação. `falta` isolado nunca é interpretado como ingrediente porque pode significar falta acadêmica/ausência.

### 5.2 Jogos

Catálogo com plataforma, gênero, modos, peso aproximado e tags. Permite recomendações como jogo de PC, leve, RPG, estratégia, coop/multiplayer etc.

Pokémon FireRed possui dados/gerador próprio para times aleatórios. Esse é um exemplo de conhecimento estruturado alimentando lógica determinística, não uma resposta fixa.

### 5.3 Filmes, séries e cultura pop

Catálogo de obras/personagens com aliases, gênero, clima, episódios/temporadas quando aplicável e resumos. Inclui referências como Walter White, Jake Peralta, Palpatine, Breaking Bad, Supernatural, Brooklyn Nine-Nine, Star Wars etc.

Uma série pode manter contexto recente. `quero assistir ela toda` pode oferecer rotina diária, solicitar horário e confirmar antes de criar.

### 5.4 Filosofia

Acervo factual inicial para figuras e conceitos, incluindo Platão, Spinoza e outros. Variações como `quem foi`, `me explica`, `qual é a desse` e `era quem mesmo` devem convergir para intenção/alvo em vez de exigir frase exata.

### 5.5 Livros

Acervo amplo com prioridade em:

- literatura brasileira e clássicos;
- filosofia;
- clássicos internacionais;
- Geração Beat/contracultura;
- dirty realism e linha próxima a Bukowski/John Fante;
- obras na atmosfera de `On the Road`.

O catálogo cruza título, autor, país, tipo e tags. Inclui Machado de Assis, Graciliano Ramos, Clarice Lispector, Guimarães Rosa, Jorge Amado, Carolina Maria de Jesus, Dostoiévski, Kafka, Camus, Orwell, Hesse, Platão, Spinoza, Nietzsche, Marco Aurélio, Kerouac, Bukowski e John Fante, entre outros.

### 5.6 Prioridade dos acervos

A Library é deliberadamente opcional. Regra prática:

```text
Core explícito > memória funcional > acervo opcional > conversa/fallback
```

Exemplo de regressão já observada e proibida: após falar de receita, `queria faltar essa aula de Sistemas Digitais I` não pode ser interpretado como ingrediente faltando. A mensagem atual define o domínio; contexto recente apenas ajuda quando a mensagem atual é ambígua dentro do mesmo domínio.

## 6. Personalidade, português informal e conversa cotidiana

O Butler deve aceitar conversa simples sem responder sempre com produtividade. Saudações, agradecimentos, risadas, fome, sono, desânimo e comentários cotidianos devem ter respostas naturais e variadas.

Existe um acervo linguístico auxiliar de português informal com equivalências e marcadores como `oq`, `pq`, `vc`, `tbm`, `hj`, `dps`, `tô/to`, `blz`, `vlw`, `facul`, `trampo`, além de construções como `deu ruim`, `tá osso`, `queria`, `tava pensando`, `me lembra` etc.

Esse acervo **não é uma enciclopédia para perguntas sobre gírias** e não deve responder por conta própria. Sua função é melhorar normalização, intenção, mudança de assunto e separação de domínios.

Tom desejado: familiaridade e parceria, com humor/gírias quando cabem. Evitar frases feitas como transformar todo `oi` em `vamos resolver as coisas agora ou depois?`.

O histórico pode dar contexto a encorajamento ou provocação, mas apenas com dados reais. Primeira ocorrência nunca deve virar `você sempre...`.

## 7. Day-off

Day-off significa folga/indisponibilidade. Deve reduzir/silenciar cobranças e respeitar agendamentos compatíveis. Reativação pode acontecer chamando novamente o Butler. Estado isolado por usuário.

## 8. Tarefas, compromissos e agenda

Decisões preservadas:

- tarefa vencida e não concluída = pendência; pendência não é categoria cadastrável;
- remoção arquiva/cancela quando o histórico precisa ser preservado;
- bloquear data passada e horário passado no dia atual;
- `me lembra de...` sem data/hora pergunta quando;
- agenda reutiliza as mesmas fontes dos resumos;
- aulas da grade são `previstas`, não presença presumida;
- conclusão/atraso usa busca por alvo e confirma quando houver ambiguidade.

## 9. Casa / mercado

A lista é memória persistente do que falta em casa. Quantidade é opcional.

`preciso comprar café` tende a mercado; `preciso comprar adaptador para o trabalho` pode ser tarefa; pedido explicitamente temporal vira tarefa/lembrete.

A Butler Library pode sugerir itens de mercado a partir de contexto culinário, mas nunca deve gravar silenciosamente.

## 10. Acadêmico

Gerenciamento de matérias preserva listar/adicionar/remover/trancar/editar, horários/locais e importação de grade textual.

Decisões históricas mantidas:

- sem OCR/Tesseract;
- PDF precisa ter texto pesquisável ou ser convertido para `.txt`;
- SIGAA usa blocos de horas completas (`M23=08–10`, `M45=10–12`, `T23=14–16`, `T2345=14–18`, `N12=18–20`);
- correção manual tem prioridade;
- no perfil pessoal, Laboratório de Sistemas Digitais I permanece segunda 14:00–16:00.

## 11. Musculação

Butler pessoal possui protocolo interno de 12 semanas. `🚀 Começar os trabalhos` inicia oficialmente. Acompanhamento inclui dia/semana, exercício, substitutos, série por série, carga, repetições, faltas e evolução.

Antes de iniciar, o protocolo não deve aparecer nos resumos nem registrar falta. Mensagens comuns usam `treino na academia`, não o nome interno do protocolo.

Usuário genérico nasce sem esse protocolo e cadastra a própria musculação.

## 12. Metas, streaks e finanças

Streaks permanecem simples: Inglês, Programação, Água, Alimentação e Musculação. Evitar gamificação pesada sem necessidade.

Finanças permanecem deliberadamente simples: entradas, saídas, categorias, relatório mensal, saldo, comparação básica e alertas. Não adicionar cartões, parcelas, investimentos, múltiplas contas ou orçamento sofisticado sem nova decisão explícita.

## 13. Resumos

Resumo matinal e fechamento semanal continuam como mecanismos principais. Não existe fechamento automático noturno: o dia real pode terminar tarde.

## 14. Experimento LLM — decisão preservada

Em agosto/2026 foi testada uma LLM apenas como camada de linguagem, personalidade, memória e sugestão, com Core determinístico. Workers AI apresentou falhas de integração/fallback e latência; até diagnóstico não atravessou o fluxo de forma confiável.

Decisão: LLM removida da `main`. Preservação:

- `archive/llm-experiment` — laboratório;
- `backup/nlu-only` — referência pré-LLM.

A ideia útil — memória persistente — foi mantida deterministicamente.

Possibilidade futura: LLM local/privada em serviço/container (por exemplo runtime compatível com Ollama), somente para linguagem/contexto. Mesmo nesse cenário: memória pertence ao Butler, Core valida ações, nenhuma escrita direta pelo modelo e NLU determinística continua fast path/fallback.

## 15. Direitos autorais e fontes da Library

A Library pode futuramente importar documentos e bases, mas não deve armazenar indiscriminadamente livros/revistas comerciais completos. Preferir domínio público, dados abertos/licenciados, documentos próprios e resumos/metadados produzidos para o projeto.

Conhecimento estruturado é preferível quando o domínio pede cálculo/filtro (Pokémon, jogos, receitas); texto documental é adequado para contexto cultural, filosofia e literatura.

## 16. Testes prioritários após esta consolidação

Pente-fino manual deve misturar domínios para testar generalização e conflitos:

```text
oi butler
minha mãe se chama Ana
qual o nome da minha mãe?
tenho um gato chamado Jake
quem é Jake?
quem é Jake Peralta?
quem é Palpatine?
quem foi Spinoza?
me passa uma receita de strogonoff
não tenho creme de leite
pode
queria fazer um baião de dois
me explica carne do sol
me indica um jogo leve pra PC
monta um time aleatório pra FireRed
me fala de Supernatural
quero assistir ela toda
20h
pode
me indica um livro brasileiro
quero algo parecido com Bukowski
quero algo na vibe de On the Road
```

Teste obrigatório de troca de domínio:

```text
receita de carbonara
queria faltar essa aula de Sistemas Digitais I
```

A segunda mensagem deve ir ao Core acadêmico e nunca à culinária.

Também testar dois `chat_id` distintos para confirmar que memória, Day-off, contexto recente e ações nunca vazam entre usuários.

## 17. Próximos passos

1. ampliar conteúdo da Library por **fontes/domínios**, não exemplos individuais;
2. melhorar recuperação semântica determinística por intenção + alvo + tags + aliases;
3. adicionar testes automatizados da Library e conflitos memória pessoal × conhecimento global;
4. revisar respostas para evitar repetição/frases prontas;
5. manter documentação da Library em `docs/BUTLER_LIBRARY.md` sincronizada;
6. só reconsiderar LLM quando houver infraestrutura confiável e ganho claro sobre a solução determinística.

## 18. Regra de continuidade

Ao concluir etapas futuras: atualizar este arquivo e o README quando a capacidade pública mudar; registrar decisões técnicas; não remover decisões históricas sem substituição explícita; e deixar o próximo passo claro.
