# Continuidade do desenvolvimento — Butler

> Consolidado em agosto/2026. Este documento registra decisões arquiteturais que devem sobreviver às próximas expansões.

## 1. Objetivo

Butler é um assistente pessoal via Telegram. Não deve ser apenas CRUD/menu nem tentar ser IA geral. O objetivo é unir organização cotidiana, memória contextual, conversa familiar e conhecimento útil, mantendo operações críticas determinísticas.

Princípios permanentes:

1. Core funcional é autoridade;
2. texto natural e botões convivem;
3. comentário não precisa virar produtividade;
4. problemas podem gerar sugestões, nunca escrita silenciosa;
5. ambiguidade de escrita exige confirmação;
6. não inventar presença, conclusão, treino, gasto, compromisso ou memória;
7. cada usuário possui dados, memória e contexto isolados;
8. conhecimento global pertence à Library, não à memória pessoal;
9. Library/background são extras opcionais;
10. exemplos novos alimentam domínios reutilizáveis, não `if`s individuais.

## 2. Arquitetura oficial de linguagem

A `main` usa Cloudflare Worker + Telegram webhook + D1. Não há LLM externa ativa.

Fluxo oficial:

```text
mensagem
→ Context Router + Intent Parser
→ Core funcional
→ memória/contexto pessoal
→ sugestões confirmáveis
→ Library opcional
→ NLU/conversa/fallback
```

Hierarquia obrigatória:

```text
Core > contexto explícito atual > memória > Library > conversa genérica
```

`context_router.py` classifica domínio, tier, formato, confiança, intenção, alvo e pista temporal. `intent_parser.py` reconhece famílias de intenção. Domínios protegidos incluem matérias/aulas/provas/faltas, tarefas, compromissos/agenda, mercado, musculação, finanças, metas e rotinas.

Regressão proibida: após falar de receita, `queria faltar essa aula de Sistemas Digitais I` jamais pode ser tratado como ingrediente ausente.

## 3. Contexto recente — concluído

`context_memory.py` mantém memória operacional curta por `user_id`, limitada aos poucos tópicos mais recentes. A tabela possui migration D1 `0004_conversation_context.sql` e também está no guard de schema.

`context_sync.py` registra mudanças explícitas e cria barreiras contra contextos opcionais antigos. `library_context_bridge.py` conecta os handlers da Library à mesma memória curta central.

Objetivo prático:

```text
receita de carbonara
não tenho bacon
```

mantém continuidade, mas:

```text
receita de carbonara
queria faltar Sistemas Digitais
```

muda imediatamente para acadêmico. Contexto antigo nunca tem autoridade sobre uma mudança explícita de assunto.

## 4. Memória pessoal — concluída nesta fase

Memória determinística continua oficial e isolada por `user_id`.

Entidades estruturadas: pets, familiares, amigos/colegas, relacionamentos, veículos e objetos. `personal_profile.py` acrescenta fatos explícitos de preferência: gostos, desgostos, preferências, time e cidade.

`o que você sabe sobre mim?` reúne o mapa pessoal conhecido sem preencher lacunas por inferência.

Regras:

- salvar apenas relações/fatos explicitamente comunicados;
- permitir correção/exclusão;
- não misturar usuários;
- memória pessoal não sequestra entidade cultural composta (`Jake` × `Jake Peralta`).

## 5. Linguagem natural — concluída como camada estrutural

`knowledge/portuguese_conversation.py` é background não respondente. `language_context.py` normaliza fala informal. `intent_parser.py` extrai intenção + domínio + alvo + tempo quando houver sinal suficiente.

Famílias atuais cobrem acadêmico, tarefas/lembretes, mercado, agenda/compromissos, musculação, finanças, rotinas e consultas principais da Library.

Exemplo de convergência:

```text
segunda eu não vou pra Sistemas
segunda quero faltar Sistemas
vou matar Sistemas segunda
```

→ mesma família de ausência acadêmica. Validação e escrita continuam no módulo funcional correspondente.

## 6. Política conversa × ação × sugestão — concluída

`action_policy.py` formaliza:

```text
comentário → conversa
pedido explícito → ação pelo Core
problema/necessidade → ajuda + possível sugestão
ação implícita/derivada → confirmação antes de escrita
```

Exemplo consolidado:

- `comprar café` / `bota café na lista` → comando de mercado;
- `acabou o café` / `tô sem café` → problema; Butler oferece salvar e espera confirmação;
- `tô cansado` → conversa, não tarefa automática.

`grocery_phrase_patch.py` foi ajustado para não gravar relatos de falta doméstica como se fossem comandos.

## 7. Sugestões transversais — concluídas como mecanismo

`suggestion_engine.py` centraliza sugestões genéricas e usa estado por usuário. Escritas confirmadas passam por `core_actions.py`.

Fluxos atuais incluem:

- item doméstico acabou → sugerir mercado;
- pet conhecido sem ração → resolver pet pela memória e sugerir mercado;
- ingrediente ausente → sugerir mercado;
- série longa → sugerir rotina;
- duas provas próximas/no mesmo dia → sugerir plano acadêmico.

`study_plan_flow.py` tornou o fluxo de duas provas multiusuário: recebe data, identifica duas matérias do próprio usuário, apresenta proposta e, após confirmação, cadastra provas ausentes e distribui tarefas de teoria/resumo, exercícios e revisão.

Nenhuma dessas sugestões deve gravar dados antes da confirmação quando nasceu de comentário/problema.

