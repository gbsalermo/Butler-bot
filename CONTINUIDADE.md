# Continuidade do desenvolvimento — Butler

## 1. Estado do projeto antes da migração

O Butler encerrou a principal fase funcional do **rolling local**. O próximo trabalho grande não deve ser adicionar novos módulos, e sim transportar o comportamento atual para produção no Cloudflare sem regressões.

Estado técnico atual:

- desenvolvimento concentrado na `main`;
- Python;
- `python-telegram-bot[job-queue]`;
- `python-dotenv`;
- SQLite;
- `pypdf` para PDFs textuais;
- execução local por polling;
- scheduler local via JobQueue;
- Butler pessoal: `Butler` / `@ButlerSal_BOT`;
- versão genérica em `src.main_generic`;
- linguagem natural determinística, sem LLM/API externa;
- próximo marco: **Cloudflare + webhook + D1/persistência compatível + scheduler compatível**.

## 2. Filosofia consolidada

O Butler é um assistente pessoal, não apenas um CRUD no Telegram.

Princípios que devem ser preservados em qualquer refatoração/migração:

1. ações frequentes devem exigir poucos passos;
2. botões continuam disponíveis, mas texto natural deve ser confortável;
3. personalidade é provocativa, sarcástica e favorável ao usuário, sem humilhação;
4. sarcasmo contextual deve nascer de fatos registrados, nunca de invenção;
5. quando uma intenção natural for ambígua, confirmar antes de alterar dados;
6. não inventar presença em aula, tarefa concluída, treino, gasto ou compromisso;
7. não prometer lembrete sem informação suficiente para executá-lo;
8. evitar complexidade que não entregue benefício cotidiano real;
9. manter módulos simples quando um controle sofisticado criaria mais atrito do que utilidade;
10. Day-off reduz/silencia cobranças e deve ser respeitado pelos agendamentos.

## 3. Menu principal atual

Ordem consolidada:

- `🌙 Day-off`
- `➕ Adicionar`
- `🗓️ Hoje`
- `🛒 Item faltando`
- `📚 Matérias`
- `🏠 Cotidiano`
- `🏋️ Musculação`

### Atalhos

`➕ Adicionar`:

- nova tarefa;
- novo compromisso.

`🛒 Item faltando`:

- adicionar item;
- listar itens faltando.

Tarefas/compromissos também ficam em Cotidiano.

**Pendência não é um tipo cadastrável.** É uma tarefa vencida e ainda não concluída.

## 4. Tarefas e compromissos

Fluxos foram encurtados para uso rápido.

Tarefa/compromisso por botão:

1. título;
2. Hoje / Outro dia / Sem data;
3. horário quando aplicável;
4. salvar.

Não perguntar observação/antecedência em sequência para o fluxo simples.

Regras:

- bloquear data passada;
- bloquear horário passado quando a data é hoje;
- tarefas podem ser concluídas;
- lembretes podem ser adiados;
- `postpone_count` registra quantos adiamentos ocorreram;
- remoção agora arquiva como `cancelado`, preservando histórico;
- tarefa vencida + não concluída = pendência.

Personalidade usa adiamentos e atraso real. Exemplo aprovado para conclusão atrasada:

> 😏 Feito. Demorou mais do que deveria, mas chegamos lá. Não vou estragar o momento.

## 5. Agenda

`🗓️ Hoje` reúne:

- aulas;
- horário/local;
- tarefas;
- compromissos;
- pendências vencidas;
- treino quando aplicável;
- quantidade de itens faltando.

Navegação disponível:

- amanhã;
- outra data (`DD/MM` ou `DD/MM/AAAA`);
- próximos 7 dias;
- histórico.

A agenda futura reutiliza as mesmas fontes de dados do resumo automático.

## 6. Histórico

### Histórico diário

Consulta uma data e reconstrói o que está registrado naquele dia:

- aulas previstas;
- tarefas/compromissos e status;
- rotinas registradas;
- academia quando houver registro.

Não afirmar que o usuário compareceu a uma aula apenas porque ela estava na grade; usar “aula prevista”.

### Histórico de tarefas

Separar:

- pendentes;
- concluídas;
- canceladas.

Itens apagados antes da mudança para arquivamento não podem ser reconstruídos.

## 7. Acadêmico

Funcionalidades:

- listar matérias;
- adicionar;
- remover;
- trancar;
- editar;
- horário/local persistentes;
- lembretes de aula;
- importação de grade.

### Importação

Aceitar:

- PDF com texto pesquisável;
- `.txt`.

