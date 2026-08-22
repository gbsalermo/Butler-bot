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

## 16. Direção oficial até dezembro/2026

A meta até **31/12/2026** é transformar o Butler de um conjunto sólido de funcionalidades em um **assistente pessoal operacional**, capaz de ajudar de forma contínua em quatro áreas principais:

1. **Projetos e trabalho** — registrar projetos, estado atual, próximos passos, bloqueios e retomada de contexto;
2. **Estudos** — integrar matérias, aulas, frequência, provas, notas, tarefas, revisões e planejamento acadêmico;
3. **Vida cotidiana** — tarefas, compromissos, mercado, finanças, rotinas, metas, treino, leitura e entretenimento;
4. **Contexto pessoal** — entender como o dia/semana está organizado, resumir prioridades e sugerir ações sem tomar decisões silenciosas pelo usuário.

O Butler não deve virar uma IA genérica nem um sistema que tenta controlar cada aspecto da vida. O alvo é ser um **copiloto cotidiano confiável**, com memória suficiente para continuidade e Core determinístico para ações.

Perguntas que a evolução deve tornar naturais:

```text
como tá meu dia?
o que eu tenho essa semana?
onde eu parei no SGL?
o que falta fazer nesse projeto?
qual é a próxima coisa mais importante?
como estão minhas matérias?
quanto ainda posso faltar?
quanto preciso tirar na próxima prova?
o que ficou pendente de ontem?
o que está faltando em casa?
como foi meu treino nas últimas semanas?
quanto eu gastei esse mês?
```

A conversa deve ser o centro da experiência. Menus e botões continuam existindo como atalhos e ferramentas de segurança, não como a única forma de operar o sistema.

## 17. Roadmap sequencial de evolução

O desenvolvimento seguirá **uma etapa por vez**. Não iniciar a etapa seguinte enquanto a anterior não tiver critérios mínimos de aceite e regressão cobrindo os fluxos principais.

### Etapa 0 — Estabilidade de conversa real

**Prioridade imediata.** Antes das novas features, usar o Butler em situações reais e fechar as arestas da arquitetura atual.

Objetivos:

- testar sequências completas de conversa, não apenas mensagens isoladas;
- ampliar testes com dois ou mais usuários para garantir isolamento;
- identificar colisões entre acadêmico, tarefas, Library, mercado, rotina e conversa casual;
- garantir que contexto antigo nunca se sobreponha a intenção explícita nova;
- corrigir frases naturais que ainda caem em fallback ou domínio errado;
- manter Core e gateway como únicas autoridades de escrita.

**Concluída quando:** os fluxos atuais passarem por uso real sem regressões críticas e houver cobertura automática dos erros encontrados.

### Etapa 1 — Captura rápida + Caixa de Entrada

Criar uma forma de registrar algo imediatamente sem obrigar o usuário a navegar por menus ou decidir a categoria naquele momento.

Exemplos:

```text
comprar arroz
assistir Cowboy Bebop
estudar árvore AVL amanhã
ver aquela biblioteca Java depois
```

Quando a intenção estiver clara, o Butler envia diretamente ao Core correspondente. Quando não estiver clara, pode salvar na **Caixa de Entrada** ou pedir uma confirmação curta.

A Caixa de Entrada deve permitir:

- adicionar;
- listar;
- mover para tarefa, mercado, projeto, ler/ver depois ou outra categoria compatível;
- editar;
- remover.

**Concluída quando:** registrar pensamentos rápidos for mais simples por conversa do que por menu e nenhuma captura ambígua gerar escrita silenciosa incorreta.

### Etapa 2 — Projetos + “Onde parei?”

Projetos passam a ser uma entidade própria, diferente de tarefas soltas.

Cada projeto deve poder manter:

- nome;
- descrição curta;
- status;
- tarefas relacionadas;
- último ponto trabalhado;
- próxima ação;
- bloqueios;
- notas/contexto de retomada;
- data da última atividade.

Fluxos desejados:

```text
cria um projeto chamado SGL Frontend
onde parei no SGL?
parei por hoje no Butler
qual é o próximo passo do Busivs?
marca essa tarefa como parte do SGL
```

Ao encerrar uma sessão de trabalho, o Butler deve permitir salvar um checkpoint:

```text
Projeto: SGL Frontend
Último ponto: login funcionando
Falta: tratar token expirado
Próxima ação: implementar interceptor do Axios
```