## 8. Gateway do Core

`core_actions.py` centraliza escritas disparadas por camadas auxiliares:

- adicionar itens de mercado;
- criar rotina;
- criar tarefa.

`butler_library.py`, contexto de pets e suggestion engine foram migrados para esse gateway. A regra `Library sugere, Core escreve` agora existe no código, não só na documentação.

## 9. Butler Library — consolidada como acervo orientado a dados

Library é conhecimento global compartilhado e opcional.

`knowledge/library_manifest.py` documenta os acervos. `library_index.py` normaliza jogos, filmes/séries/personagens, livros e filosofia em records pesquisáveis por nome, aliases, tags, gênero, autor, resumo e metadados. `library_catalog_handler.py` oferece fallback genérico para variações que não justificam lógica própria.

Acervos atuais:

- culinária estruturada por áreas/livros, incluindo cozinha brasileira tradicional e cortes;
- jogos + Pokémon FireRed;
- filmes/séries/cultura pop;
- livros/filosofia;
- português informal como background não respondente.

Culinária inclui massas, carnes, salgados, arroz/feijão, legumes, saladas, frango, doces, moquecas, vatapá, baião de dois, acarajé, bobó, feijão tropeiro, galinhada, barreado, cuscuz, caruru, vaca atolada e conhecimento de cortes/preparações bovinas.

Direção: novos conhecimentos entram preferencialmente como dados, tags, aliases ou documentos pesquisáveis. O motor não deve crescer um `if` por exemplo.

Direitos autorais: preferir domínio público, dados abertos/licenciados, documentos próprios e resumos/metadados; não armazenar indiscriminadamente obras comerciais completas.

## 10. Core funcional preservado

Continuam soberanos: tarefas, compromissos, agenda, pendências, matérias/grade, provas/faltas, lembretes, lista de itens faltando, metas/streaks, rotinas, finanças e musculação.

Tarefa vencida não concluída = pendência. Agenda reutiliza fontes reais. Aulas são previstas, não presença presumida. Escritas ambíguas confirmam alvo.

Acadêmico mantém matérias, horários/locais, grade textual, faltas e provas. Sem OCR/Tesseract; correção manual tem prioridade.

Musculação pessoal mantém protocolo de 12 semanas iniciado por `🚀 Começar os trabalhos`, com exercício, substitutos, série/carga/repetições/faltas/evolução. Usuário genérico cadastra treino próprio.

Finanças permanecem simples: entradas, saídas, categorias, relatório mensal, saldo, comparação e alertas básicos.

## 11. Personalidade e cotidiano

Butler aceita saudação, agradecimento, risada, cansaço, fome, desânimo e comentários sem tentar transformar tudo em tarefa. Tom: familiaridade/parceria, humor e gíria quando cabem.

Sarcasmo comportamental só usa histórico real; primeira ocorrência não vira hábito inventado. Day-off reduz cobranças e é isolado por usuário.

## 12. Regressão automática — concluída

Arquivos principais:

```text
cloudflare/tests/test_context_router.py
cloudflare/tests/test_library_index.py
.github/workflows/butler-regression.yml
```

`pyproject.toml` possui configuração de pytest. GitHub Actions compila `cloudflare/src` e executa a suíte a cada alteração relevante.

A suíte cobre dezenas de formulações de acadêmico, tarefas, mercado, agenda, musculação, finanças, rotina, culinária, jogos, livros, filmes/séries, cultura e conversa.

O próprio CI já encontrou uma colisão real: busca de livros recebia resultados irrelevantes para `oi butler` porque o bônus de domínio era aplicado sem evidência semântica. `library_index.py` foi corrigido para exigir match antes de aplicar bônus.

Testes futuros devem priorizar sequências completas e dois `chat_id` diferentes para validar isolamento.

## 13. Experimento LLM — decisão preservada

Workers AI foi testada como camada de linguagem/persona/memória/sugestão, mantendo Core determinístico, mas apresentou integração/fallback/latência inadequados. Foi removida da `main`.

Preservação:

- `archive/llm-experiment` — laboratório;
- `backup/nlu-only` — referência pré-LLM.

Possibilidade futura: LLM local/privada em serviço/container, somente para linguagem/contexto. Core valida ações; memória oficial pertence ao Butler; nenhuma escrita direta pelo modelo.

## 14. As sete prioridades de refinamento — estado final desta etapa

1. **estabilidade do Core** — tiers e gateway de escrita implementados;
2. **roteamento/contexto** — router central, parser estrutural, memória curta e invalidação implementados;
3. **memória pessoal** — entidades + perfil explícito + consulta agregada implementados;
4. **linguagem natural** — normalização informal e famílias intenção/alvo/tempo implementadas;
5. **sugestões inteligentes** — política problema×ação e engine confirmável implementadas;
6. **Library** — manifesto, índice comum, fallback data-driven e ponte de contexto implementados;
7. **qualidade antes de novas features** — regressão pytest + GitHub Actions implementados.

Essa fase está encerrada como arquitetura de refinamento. O próximo trabalho deve ser **testar conversa real, ampliar cobertura e corrigir arestas**, não criar outra camada paralela.

## 15. Regra de continuidade

Ao concluir etapas futuras: atualizar este arquivo e README quando a capacidade pública mudar; registrar decisões técnicas; não apagar decisões históricas sem substituição explícita; e manter claro que Library/background enriquecem, enquanto Core governa.