Não usar OCR/Tesseract. Motivo: simplicidade e compatibilidade de hospedagem. Se o usuário só possuir imagem/PDF escaneado, orientar conversão externa para PDF textual ou `.txt`, ou cadastro manual.

### SIGAA

Conversão usa horas completas:

- `M23 = 08:00–10:00`;
- `M45 = 10:00–12:00`;
- `T23 = 14:00–16:00`;
- `T2345 = 14:00–18:00`;
- `N12 = 18:00–20:00`.

Correção manual tem prioridade.

No Butler pessoal, Laboratório de Sistemas Digitais I permanece manualmente em **segunda 14:00–16:00**, mesmo que o código importado sugira bloco maior.

## 8. Grade pessoal atual

- Álgebra Linear I — terça/quinta 10:00–12:00 — PAV III, Sala 10;
- Física II — segunda/quarta 10:00–12:00 — PAV III, Sala 07;
- Laboratório de Sistemas Digitais I — segunda 14:00–16:00 — PAV Eng., Sala D6;
- Princípios de Eletrônica Analógica — terça/quinta 08:00–10:00 — PAV I, Sala 104;
- Sistemas Digitais I — segunda 08:00–10:00 — PAV I, Sala 11;
- Sistemas Digitais I — quarta 08:00–10:00 — PAV I, Sala 114.

## 9. Casa / lista de mercado

A lista é persistente e representa coisas faltando em casa, não uma lista temporária criada para cada compra.

Cadastro rápido aceita:

- `sal`;
- `sal, açúcar, café`;
- `falta sal, açúcar, café`;
- `café | 2 pacotes`.

Quantidade é opcional.

Texto natural deve diferenciar compras domésticas de tarefas:

- `preciso comprar café` → item faltando;
- `preciso comprar arroz e feijão` → itens faltando;
- `preciso comprar um adaptador para o trabalho` → tarefa;
- `me lembra de comprar café amanhã às 18h` → tarefa/lembrete temporal.

`comprei o café` marca o item como comprado; confirmar se houver ambiguidade.

## 10. Day-off

Day-off representa folga/indisponibilidade e deve silenciar cobranças e agendamentos compatíveis.

Reativação por chamada ao Butler, mantendo sensação conversacional.

Na versão genérica, Day-off é isolado por `chat_id`.

## 11. Musculação — Butler pessoal

O protocolo interno possui 12 semanas.

Funcionalidades implementadas:

- `🚀 Começar os trabalhos` inicia oficialmente o protocolo;
- treino do dia/semana;
- exercícios;
- substitutos;
- série por série;
- carga;
- repetições;
- histórico/evolução de carga;
- falta com motivo;
- progresso semanal;
- reinício temporário para testes.

Decisão de UX: mensagens comuns não chamam isso de “Protocol Mass”; usar **treino na academia**.

Regra crítica: antes de `Começar os trabalhos`, treino não aparece nos resumos e uma frase de falta não deve criar falta no protocolo.

Versão genérica não recebe esse protocolo; musculação começa vazia e usa cadastro próprio.

## 12. Personalidade baseada em comportamento

Arquivos centrais:

- `personality.py`;
- `behavior_engine.py`;
- `natural_store.py` para eventos naturais úteis.

Contextos atualmente aproveitados:

- quantidade de adiamentos;
- conclusão atrasada/no prazo;
- streaks;
- faltas no treino;
- evolução de carga quando os valores são comparáveis;
- avisos recorrentes de atraso.

Emojis podem aparecer com moderação.

Regra importante: primeira ocorrência não vira “você sempre faz isso”. Ex.: primeiro aviso de atraso é caso isolado; somente reincidência dá munição para provocações como “não chega a ser novidade”.

## 13. Resumos automáticos

### Manhã

Default: **07:30**, configurável por `BUTLER_MORNING_SUMMARY_TIME`.

Pode conter:

- aulas do dia com horário/local;
- tarefas;
- compromissos;
- treino quando aplicável;
- mercado;
- fechamento curto do dia anterior quando houver algo relevante;
- tarefas que ficaram pendentes ontem.

Não existe mais fechamento automático noturno. Decisão tomada porque o usuário pode treinar/encerrar responsabilidades às 22h–23h e o resumo noturno poderia ocorrer antes do fim real do dia.

### Semanal

Default: domingo **20:00**, configurável.

Mostra de forma simples o que foi cumprido, o que ficou aberto e sinais de evolução nos registros disponíveis.

## 14. Metas e streaks

Escopo deliberadamente leve, estilo acompanhamento visual de sequência.

Categorias-base:

- Inglês;
- Programação;
- Água;
- Alimentação;
- Musculação.

`🎯 Metas → 🔥 Sequências` mostra:

- streak atual;
- recorde;
- total de dias;
- últimos 7 dias.

No Butler pessoal, musculação usa treinos concluídos reais para evitar marcação duplicada.

Não aprofundar em gamificação complexa antes de necessidade real.

## 15. Finanças

Escopo deliberadamente simples.

Implementado:

- entrada;
- saída/gasto;
- categoria;
- descrição opcional;
- relatório do mês;
- saldo baseado nos registros;
- comparação simples com mês anterior;
- limites predefinidos para algumas categorias;
- alertas de excesso;
- linguagem natural para registros simples.

Categorias-base:

- Alimentação;
- Transporte;
- Lazer;
- Compras;
- Renda;
- Outros.

O Butler deve lembrar que relatório financeiro só é tão confiável quanto os registros informados, inclusive com provocações sobre o trabalho chato de registrar movimentos.

Não adicionar agora:

- cartões;
- parcelas;
- investimentos;
- múltiplas contas;
- orçamento sofisticado.

## 16. Integração natural por texto — v1 concluída

Arquivos:

- `src/natural_language.py` — interpretação;
- `src/natural_handlers.py` — execução;
- `src/natural_store.py` — eventos comportamentais;
- `scripts/nlu_smoke.py` — smoke test crítico.

A camada é determinística, sem LLM externo, e chama os stores existentes.

### Intenções cobertas

#### Criar compromisso

- `Butler, amanhã tenho dentista às 15h`;
- `amanhã tenho dentista 15h`;
- `tenho dentista amanhã às 15:30`;
- `sexta tenho reunião 10h`;
- `dentista amanhã 15h`.

#### Criar tarefa/lembrete

- `amanhã preciso entregar o relatório às 18h`;
- `tenho que estudar física amanhã`;
- `preciso comprar um adaptador`;
- `anota uma tarefa: revisar álgebra`;
- `me lembra de ...` pede data/hora quando ausentes.

#### Mercado

- `preciso comprar café`;
- `preciso comprar arroz e feijão`;
- `falta sal, açúcar e café`;
- `bota café na lista de mercado`;
- `o que falta em casa?`;
- `comprei o café`.

#### Agenda

- `o que tenho amanhã?`;
- `o que tenho daqui a 3 dias?`;
- `o que tenho sexta?`;
- `como está minha agenda sexta?`;
- `o que tenho na próxima semana?`.

#### Pendências

- `quais tarefas estão atrasadas?`;
- `o que ficou pendente?`;
- `o que está atrasado?`.

#### Concluir tarefa

- `já fiz o relatório`;
- `terminei o trabalho`;
- `concluí revisar física`.

Busca entre tarefas pendentes e confirma quando houver mais de um alvo plausível.

#### Falta de treino

- `hoje não vou treinar porque estou cansado`;
- `não consigo treinar hoje`;
- `não vai dar pra treinar hoje`.

#### Atraso

- `vou me atrasar para o dentista`;
- `vou chegar atrasado na reunião`;
- `estou atrasado para a entrevista`.

Não altera horário. Registra `late_notice` para contexto futuro.

#### Finanças

- `gastei 35 com lanche`;
- `paguei 20 de uber`;
- `gastei 80 no mercado`;
- `recebi 540 de bolsa`;
- `entrou 200 de trabalho`;
- `quanto gastei esse mês?`;
- `quanto sobrou?`.

### Datas/horas reconhecidas

- hoje;
- amanhã;
- depois de amanhã;
- dias da semana;
- próxima sexta etc.;
- `DD/MM`;
- `DD/MM/AAAA`;
- daqui a N dias;
- `15h`;
- `15h30`;
- `15:30`;
- às 15h;
- por volta das 15h.

### Follow-up temporário

Se faltar uma informação como horário, `context.user_data` mantém temporariamente o contexto para a próxima mensagem. Reiniciar o processo pode descartar uma conversa incompleta; isso é aceitável nesta versão.

## 17. Multiusuário por chat_id

Existem dois modos de execução.

### Pessoal

`python -m src.main`

Usa `data/butler.db` e mantém os dados pessoais/grade/protocolo.

### Genérico

`python -m src.main_generic`

Regras:

- nasce sem grade pessoal;
- nasce sem protocolo pessoal;
- `/start` pergunta como o usuário quer ser chamado;
- cada chat é identificado pelo Telegram `chat_id`;
- `telegram_user_id` também é preservado quando aplicável;
- cada chat possui armazenamento isolado no rolling local;
- callbacks também precisam selecionar o escopo correto;
- scheduler percorre chats individualmente.

Rolling local atual:

- registro central em `data/butler_generic_registry.db`;
- bancos em `data/butler_generic_users/<chat_id>.db`.