**Concluída quando:** depois de dias sem abrir um projeto, o usuário conseguir retomá-lo sem precisar reconstruir manualmente o contexto.

### Etapa 3 — Prioridade + Central de contexto + resumo diário

Adicionar prioridade operacional sem transformar tudo em urgência.

Níveis iniciais:

```text
normal
importante
urgente
```

O Butler pode sugerir prioridade com base em prazo e contexto, mas deve preservar correção manual e evitar inferências exageradas.

Criar uma **Central de Contexto** capaz de agregar dados reais já existentes:

- compromissos do dia;
- aulas;
- tarefas e pendências;
- provas próximas;
- projetos ativos e próximos passos;
- treino planejado;
- itens relevantes de rotina.

Fluxos principais:

```text
como tá meu dia?
como tá minha semana?
o que eu preciso resolver hoje?
```

Adicionar dois rituais opcionais:

- **Bom dia, chefe** — resumo curto do dia;
- **Encerrar o expediente** — mostra concluído, pendente e próximos passos sem remarcar silenciosamente o que não foi feito.

**Concluída quando:** o Butler conseguir produzir um panorama útil usando apenas dados oficiais do Core, sem duplicar fontes ou inventar estado.

### Etapa 4 — Modo Universidade

Transformar o domínio acadêmico existente em um painel pessoal de acompanhamento.

Por matéria, integrar:

- horários e locais;
- frequência/faltas;
- avaliações;
- notas;
- fórmula de média quando cadastrada;
- tarefas e trabalhos;
- próximos prazos;
- revisões/planos de estudo.

Fluxos desejados:

```text
como estou em Estrutura de Dados?
quanto ainda posso faltar?
quanto preciso tirar na P2?
tenho alguma prova nas próximas duas semanas?
o que preciso estudar hoje?
```

Nunca presumir presença em aula. Frequência continua baseada apenas em registro explícito.

**Concluída quando:** for possível acompanhar uma disciplina do início ao fim do semestre sem precisar manter cálculos ou pendências acadêmicas fora do Butler.

### Etapa 5 — Sessões de projeto, estudo e trabalho

Criar acompanhamento de sessões de foco sem conflitar com `🚀 Começar os trabalhos`, que permanece reservado ao protocolo de musculação.

A sessão deve poder guardar:

- projeto ou matéria;
- objetivo da sessão;
- início/fim;
- resultado;
- bloqueio encontrado;
- próximo passo.

O Butler não precisa vigiar tempo constantemente. A prioridade é **continuidade**, não produtividade performática.

Exemplos:

```text
vou trabalhar no SGL agora
vou estudar Física por uma hora
terminei por hoje
salva onde parei
```

**Concluída quando:** sessões de trabalho/estudo atualizarem automaticamente o contexto de projeto ou matéria com confirmação adequada.

### Etapa 6 — Musculação com histórico de evolução

Aprofundar o protocolo já existente sem reescrevê-lo.

Adicionar consultas e comparações sobre:

- carga por exercício;
- repetições por série;
- evolução entre semanas;
- exercícios substituídos;
- treinos não realizados;
- histórico do ciclo de 12 semanas.

O Butler pode apontar tendências simples, mas não deve prescrever progressões arriscadas como verdade automática.

**Concluída quando:** o usuário conseguir comparar o desempenho atual com semanas anteriores e recuperar claramente o histórico de cada exercício.

### Etapa 7 — Finanças e cotidiano integrado

Manter finanças simples e úteis.

Evoluir para:

- registro rápido de gastos/entradas por linguagem natural;
- orçamento opcional por categoria;
- comparação com mês anterior;
- alertas simples de excesso;
- consulta de saldo e distribuição de gastos.

Integrar com cotidiano sem misturar dados financeiros com sugestões não solicitadas.

Também consolidar:

- lista de itens faltando;
- metas;
- rotinas;
- ler/ver depois;
- compromissos;
- pendências domésticas.

**Concluída quando:** o usuário conseguir consultar o estado básico da vida cotidiana sem abrir sistemas separados para pequenas informações recorrentes.

### Etapa 8 — Library pessoal, aprendizado e descobertas

Manter a Butler Library como conhecimento global, mas permitir um fluxo explícito de **salvar referência pessoal** quando fizer sentido.

Exemplo:

```text
me explica arquitetura hexagonal
salva isso pra eu revisar depois
```

