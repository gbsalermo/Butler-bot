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

Fluxo conceitual oficial:

```text
mensagem
→ Context Router
→ Core funcional
→ memória pessoal
→ Library opcional
→ NLU/conversa/fallback
```

Hierarquia obrigatória: `Core > contexto explícito atual > memória > Library > conversa genérica`.

`context_router.py` centraliza classificação de domínio/tier/formato. Domínios protegidos incluem matérias/aulas/provas/faltas, tarefas, compromissos/agenda, mercado, musculação, finanças, metas e rotinas. Acervos não implementam autoridade concorrente.

Regressão proibida: após falar de receita, `queria faltar essa aula de Sistemas Digitais I` jamais pode ser tratado como ingrediente ausente.

## 3. Contexto recente

`context_memory.py` fornece memória operacional curta, por usuário, limitada a poucos tópicos. É diferente da memória pessoal permanente.

Serve para resolver follow-ups como `não tenho bacon` após carbonara e `quero assistir ela toda` após uma série, sem deixar assunto antigo perseguir o usuário. A mensagem atual sempre pode invalidar/despriorizar contexto anterior.

## 4. Memória pessoal

Memória determinística continua oficial e isolada por `user_id`. Entidades atuais: pets, familiares, amigos/colegas, relacionamentos, veículos e objetos.

Direção: formar mapa pessoal estruturado e incremental, não armazenar conversa indiscriminadamente. Conflito pessoal × cultura: `Jake` pode ser pet conhecido; `Jake Peralta` deve permanecer cultura pop.

## 5. Linguagem natural

`knowledge/portuguese_conversation.py` é background linguístico não respondente. `language_context.py` normaliza fala informal. `context_router.py` usa essa normalização.

A NLU deve evoluir por intenção + alvo + tempo, não por frases mágicas. Formulações semanticamente equivalentes devem convergir para o mesmo Core, por exemplo `segunda eu não vou pra Sistemas`, `segunda quero faltar SD1` e `acho que vou matar Sistemas segunda` → ausência acadêmica + matéria + data.

## 6. Política de ação e sugestão

`action_policy.py` formaliza:

```text
comentário → conversa
pedido explícito → ação pelo Core
problema/necessidade → ajuda + possível sugestão
ação implícita/derivada → confirmação antes de escrita
```

Sugestões são transversais: pet sem ração → mercado; ingrediente ausente → mercado; série longa → rotina; duas provas próximas → futuramente plano de estudo. Library nunca executa regra de negócio própria.

## 7. Butler Library

Library é conhecimento global compartilhado e opcional. `knowledge/library_manifest.py` documenta acervos e regra de expansão.

Acervos atuais: culinária estruturada por áreas/livros (incluindo cozinha brasileira tradicional e cortes), jogos + Pokémon FireRed, filmes/séries/cultura pop, livros/filosofia e português informal como background não respondente.

Culinária inclui massas, carnes, salgados, arroz/feijão, legumes, saladas, frango, doces, moquecas, vatapá, baião de dois, acarajé, bobó, tropeiro, galinhada, barreado, cuscuz, caruru, vaca atolada e conhecimento de cortes/preparações bovinas.

Direção arquitetural: conteúdo deve migrar progressivamente para dados estruturados/documentos pesquisáveis, separado do mecanismo. O motor deve permanecer pequeno. Preferir domínio público, dados abertos/licenciados, documentos próprios e resumos/metadados; não armazenar indiscriminadamente obras comerciais completas.

## 8. Core funcional preservado

Continuam soberanos: tarefas, compromissos, agenda, pendências, matérias/grade, provas/faltas, lembretes, lista de itens faltando, metas/streaks, rotinas, finanças e musculação.

Tarefa vencida não concluída = pendência. Agenda reutiliza fontes reais. Aulas são previstas, não presença presumida. Escritas ambíguas confirmam alvo. Mercado é lista persistente do que falta em casa; Library pode sugerir item, nunca gravar silenciosamente.

Acadêmico mantém matérias, horários/locais, grade textual, faltas e provas. Sem OCR/Tesseract; correção manual tem prioridade.

Musculação pessoal mantém protocolo de 12 semanas iniciado por `🚀 Começar os trabalhos`, com exercício, substitutos, série/carga/repetições/faltas/evolução. Usuário genérico cadastra treino próprio.

Finanças permanecem simples: entradas, saídas, categorias, relatório mensal, saldo, comparação e alertas básicos.

## 9. Personalidade e cotidiano

Butler aceita saudação, agradecimento, risada, cansaço, fome, desânimo e comentários sem tentar transformar tudo em tarefa. Tom: familiaridade/parceria, humor e gíria quando cabem. Sarcasmo comportamental só usa histórico real; primeira ocorrência não vira hábito inventado. Day-off reduz cobranças e é isolado por usuário.

## 10. Testes de conversa

`cloudflare/tests/test_context_router.py` inicia testes automatizados de roteamento e política de ação. A suíte deve crescer para 50–100 cenários reais misturando domínios e sequências.

Casos prioritários:

```text
qual minha aula segunda?
quero faltar ela
quantas faltas tenho?

receita de carbonara
não tenho bacon
deixa
segunda tenho prova?

tenho um gato chamado Jake
Jake tá sem ração
pode colocar
```

Também testar dois `chat_id` para provar isolamento de memória/contexto.

## 11. Experimento LLM

Workers AI foi testada como camada de linguagem/persona/memória/sugestão, mantendo Core determinístico, mas apresentou integração/fallback/latência inadequados. Foi removida da `main`.

Preservação: `archive/llm-experiment` (laboratório) e `backup/nlu-only` (referência pré-LLM).

Possibilidade futura: LLM local/privada em serviço/container, somente para linguagem/contexto. Core valida ações; memória oficial pertence ao Butler; nenhuma escrita direta pelo modelo.

## 12. Prioridade de desenvolvimento

Ordem oficial atual:

1. estabilidade do Core;
2. roteamento e contexto;
3. memória pessoal;
4. linguagem natural;
5. sugestões inteligentes;
6. Library;
7. novas funcionalidades.

Não adicionar grande módulo novo enquanto conflitos entre essas camadas ainda estiverem sendo encontrados.

## 13. Estado desta consolidação

Implementado na `main` nesta etapa:

- roteador central determinístico (`context_router.py`);
- contexto recente curto (`context_memory.py`);
- política central de ação/sugestão (`action_policy.py`);
- manifesto data-driven da Library (`knowledge/library_manifest.py`);
- dispatcher reorganizado em tiers;
- testes iniciais de roteamento entre domínios;
- README e continuidade alinhados.

Esta é a fundação das sete prioridades. Memória, NLU e testes devem continuar sendo ampliados incrementalmente sobre esses contratos, sem reescrever o Core inteiro de uma vez.

## 14. Regra de continuidade

Ao concluir etapas futuras: atualizar este arquivo e README quando a capacidade pública mudar; registrar decisões técnicas; não apagar decisões históricas sem substituição explícita; e manter claro que Library/background enriquecem, enquanto Core governa.