Essa estratégia foi escolhida por simplicidade e pelo volume esperado ser muito pequeno (poucos usuários). **Não transportar os arquivos SQLite literalmente para Cloudflare.** Preservar a regra de identidade/isolamento e trocar a implementação de persistência.

## 18. Arquitetura funcional relevante

Principais responsabilidades:

- `database.py`: usuários/grade;
- `daily_store.py`: tarefas e compromissos;
- `home_store.py`: mercado, metas, rotinas, musculação genérica;
- `protocol_mass_store.py`: treino pessoal;
- `finance_store.py`: finanças;
- `assistant_state.py`: estado/Day-off;
- `scheduler.py`: agendamentos locais;
- `summary_engine.py`: resumos;
- `behavior_engine.py`: comportamento contextual;
- `personality.py`: personalidade;
- `natural_language.py`: NLU determinística;
- `natural_handlers.py`: ações por linguagem natural;
- `natural_store.py`: eventos naturais;
- `user_scope.py`: escopo multiusuário local.

Evitar duplicar regra entre botão e texto natural.

## 19. Smoke test da NLU

Rodar antes da migração:

```bash
python scripts/nlu_smoke.py
```

Esperado:

```text
NLU smoke OK
```

O teste inclui casos críticos de:

- compromisso;
- tarefa;
- agenda relativa;
- mercado;
- distinção `preciso comprar café` x compra não doméstica;
- falta de treino;
- atraso;
- finanças;
- data/horário passado.

## 20. Pente-fino obrigatório antes/depois da migração

Teste manual recomendado no Telegram:

- `/start` e nome preferido;
- menu principal completo;
- Day-off e reativação;
- criação por botão;
- criação natural em ordem `amanhã tenho...` e `tenho... amanhã`;
- horários `15h`, `15h30`, `15:30`;
- data passada/horário passado;
- compromisso sem hora + follow-up;
- agenda hoje/amanhã/outra data/7 dias;
- histórico diário;
- histórico de tarefas;
- duas tarefas semelhantes + `já fiz...`;
- dois compromissos semelhantes + `vou me atrasar...`;
- mercado por botão e texto;
- `preciso comprar café` → mercado;
- `preciso comprar adaptador para o trabalho` → tarefa;
- importar grade por `.txt`/PDF textual e revisar prévia;
- tradução SIGAA;
- treino antes/depois de `Começar os trabalhos`;
- falta de treino com motivo;
- série/carga/substituto;
- streaks;
- entrada/saída financeira;
- relatório financeiro;
- resumo matinal;
- fechamento semanal;
- dois chats distintos no modo genérico sem vazamento de dados.

## 21. Próxima grande etapa — Cloudflare

A migração deve priorizar **paridade funcional**, não novas features.

### Objetivos

1. revisar dependências incompatíveis com ambiente Cloudflare;
2. substituir polling por webhook do Telegram;
3. migrar SQLite para Cloudflare D1 ou persistência compatível;
4. preservar isolamento por `chat_id`;
5. adaptar scheduler/JobQueue para mecanismo Cloudflare;
6. preservar lembretes de tarefas/compromissos/aulas;
7. preservar resumo matinal e fechamento semanal;
8. configurar secrets sem expor token;
9. validar timezone corretamente;
10. executar smoke tests pessoais e multiusuário;
11. somente depois considerar produção estável.

### Regra de migração

Não redesenhar funcionalidades durante a migração salvo quando a plataforma exigir. Se uma abstração for necessária, criar adaptadores para persistência/agendamento mantendo as regras de domínio atuais.

### Pontos de atenção

- SQLite local não é persistência de produção no Worker;
- JobQueue/polling não devem ser assumidos como disponíveis;
- webhook precisa validar e processar updates do Telegram corretamente;
- scheduler deve conseguir enviar mensagens proativamente por `chat_id`;
- timezone dos resumos/lembretes deve permanecer coerente;
- PDFs textuais/importação precisam ser reavaliados conforme limites do runtime;
- manter versão pessoal e genérica sem duplicar projeto;
- dados pessoais existentes precisam de estratégia explícita de migração se forem levados ao D1.

## 22. Decisões que NÃO devem ser revertidas sem motivo