A referência pessoal não deve copiar obras integrais nem contaminar conhecimento global compartilhado.

Evoluir recomendações usando apenas sinais reais disponíveis, por exemplo:

- itens salvos em ler/ver depois;
- preferências pessoais explícitas;
- Library;
- contexto pedido na conversa.

Fluxos:

```text
me recomenda um livro
quero jogar alguma coisa hoje
me sugere uma série curta
```

**Concluída quando:** recomendações forem úteis, explicáveis e baseadas em dados reais, sem fingir conhecer gostos que não foram informados.

### Etapa 9 — Modos pessoais e proatividade controlada

Evoluir o comportamento cotidiano para três estados claros:

```text
🟢 Trabalhando
🟡 Modo leve
🔴 Day Off
```

- **Trabalhando:** funcionamento normal;
- **Modo leve:** reduzir cobranças e destacar somente compromissos/prazos relevantes;
- **Day Off:** não gerar cobrança de produtividade, mantendo o Butler disponível quando chamado.

A proatividade deve continuar obedecendo a política atual:

```text
observar contexto → sugerir → usuário decide → Core escreve
```

Nunca:

```text
observar contexto → escrever silenciosamente
```

Personalidade pode variar conforme situação e histórico real, usando humor e familiaridade sem transformar todo erro ou atraso em julgamento.

**Concluída quando:** o Butler parecer atento ao contexto sem se tornar invasivo ou insistente.

### Etapa 10 — Fechamento Butler 2026

Dezembro deve priorizar consolidação, não uma corrida por novas funções.

Checklist final:

- revisar arquitetura e remover duplicações;
- ampliar regressão end-to-end;
- validar isolamento multiusuário;
- revisar migrations e guards de schema;
- revisar menus, cancelar/voltar e fluxos incompletos;
- revisar documentação pública e `README`;
- medir quais features realmente são usadas;
- corrigir inconsistências de linguagem natural;
- deixar backlog de 2027 separado do que pertence à versão estável de 2026.

O objetivo do fechamento é ter um Butler menor e confiável, se necessário, em vez de um Butler maior e imprevisível.

## 18. Ordem de execução até o fim de 2026

Janela de planejamento, ajustável conforme uso real:

```text
Agosto / início de setembro
→ Etapa 0 — estabilidade real
→ Etapa 1 — captura rápida + inbox

Setembro
→ Etapa 2 — projetos + onde parei

Outubro
→ Etapa 3 — central de contexto + resumo diário
→ Etapa 4 — modo universidade

Novembro
→ Etapa 5 — sessões de projeto/estudo/trabalho
→ Etapa 6 — histórico de musculação
→ Etapa 7 — cotidiano/finanças

Dezembro
→ Etapa 8 — Library pessoal/descobertas
→ Etapa 9 — modos e proatividade controlada
→ Etapa 10 — hardening e fechamento 2026
```

Datas são direção, não justificativa para pular testes. Se uma etapa revelar fragilidade estrutural, corrigir antes de avançar.

## 19. Protocolo para trabalharmos etapa por etapa

Para cada etapa futura:

1. revisar o comportamento atual relacionado;
2. definir fluxos de usuário antes de alterar código;
3. definir o modelo de dados mínimo necessário;
4. implementar sem criar camada paralela ao Core existente;
5. adicionar testes de intenção, contexto e escrita;
6. testar exemplos reais por conversa;
7. corrigir regressões encontradas;
8. atualizar `CONTINUIDADE.md` com estado e decisões;
9. atualizar `README` somente quando houver mudança pública relevante;
10. marcar explicitamente a etapa como concluída antes de iniciar a próxima.

Prioridade entre features da mesma etapa:

```text
confiabilidade > continuidade de contexto > simplicidade de uso > automação > quantidade de funções
```

## 20. Norte de produto

O Butler deve evoluir para reduzir três tipos de carga:

- **lembrar** — compromissos, tarefas, pendências, estado de projetos;
- **reconstruir contexto** — onde parei, o que falta, o que aconteceu antes;
- **organizar** — transformar informação solta em próximos passos úteis.

Ele não precisa substituir aplicativos especializados quando estes forem claramente melhores. O valor do Butler está em ser a camada cotidiana que conecta informações suficientes para responder:

> **“Chefe, é isso que importa agora, foi aqui que você parou e esse é o próximo passo.”**

Esse é o critério principal de produto para a evolução até o fim de 2026.