- Pendência é estado derivado, não categoria manual.
- Mercado persistente é memória do que falta em casa.
- Quantidade de item de mercado é opcional.
- Sem OCR/Tesseract.
- SIGAA usa blocos de horas completas.
- Laboratório pessoal permanece 14:00–16:00.
- Sem resumo automático noturno.
- Treino pessoal só começa após `Começar os trabalhos`.
- Mensagens comuns dizem “treino na academia”.
- Streaks são simples, não gamificação pesada.
- Finanças permanecem simples nesta fase.
- Personalidade contextual depende de comportamento real.
- Primeiro aviso de atraso não deve ser tratado como hábito.
- Linguagem natural confirma ambiguidade.
- `preciso comprar café` é mercado; compra não doméstica pode ser tarefa.
- `me lembra de...` sem data/hora deve pedir quando lembrar.
- Multiusuário é isolado por `chat_id`.
- Próxima etapa é infraestrutura Cloudflare, não expansão funcional.

## 23. Regra de continuidade

Ao concluir qualquer etapa futura:

1. atualizar este arquivo com decisões e estado técnico;
2. atualizar README quando capacidade pública/uso mudar;
3. registrar incompatibilidades encontradas na migração;
4. não apagar decisões históricas relevantes sem substituí-las explicitamente;
5. deixar sempre indicado o próximo passo técnico.

## 24. Experimento com LLM e retorno à NLU determinística — agosto/2026

Foi realizado um laboratório para usar LLM somente como camada de linguagem, personalidade, memória e sugestão de ações, mantendo o Core determinístico como autoridade sobre banco, regras e operações.

### Arquitetura testada

A proposta era:

- fast path determinístico primeiro;
- Cloudflare Workers AI somente para mensagens conversacionais não resolvidas;
- memória persistente no D1;
- LLM retornando resposta estruturada e propostas de ação;
- nenhuma escrita direta pela LLM;
- confirmação do usuário antes de qualquer alteração;
- NLU atual como fallback.

Foram testados binding `AI`, modelos do Workers AI, provider abstrato, parser de respostas, memória semântica e comando de diagnóstico.

### Resultado do laboratório

No ambiente de produção do Butler, a integração não se mostrou confiável nesta etapa. Mensagens conversacionais continuaram caindo no fallback determinístico e houve aumento de latência antes da resposta. Até o comando de diagnóstico da LLM não conseguiu atravessar corretamente o fluxo do bot.

Decisão: **retirar a LLM da `main` e voltar para NLU determinística/contextual como base oficial**. O experimento foi preservado na branch `archive/llm-experiment`. A versão pré-LLM permanece em `backup/nlu-only`.

### Direção atual: memória determinística

A ideia útil do experimento — memória persistente — permanece, mas sem modelo externo.

Novo módulo: `cloudflare/src/deterministic_memory.py`.

Objetivo inicial:

- reconhecer fatos explícitos sobre entidades pessoais;
- persistir relações no D1 usando `natural_events`;
- reutilizar essas relações em mensagens futuras;
- evitar pedir ao usuário para repetir contexto já informado.

Primeiro caso implementado: pets.

Exemplo esperado:

1. `tenho um gato chamado Jake e ele é laranja` → grava `Jake = gato`, com atributo `laranja` quando identificado;
2. mais tarde `Jake tá sem ração` → recupera Jake como gato, entende o contexto e propõe adicionar ração à lista;
3. a inclusão na lista continua exigindo confirmação (`pode`/`sim`), reaproveitando o fluxo existente de mercado/pet.

A memória deve crescer por domínios claros e estruturados (pets, pessoas recorrentes, preferências e relações úteis), não como tentativa de interpretar qualquer frase aberta.

### Correção contextual associada

O fallback emocional antigo tinha uma falha: o marcador curto `é` era normalizado para `e` e testado por substring, fazendo mensagens sem relação com o estado anterior serem tratadas como continuação emocional. Isso provocava respostas repetidas, como reciclar o contexto de tarefas concluídas ao dizer `ele tá lendo aqui`.

A `main` agora usa `companion_safe_fallback.py`: saudações e estados explícitos continuam funcionando, mas continuadores curtos como `é`, `sei lá` e `isso` só são aceitos quando correspondem à mensagem inteira.

### Possibilidade futura de LLM

LLM não está descartada definitivamente. Uma futura tentativa deve evitar depender da integração direta que falhou neste laboratório. Alternativas a avaliar quando houver infraestrutura própria:

- LLM local/privada executada junto ao servidor;
- serviço separado em container (ex.: Ollama ou runtime compatível) e acessado pelo Butler por uma interface interna;
- provider externo somente se tiver contrato/API estável e latência aceitável;
- manter sempre o Core determinístico como autoridade e a NLU/memória como fallback.

Se a abordagem local/containerizada for retomada, reutilizar os princípios do laboratório: LLM apenas para linguagem/contexto, memória externa pertencente ao Butler, ações validadas pelo Core e nenhuma escrita direta pelo modelo.
