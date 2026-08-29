# Butler — Trilha Definitiva de Desenvolvimento

**Roadmap mestre de evolução do produto e da arquitetura**  
**Versão:** 1.1  
**Data-base:** 29/08/2026  
**Status:** oficial para as próximas fases de desenvolvimento

> Este documento define **para onde o Butler deve evoluir e em qual ordem**. Ele não substitui `docs/ARCHITECTURE.md` como fonte de verdade do runtime atual. Sempre que houver divergência entre este roadmap e o código ativo, a arquitetura de produção deve ser conferida antes da implementação.

---

## 1. Visão do Butler

O Butler deve evoluir para ser um **assistente pessoal de verdade**, centrado em Telegram, capaz de organizar cotidiano, estudo, universidade, projetos, trabalho, hábitos e interesses sem virar apenas um menu de CRUDs nem uma IA imprevisível.

A meta não é responder qualquer coisa. A meta é **conhecer o estado real da vida operacional do usuário e ajudá-lo a agir sobre ele**.

O Butler ideal deve conseguir responder perguntas como:

- “O que eu tenho hoje?”
- “O que ficou de ontem?”
- “Onde eu parei no SGL?”
- “Qual é a próxima coisa mais importante?”
- “O que eu preciso estudar no curso de inglês hoje?”
- “Essa matéria mudou de horário, ajusta aí.”
- “Não vou conseguir treinar hoje porque vou viajar.”
- “Amanhã tenho aula, mas depois quero trabalhar no Aconchega Aí e à noite estudar inglês.”
- “Anota isso para eu organizar depois.”
- “Quero estudar Cálculo agora: limites, derivadas e integrais.”
- “Em que tópico da sessão de estudo eu estou?”

A experiência desejada é a de um **assistente confiável, familiar e útil**, não de um chatbot que tenta transformar toda frase em tarefa.

---

## 2. Princípios não negociáveis

Estes princípios valem para todas as etapas.

1. **Core determinístico:** ações críticas não dependem de interpretação ampla ou imprevisível.
2. **Ação explícita vence contexto antigo:** uma mudança clara de assunto deve ser respeitada imediatamente.
3. **Não inventar fatos:** presença, conclusão, gasto, treino, progresso, compromisso, prioridade ou memória só existem quando há dado real ou regra explícita.
4. **Multiusuário por padrão:** toda informação pessoal deve permanecer isolada por usuário.
5. **Confirmação para escrita derivada:** quando a ação nasceu de inferência ou sugestão, confirmar antes de persistir.
6. **Texto natural e botões convivem:** nenhum deles deve ser obrigatório em todos os fluxos.
7. **Uma autoridade por domínio:** cada área do Butler deve ter um módulo claramente responsável pelo comportamento final.
8. **Migration é fonte formal de schema:** `ensure_schema()` é defesa operacional, não substituto da evolução formal do D1.
9. **Toda expansão exige regressão:** feature nova sem cobertura cria dívida imediatamente.
10. **Não criar patch por reflexo:** antes de um novo `*_fix.py`, verificar se a regra pode entrar no módulo autoritativo.
11. **Contexto auxilia, não governa:** memória e Library nunca podem sequestrar ações críticas.
12. **Documentação acompanha comportamento:** capacidade ativa, decisão arquitetural e roadmap devem estar claramente separados.

---

## 3. Estado atual que este roadmap assume

A produção atual roda em:

```text
Telegram
→ webhook
→ Cloudflare Python Worker
→ dispatcher em cloudflare/src/entry.py
→ handlers operacionais
→ D1 / Durable Objects / Telegram Bot API
```

O runtime antigo em `src/` usa polling/SQLite e não é a produção principal.

O Core atual já possui, em diferentes níveis de maturidade:

- tarefas, pendências e agenda;
- compromissos e lembretes;
- matérias, provas, presença e faltas;
- importação de grade do SIGAA;
- rotinas e metas;
- lista do que está faltando em casa;
- musculação, séries, cargas e progresso;
- Ler/Ver Depois;
- Day-off;
- resumos matinal e semanal;
- clima integrado à agenda/resumo;
- isolamento multiusuário;
- diagnósticos administrativos e avisos do proprietário;
- código preservado de contexto, memória, sugestões e Butler Library que não deve ser reativado indiscriminadamente.

A arquitetura atual acumulou handlers, integrações e patches ao longo da evolução. Por isso, a primeira etapa deste roadmap foi deliberadamente uma fase de **arrumação estrutural**.

---

# 4. Roadmap oficial

```text
ETAPA 0  🧹 Arrumar a casa
         revisão geral + limpeza + Dossiê Mestre
             ↓
ETAPA 1  🗣️ Linguagem natural + estabilidade de conversa
             ↓
ETAPA 2  🎓 Acadêmico completo + importação robusta
             ↓
ETAPA 3  ⏱️ Auxiliar de Estudos / Modo Estudo
             ↓
ETAPA 4  📚 Cursos e trilhas de estudo
             ↓
ETAPA 5  📥 Caixa de entrada / captura rápida
             ↓
ETAPA 6  🗂️ Projetos e trabalho
             ↓
ETAPA 7  🧭 Resumo, contexto operacional e priorização
             ↓
ETAPA 8  🧠 Reativação seletiva de memória, sugestões e Library
             ↓
ETAPA 9  🔒 Hardening e consolidação de longo prazo
```

**Status atual:** Etapa 0 concluída. Próxima fase oficial: **Etapa 1 — Linguagem natural + estabilidade de conversa real**.

### Regra de avanço

Não avançar uma etapa apenas porque “a feature principal funciona”. Cada etapa possui **critérios de saída**. Se o gate não foi atendido, a fase continua aberta.

Correções urgentes de produção podem ocorrer a qualquer momento, mas não devem ser usadas como desculpa para abandonar a ordem estrutural.

---

# ETAPA 0 — 🧹 Arrumar a casa antes de decorar

## 0.1 Objetivo

Transformar a `main` em uma base compreensível, auditável e segura para receber novas funcionalidades grandes.

A etapa não existe para “refatorar por estética”. Ela existe para reduzir risco operacional, remover duplicidade e deixar claro **quem manda em cada comportamento**.

## 0.2 Inventário completo do repositório

Mapear:

- diretórios;
- arquivos Python;
- migrations;
- testes;
- documentação;
- workflows;
- assets;
- runtime legado;
- módulos preservados;
- arquivos que substituem símbolos via `install()`;
- tabelas criadas somente em runtime;
- callbacks;
- schedulers;
- handlers de mensagens;
- funções administrativas.

Cada componente deve receber uma classificação:

| Classificação | Significado | Ação esperada |
|---|---|---|
| **ATIVO** | alcançado pelo runtime atual | preservar e documentar |
| **LEGADO NECESSÁRIO** | antigo, mas ainda usado por compatibilidade | isolar e planejar remoção futura |
| **PRESERVADO** | referência/experimento útil, fora do runtime | manter identificado e fora do caminho crítico |
| **DUPLICADO** | mesma responsabilidade em mais de um lugar | escolher autoridade e consolidar |
| **OBSOLETO** | não serve ao runtime nem como referência útil | preparar remoção |
| **REMOVÍVEL** | seguro apagar após testes | excluir em PR específico |

**Regra:** nenhum arquivo é apagado apenas pelo nome parecer antigo.

## 0.3 Mapa do dispatcher real

Produzir um mapa atualizado de:

```text
mensagem Telegram
→ callback ou message
→ handler 1
→ handler 2
→ ...
→ fallback
```

Para cada handler:

- quais frases/estados pode consumir;
- precedência;
- tabelas que lê/escreve;
- se pode enviar mensagem;
- se altera estado guiado;
- se cria contexto;
- se interfere com outro domínio.

O mesmo deve ser feito para cron e Durable Objects.

## 0.4 Consolidar módulos autoritativos

Meta: cada domínio deve ter uma resposta objetiva para:

> “Qual arquivo é a autoridade deste comportamento?”

Domínios mínimos:

- menus;
- tarefas;
- compromissos;
- lembretes;
- acadêmico;
- presença;
- rotinas;
- metas;
- mercado;
- musculação;
- clima;
- resumos;
- Ler/Ver Depois;
- administração;
- navegação global;
- contexto operacional.

Quando existirem múltiplas fontes concorrentes, consolidar progressivamente, com PRs pequenos.

## 0.5 Política única de menus

Eliminar fontes concorrentes de teclado/menu sempre que possível.

O sistema deve possuir:

- menu principal autoritativo;
- submenus declarados por domínio;
- botão Voltar consistente;
- Cancelar ação consistente;
- Day-off em posição deliberada;
- nenhum menu “fantasma” vindo de patch antigo.

## 0.6 Política única de lembretes

Documentar e consolidar:

- tarefa com horário;
- compromisso;
- lembrete pessoal simples;
- aula;
- rotina;
- resumo matinal;
- resumo semanal;
- alertas futuros de curso/projeto.

Para cada tipo:

```text
fonte do dado
horário do disparo
janela de tolerância
idempotência
respeito ao Day-off
confirmação de entrega
retry/falha
```

## 0.7 Banco e migrations

Auditar:

- todas as migrations;
- tabelas reais utilizadas;
- tabelas preservadas;
- colunas sem uso;
- `ensure_schema()` espalhados;
- backfills necessários para usuários antigos;
- índices úteis;
- integridade referencial;
- estratégia de backup/recuperação.

Nenhuma tabela nova futura deve existir apenas “porque o módulo cria se faltar” sem migration correspondente.

## 0.8 Testes do dispatcher de produção

Criar testes de integração com fakes que percorram a cadeia real do dispatcher, não apenas funções isoladas.

Cenários obrigatórios:

- handler correto vence o incorreto;
- mudança explícita de assunto;
- botão e texto natural equivalentes;
- dois usuários simultâneos;
- callback repetido;
- estado guiado cancelado;
- Telegram retorna falha;
- cron reexecutado;
- item já notificado;
- usuário antigo após migration;
- usuário novo.

## 0.9 Dossiê Mestre

Criar `docs/BUTLER_DOSSIE_MESTRE.md` contendo:

1. visão do produto;
2. arquitetura de produção;
3. mapa do dispatcher;
4. mapa de domínios;
5. banco e migrations;
6. schedulers e alarmes;
7. contexto e linguagem;
8. multiusuário;
9. recursos exclusivos do proprietário;
10. funcionalidades ativas;
11. código preservado/desativado;
12. dívida técnica;
13. convenções de desenvolvimento;
14. fluxo de deploy/teste;
15. roadmap oficial.

## 0.10 Entregáveis

- inventário completo;
- matriz ativo/legado/preservado/duplicado/obsoleto/removível;
- Dossiê Mestre;
- `ARCHITECTURE.md` atualizado;
- `CONTINUIDADE.md` simplificado para decisões duradouras;
- README coerente;
- lista de dívida técnica priorizada;
- patches duplicados reduzidos;
- testes ponta a ponta do dispatcher.

## Gate de saída da Etapa 0

A etapa só encerra quando:

- [x] todo arquivo relevante possui papel conhecido;
- [x] não há dúvida sobre a autoridade dos principais domínios;
- [x] código removido foi protegido por regressão;
- [x] menus e lembretes possuem política documentada;
- [x] migrations representam o schema formal conhecido;
- [x] fluxo de webhook e cron possui teste de integração mínimo;
- [x] Dossiê Mestre existe e reflete a `main`;
- [x] nenhuma regressão funcional conhecida foi introduzida.

**Encerrada em 29/08/2026**, após merge da PR #9 e regressão pós-merge verde na `main`.

---

# ETAPA 1 — 🗣️ Linguagem natural + estabilidade de conversa real

## 1.1 Objetivo

Aumentar drasticamente o repertório do Butler em português brasileiro sem reativar uma NLU ampla, opaca e propensa a falsos positivos.

A linguagem deve ser tratada como **estrutura**, não como uma coleção crescente de frases decoradas.

## 1.2 Modelo de interpretação desejado

Quando possível, uma expressão deve ser decomposta em:

```text
AÇÃO
ALVO
TEMPO
QUALIFICADORES
RELAÇÕES
CONTEXTO
NÍVEL DE CONFIANÇA
```

Exemplo:

> “Amanhã depois da aula me lembra de comprar café.”

```text
AÇÃO: lembrar
ALVO: comprar café
TEMPO: amanhã
RELAÇÃO TEMPORAL: depois da aula
```

## 1.3 Conjunções e conectivos

Cobertura prioritária:

- e;
- mas;
- porém;
- só que;
- porque;
- então;
- se;
- quando;
- enquanto;
- antes;
- depois;
- assim que;
- até;
- caso;
- embora;
- além disso.

A conjunção define uma **relação**, não necessariamente uma segunda ação.

Exemplos:

> “Não vou treinar porque estou viajando.”

`viajando` explica o motivo. Não deve virar compromisso automaticamente.

> “Tenho aula às 10 e depois quero trabalhar no front.”

Aqui existem dois blocos operacionais relacionados no tempo.

> “Quero treinar, mas tenho aula às 18h.”

Contraste não autoriza cancelar, mover ou criar nada sem pedido explícito.

## 1.4 Frases compostas e múltiplas intenções

O Butler deve conseguir segmentar mensagens como:

> “Amanhã tenho aula de cálculo, mas depois quero mexer no SGL e às 21h estudar inglês.”

Em blocos semanticamente independentes:

```text
acadêmico → aula de cálculo
projeto/tarefa → trabalhar no SGL
curso/rotina → inglês às 21h
```

### Regra de segurança

Se um bloco for claro e outro ambíguo, não rejeitar tudo nem executar tudo cegamente. Confirmar somente o trecho incerto quando possível.

## 1.5 Conjugações e formas coloquiais

Famílias a cobrir:

```text
me lembre
me lembra
lembra de
não deixa eu esquecer
pode me lembrar
queria que lembrasse
preciso lembrar
bota um aviso
me avisa
```

O mesmo vale para:

- criar/adicionar/anotar;
- mover/adiar/postergar/deixar para;
- concluir/terminei/fiz/já foi;
- cancelar/apagar/tirar/remover;
- faltar/não ir/matar aula;
- treinar/fazer academia/ir para academia.

## 1.6 Referências e elipse

Cobrir:

```text
essa
isso
ela
a anterior
a outra
essa também
aquela de amanhã
muda pra sexta
deixa essa
cancela a primeira
```

O contexto deve possuir:

- domínio;
- entidade candidata;
- timestamp;
- barreira de mudança de assunto;
- expiração adequada.

## 1.7 Correção e auto-reparo conversacional

Exemplo:

```text
Usuário: marca dentista amanhã às 15
Usuário: não, 16h
```

O segundo turno deve corrigir o item recém-criado/proposto, não criar um compromisso novo.

Outros padrões:

- “quis dizer terça”;
- “não essa, a outra”;
- “volta”;
- “cancela isso”;
- “deixa como tava”.

## 1.8 Negação

A negação precisa ter escopo correto.

> “Não me lembra de estudar hoje.”

não é igual a:

> “Me lembra de não estudar hoje.”

> “Não vou para a aula.”

não significa “remover aula”.

## 1.9 Corpus real de português brasileiro

Criar um corpus versionado de testes com pelo menos:

- 100 frases simples;
- 100 frases com conjunções;
- 50 frases com referência contextual;
- 50 correções/negações;
- 50 múltiplas intenções;
- 50 falsos positivos deliberados;
- sequências de 3 a 8 turnos;
- casos com dois usuários.

O corpus deve crescer com erros reais encontrados em produção.

## 1.10 O que NÃO fazer

- não reativar `intent_parser.py` globalmente apenas porque existe;
- não usar fuzzy match agressivo para tudo;
- não transformar comentário em ação;
- não criar centenas de `if "frase" in text` sem abstração;
- não permitir que Library influencie intenção crítica.

## Gate de saída da Etapa 1

- [ ] principais conjunções cobertas estruturalmente;
- [ ] mensagens compostas segmentadas com segurança;
- [ ] referências curtas funcionam em sequências reais;
- [ ] correção do turno anterior funciona;
- [ ] corpus de regressão consolidado;
- [ ] dois usuários não compartilham contexto;
- [ ] falsos positivos permanecem baixos;
- [ ] Core continua sendo a autoridade de escrita.

---

# ETAPA 2 — 🎓 Acadêmico completo + importação robusta

## 2.1 Objetivo

Transformar o domínio acadêmico em uma base sólida, editável e reutilizável para futuras importações de grades, para alimentar o Auxiliar de Estudos e, depois, a Etapa 4 de cursos.

## 2.2 Edição completa de matérias

Uma matéria deve poder ser editada sem remover e recriar.

Campos previstos:

- nome;
- código opcional;
- professor opcional;
- local/sala;
- status ativa/trancada;
- múltiplos horários;
- dia da semana;
- início/fim;
- carga horária;
- limite de faltas;
- observações.

### Exemplo

```text
Sistemas Digitais

Segunda
10:00–11:50 · Pavilhão II / Sala 14

Quarta
08:00–09:50 · Laboratório 3
```

## 2.3 Modelo acadêmico

Direção conceitual:

```text
Matéria
 ├─ horários[]
 ├─ avaliações[]
 ├─ trabalhos[]
 ├─ aulas previstas[]
 ├─ registros de presença/falta[]
 └─ observações
```

Presença continua explícita; aula prevista não implica presença.

## 2.4 Importação como pipeline

Nunca fazer “parser → banco” diretamente.

```text
fonte externa
→ adaptador
→ estrutura normalizada
→ validação
→ prévia
→ correção manual
→ confirmação
→ persistência
```

## 2.5 Adaptador SIGAA

O SIGAA permanece como primeiro adaptador oficial.

Formato recomendado atual:

```text
Componente Curricular | Local | Horário
```

O importador deve:

- aceitar PDF textual e TXT;
- entender códigos de horário do SIGAA;
- detectar múltiplos horários da mesma matéria;
- apresentar prévia;
- permitir correção antes de gravar;
- rejeitar ambiguidades perigosas;
- não depender de OCR.

## 2.6 Motor reutilizável

Separar:

```text
parser SIGAA
≠
modelo acadêmico interno
```

Isso permitirá futuramente:

- outro portal acadêmico;
- CSV;
- texto copiado;
- grade manual estruturada;
- importação de cursos.

## 2.7 Onboarding acadêmico

No primeiro acesso:

- explicar formatos aceitos;
- mostrar formato recomendado;
- explicar que print/foto não é suportado;
- oferecer cadastro manual;
- permitir pular a importação;
- não bloquear uso geral do Butler.

## Gate de saída da Etapa 2

- [ ] matéria editável integralmente;
- [ ] múltiplos horários sem duplicação artificial;
- [ ] SIGAA passa por pipeline com prévia;
- [ ] parser separado do domínio interno;
- [ ] importação não grava sem confirmação;
- [ ] presença permanece explícita;
- [ ] onboarding documentado e testado.

---

# ETAPA 3 — ⏱️ Auxiliar de Estudos / Modo Estudo

## 3.1 Objetivo

Criar um **modo ativo de estudo acompanhado pelo Butler**, no qual o usuário informa os tópicos/conteúdos que pretende estudar e o Butler conduz a sessão em ciclos de foco e descanso, acompanha o tópico atual e registra o progresso real.

A ideia central é combinar a disciplina de um Pomodoro com o contexto do Butler, sem transformar tempo decorrido em progresso fictício.

O Butler deve ser capaz de acompanhar uma sessão como:

```text
Matéria: Cálculo I
Tópicos:
1. Limites
2. Derivadas
3. Integrais

Modo: 25 min foco / 5 min pausa
```

E manter **Limites** como tópico atual por quantos ciclos forem necessários, até o usuário declarar explicitamente que concluiu.

## 3.2 Diferença entre Auxiliar de Estudos e Cursos

Esses domínios são relacionados, mas diferentes:

```text
Auxiliar de Estudos
= controla a sessão ativa de foco, pausa, tópico atual e check-ins

Cursos e Trilhas
= controla a estrutura de longo prazo, módulos, conteúdos e progresso do curso
```

A Etapa 3 deve funcionar **sozinha**, com tópicos digitados manualmente.

Depois, na Etapa 4, cursos poderão alimentar automaticamente a fila do Modo Estudo. O domínio acadêmico também poderá sugerir tópicos associados a uma matéria, prova ou trabalho, mas a sessão continua sob controle explícito do usuário.

## 3.3 Criação da sessão

Fluxos desejados:

```text
modo estudo
quero estudar agora
começar estudo
vou estudar Cálculo
```

O Butler pede ou interpreta:

1. assunto/matéria opcional;
2. lista ordenada de tópicos;
3. duração do foco;
4. duração da pausa;
5. regra de pausa longa, se habilitada.

Exemplo de entrada natural:

> “Vou estudar cálculo agora: limites, derivadas e integrais. Faz 25 de estudo e 5 de pausa.”

Prévia:

```text
📚 Sessão de estudo

1. Limites
2. Derivadas
3. Integrais

⏱️ Foco: 25 min
☕ Pausa: 5 min

[▶️ Começar]
[✏️ Ajustar]
[❌ Cancelar]
```

O padrão inicial pode ser 25/5, mas o usuário deve poder escolher tempos como 50/10, 40/5 ou outros valores razoáveis.

## 3.4 Estrutura conceitual

Modelo mínimo desejado:

```text
StudySession
- user_id
- título/contexto opcional
- source_type/source_id opcional
- status
- focus_minutes
- break_minutes
- long_break_minutes opcional
- cycles_before_long_break opcional
- current_topic_id
- started_at
- paused_at
- finished_at

StudyTopic
- session_id
- position
- title
- status
- started_at
- completed_at

StudyCycle
- session_id
- topic_id
- cycle_type: focus | break | long_break
- planned_minutes
- started_at
- ended_at
- status
```

O schema real pode variar, mas precisa preservar histórico suficiente para responder quanto tempo foi estudado, em qual tópico e quantos ciclos foram realizados.

## 3.5 Ciclo de foco e descanso

O funcionamento esperado é:

```text
▶️ iniciar sessão
↓
📚 foco no tópico atual
↓
⏰ fim do bloco de foco
↓
☕ iniciar/avisar pausa
↓
⏰ fim da pausa
↓
📚 voltar ao estudo
```

O Butler envia alertas claros nas transições.

Exemplo ao iniciar:

```text
📚 Foco: Limites
⏱️ 25 minutos.

Agora é Limites. Te chamo quando for hora de parar um pouco.
```

Fim do foco:

```text
⏰ Bloco concluído.
☕ Hora de descansar por 5 minutos.

Como foi com “Limites”?

[✅ Terminei o tópico]
[➡️ Ainda estou nele]
[⏸️ Pausar sessão]
```

Fim da pausa, se o tópico não foi concluído:

```text
📚 Voltando.
Continuamos em “Limites”.
⏱️ Próximo bloco: 25 min.
```

## 3.6 Regra central: tempo não conclui tópico

Esta é uma **invariante do domínio**:

> **O Butler só avança para o próximo tópico quando o usuário disser explicitamente que concluiu o tópico atual.**

Portanto:

```text
25 min em Limites
→ usuário não concluiu
→ pausa
→ próximo bloco continua em Limites
```

Mesmo que sejam necessários três, quatro ou dez ciclos, o ponteiro não avança sozinho.

Formas de conclusão aceitas futuramente:

```text
terminei
terminei limites
concluí esse tópico
esse já foi
pode passar pro próximo
```

ou botão:

```text
[✅ Terminei o tópico]
```

A linguagem natural da Etapa 1 deve ajudar a reconhecer essas variações sem tornar a conclusão ambígua.

## 3.7 Avanço e tópico seguinte

Ao concluir explicitamente:

```text
✅ Limites concluído.

Próximo: Derivadas.

[▶️ Começar agora]
[☕ Fazer uma pausa]
[⏸️ Pausar sessão]
```

O Butler pode sugerir o próximo tópico, mas não deve marcar que ele foi iniciado até o novo bloco realmente começar.

Quando o último tópico for concluído:

```text
🎉 Sessão concluída.

✅ Limites
✅ Derivadas
✅ Integrais

Foco total: 1h40
Pausas: 20 min
Ciclos de foco: 4
```

## 3.8 Check-ins e acompanhamento

O Butler deve perguntar “como está?” principalmente em **pontos naturais da sessão**, não no meio de um bloco sem motivo.

Check-ins prioritários:

- ao fim de cada bloco de foco;
- após pausa longa;
- quando a sessão fica pausada por muito tempo e o usuário retorna;
- ao encerrar a sessão;
- opcionalmente após vários ciclos no mesmo tópico.

Respostas possíveis:

```text
✅ terminei
➡️ continuo nele
😵 não estou rendendo
⏸️ quero pausar
🛑 encerrar por hoje
```

“Não estou rendendo” não deve marcar fracasso nem conclusão. Pode oferecer aumentar a pausa, encerrar ou continuar com outro bloco, sempre com decisão do usuário.

## 3.9 Pausar, retomar e encerrar

A sessão deve sobreviver a interrupções.

Comandos naturais:

```text
pausa o estudo
vou parar um pouco
voltar a estudar
continuar estudo
encerrar por hoje
```

Ao retomar:

```text
📚 Sessão retomada.
Tópico atual: Limites
Ciclos concluídos nesse tópico: 2

[▶️ Continuar]
```

Encerrar a sessão antes de concluir todos os tópicos **não deve descartá-los**. O resumo deve separar:

```text
concluídos
pendentes
parcialmente estudados
```

Uma sessão futura pode reutilizar os tópicos pendentes mediante confirmação.

## 3.10 Temporização confiável

O timer não pode depender de um `sleep()` mantido em memória.

O mecanismo deve:

- sobreviver a reinício do Worker;
- persistir estado;
- evitar alerta duplicado;
- tolerar retry;
- confirmar entrega pelo Telegram quando relevante;
- manter isolamento por usuário;
- permitir cancelamento/pausa do próximo alarme.

A implementação deve reutilizar a infraestrutura temporal já existente quando adequado, como Durable Objects/alarmes persistentes, ou criar um componente autoritativo específico para estudo se isso reduzir acoplamento.

## 3.11 Pausa longa

Opcionalmente suportar estilo Pomodoro clássico:

```text
4 ciclos de foco
→ pausa longa de 15–30 min
```

Isso deve ser configurável. O Butler não precisa obrigar pausa longa para quem prefere apenas ciclos simples.

## 3.12 Integrações futuras

### Acadêmico

Uma matéria/prova pode originar uma sessão:

```text
estudar para prova de Física
→ selecionar/definir tópicos
→ abrir Modo Estudo
```

### Cursos e trilhas

Na Etapa 4:

```text
Curso de Inglês
Próximo conteúdo: Simple Past
→ Estudar agora
→ Modo Estudo recebe o conteúdo
```

Concluir o tópico durante o Modo Estudo só deverá atualizar o progresso do curso quando a integração possuir vínculo explícito e regra testada.

### Resumo diário/semanal

Futuramente os resumos podem mostrar dados reais como:

```text
📚 Estudo hoje: 1h50
• Cálculo — Limites concluído
• Derivadas — 2 ciclos, ainda pendente
```

## 3.13 UX mínima

Menu sugerido:

```text
📚 Modo Estudo

[▶️ Começar estudo]
[⏸️ Sessão ativa]
[📋 Tópicos]
[📊 Histórico]
[⚙️ Temporizador]
[🏠 Menu principal]
```

Durante sessão ativa, priorizar botões contextuais:

```text
[✅ Terminei o tópico]
[➡️ Continuar nele]
[⏸️ Pausar]
[🛑 Encerrar]
```

Evitar exigir que o usuário redigite tópico, duração ou contexto já conhecidos.

## Gate de saída da Etapa 3

- [ ] criar sessão com múltiplos tópicos;
- [ ] iniciar, pausar, retomar e encerrar sessão;
- [ ] foco e pausa possuem alertas persistentes e idempotentes;
- [ ] duração de foco/pausa é configurável;
- [ ] Butler pergunta como foi nos pontos de transição;
- [ ] tópico atual não avança pelo simples fim do timer;
- [ ] avanço exige conclusão explícita;
- [ ] múltiplos ciclos podem ocorrer no mesmo tópico;
- [ ] histórico registra tempo e ciclos por tópico;
- [ ] interrupção/reinício não perde a sessão ativa;
- [ ] dois usuários podem estudar simultaneamente sem interferência;
- [ ] integração futura com acadêmico/cursos possui contrato claro, sem acoplamento prematuro.

---

# ETAPA 4 — 📚 Cursos e trilhas de estudo

## 4.1 Objetivo

Criar um domínio genérico para cursos de idiomas, programação, certificações e outras formações estruturadas.

Não criar uma feature exclusiva para inglês.

## 4.2 Estrutura

```text
Curso
→ Módulo/Etapa
   → Conteúdo/Submódulo
      → Materiais
      → Atividades
      → Progresso
```

Os nomes exibidos podem preservar a nomenclatura original da plataforma, mas o modelo interno deve permanecer genérico.

## 4.3 Tipos de curso

### Autogerido / gravado

O usuário define dias/horários de estudo. O Butler aponta para o **próximo conteúdo pendente**.

```text
segunda: 1.3 não concluído
terça: 1.3 reaparece
quarta: 1.3 concluído
quinta: 1.4
```

O tempo passar nunca marca conclusão.

### Ao vivo / calendário fixo

O curso possui aulas que acontecem independentemente do progresso anterior.

Conteúdo perdido pode gerar pendência/revisão, mas a grade ao vivo não deve ser deslocada automaticamente.

## 4.4 Estados de conteúdo

Mínimo:

```text
pendente
em andamento
concluído
pulado
```

Opcional futuro:

```text
revisar
bloqueado por pré-requisito
```

## 4.5 Conclusão em lote

Telegram deve permitir marcar vários itens e concluir juntos:

```text
☑ Aula — Alphabet
☑ Lista — Alphabet
☐ Solução — Alphabet

[✅ Concluir selecionados]
```

Cada item mantém histórico individual.

## 4.6 Importador de cursos

O importador deve reconhecer relações entre arquivos/conteúdos:

- vídeo + legenda = mesmo conteúdo com materiais diferentes;
- PDF associado à aula = material;
- lista de exercícios = atividade;
- solução/gabarito = solução/revisão;
- revisão = tipo explícito;
- títulos semelhantes só são fundidos com confiança suficiente.

Ambiguidade deve aparecer na prévia.

## 4.7 Integração com agenda

Autogerido:

```text
horário de estudo
→ mostra próximo conteúdo pendente
```

Ao vivo:

```text
horário fixo
→ mostra aula prevista daquele encontro
```

Não criar uma tarefa nova para cada sessão se o curso já possui progresso próprio.

## 4.8 Integração com o Modo Estudo

Cursos autogeridos devem poder abrir o Auxiliar de Estudos com o próximo conteúdo real já selecionado.

Exemplo:

```text
📚 Inglês
Próximo: Simple Past

[⏱️ Estudar agora]
```

Ao iniciar:

```text
Modo Estudo
→ tópico vinculado: Simple Past
→ ciclos de foco/pausa
→ usuário marca explicitamente que concluiu
→ progresso do curso pode ser atualizado pelo vínculo explícito
```

O fim de um Pomodoro nunca conclui conteúdo de curso por si só.

## Gate de saída da Etapa 4

- [ ] criar curso manualmente;
- [ ] módulos e conteúdos ordenados;
- [ ] progresso explícito;
- [ ] curso autogerido não avança sozinho;
- [ ] curso ao vivo respeita calendário;
- [ ] integração com Hoje/resumos;
- [ ] conclusão em lote;
- [ ] importação com prévia e heurísticas testadas;
- [ ] conteúdo de curso pode alimentar Modo Estudo sem duplicar progresso.

---

# ETAPA 5 — 📥 Caixa de entrada / captura rápida

## 5.1 Objetivo

Permitir capturar rapidamente algo sem obrigar o usuário a decidir imediatamente a categoria correta.

## 5.2 Princípio

Capturar agora, organizar depois.

Exemplos:

```text
anota aí: conferir documentação do Cloudflare
salva isso pra depois: pesquisar deploy do AkosMed
/inbox comprar cabo para o robô
```

## 5.3 Estrutura mínima

```text
InboxItem
- texto original
- data de captura
- origem/contexto opcional
- status
- categoria final opcional
```

## 5.4 Triagem

Ações possíveis:

- transformar em tarefa;
- compromisso;
- Ler/Ver Depois;
- item de mercado;
- item de projeto;
- nota;
- descartar.

Sugestão automática de categoria pode existir, mas nunca é obrigatória.

## 5.5 UX

```text
📥 Caixa de entrada

1. Conferir deploy do AkosMed
2. Comprar cabo para o robô
3. Ler documentação X

[✅ Tarefa] [📅 Compromisso]
[📌 Ler depois] [🗂 Projeto]
[🗑 Descartar]
```

## Gate de saída da Etapa 5

- [ ] captura em uma mensagem;
- [ ] nada é classificado silenciosamente de forma irreversível;
- [ ] triagem por botão e texto;
- [ ] conversão preserva texto/origem;
- [ ] itens processados não reaparecem como pendentes.

---

# ETAPA 6 — 🗂️ Projetos e trabalho

## 6.1 Objetivo

Dar ao Butler memória operacional estruturada sobre projetos e sessões de trabalho.

A pergunta central é:

> “Onde eu parei?”

## 6.2 Modelo de projeto

```text
Projeto
- nome
- descrição
- status
- prioridade
- próximo passo
- bloqueios
- links/referências
- marcos
- pendências
- sessões de trabalho
- última atualização
```

## 6.3 Estado operacional

O projeto deve conseguir responder:

```text
🗂 SGL

Estado atual:
Frontend de relatórios em desenvolvimento

Último trabalho:
Ajuste de scroll/responsividade

Próximo passo:
Finalizar relatório de resíduos

Bloqueios:
Nenhum
```

## 6.4 Sessões de trabalho

Fluxo desejado:

```text
começar SGL
→ Butler marca sessão ativa
→ opcionalmente mostra próximo passo

encerrar
→ pergunta o que foi feito
→ registra resultado
→ atualiza próximo passo/bloqueio
```

## 6.5 Integração com tarefas

Projeto não substitui tarefa.

```text
Projeto = contexto de longo prazo
Tarefa = ação executável
```

Uma tarefa pode pertencer a um projeto.

## 6.6 Perguntas naturais

- onde parei no SGL?
- o que falta no Aconchega Aí?
- qual foi a última coisa que fiz no RasComp?
- tenho projeto parado?
- qual o próximo passo do AkosMed?

## Gate de saída da Etapa 6

- [ ] projeto possui estado real persistente;
- [ ] tarefas podem ser vinculadas;
- [ ] sessões registram início/fim/resultado;
- [ ] “onde parei?” retorna dado verificável;
- [ ] bloqueios e próximo passo editáveis;
- [ ] nenhuma inferência de progresso sem registro.

---

# ETAPA 7 — 🧭 Resumo, contexto operacional e priorização

## 7.1 Objetivo

Fazer o Butler cruzar os domínios já confiáveis para ajudar o usuário a entender o dia e a semana.

Não é um “modelo decidindo a vida”. É uma camada de **priorização explicável**.

## 7.2 Fontes

- compromissos;
- tarefas;
- pendências;
- matérias/aulas;
- avaliações;
- sessões de estudo;
- cursos;
- rotinas;
- treino;
- projetos;
- clima;
- inbox;
- itens vencidos.

## 7.3 Perguntas-alvo

- como tá meu dia?
- o que tenho amanhã?
- o que ficou de ontem?
- o que é mais importante hoje?
- o que tenho essa semana?
- tenho conflito de horários?
- tem alguma coisa atrasada?
- quanto eu estudei hoje?

## 7.4 Política inicial de prioridade

A prioridade deve ser derivada de fatores explícitos:

```text
prazo imediato
> compromisso fixo
> atraso
> avaliação próxima
> prioridade manual
> dependência/bloqueio
> rotina planejada
> item sem prazo
```

A política deve ser configurável no futuro e nunca esconder itens menos prioritários.

## 7.5 Conflitos

Detectar:

- dois compromissos simultâneos;
- aula × compromisso;
- sessão planejada × prova próxima;
- rotinas incompatíveis no mesmo horário.

O Butler sugere ajuste; não move automaticamente sem pedido.

## 7.6 Exemplo de resumo

```text
🕴️ Hoje está moderado.

🔴 Prioridade
• Entregar relatório — 14:00

🟡 Depois
• SGL — finalizar relatório de resíduos
• Inglês — próximo conteúdo: Simple Past

📚 Estudo
• Cálculo — 1h15
• Limites concluído
• Derivadas ainda em andamento

🟢 Rotinas
• Água: 2/4
• Treino: peito

🌦️ Chance baixa de chuva à tarde.

Ficou de ontem:
• revisar endpoint X
```

## Gate de saída da Etapa 7

- [ ] resumo usa apenas fontes reais;
- [ ] prioridade tem justificativa reproduzível;
- [ ] conflitos detectados sem escrita automática;
- [ ] itens atrasados aparecem claramente;
- [ ] agenda, estudo, projetos e cursos não são duplicados artificialmente.

---

# ETAPA 8 — 🧠 Reativação seletiva de memória, sugestões e Library

## 8.1 Objetivo

Recuperar partes úteis da arquitetura preservada somente depois que o Core e a conversa estiverem estáveis.

A pergunta não é “como ligar tudo?”. É:

> “Qual capacidade melhora o Butler sem diminuir a previsibilidade?”

## 8.2 Memória pessoal

Pode guardar fatos explícitos como:

- preferências;
- pessoas/pets citados;
- hábitos declarados;
- cidade;
- gostos e desgostos.

Regras:

- explícito;
- corrigível;
- removível;
- isolado por usuário;
- não vira ação automaticamente.

## 8.3 Sugestões

Exemplo:

> “Quero assistir Supernatural.”

Butler pode perguntar:

> “Quer adicionar em Ler/Ver Depois?”

Mas não adiciona sem confirmação.

## 8.4 Library

Reativar, de forma data-driven, domínios como:

- culinária;
- jogos;
- filmes/séries;
- livros;
- filosofia;
- cultura geral selecionada.

Política:

```text
Library informa/sugere
Core persiste/executa
```

## 8.5 Critério para reativar um módulo preservado

Antes de ligar qualquer componente:

- definir posição no dispatcher;
- definir precedência;
- definir domínios protegidos;
- testar falsos positivos;
- validar isolamento;
- atualizar `/health`;
- atualizar arquitetura.

## Gate de saída da Etapa 8

- [ ] memória genérica não interfere em ações críticas;
- [ ] Library tem dispatcher controlado;
- [ ] sugestões exigem confirmação para escrita;
- [ ] módulos reativados possuem testes de precedência;
- [ ] `/health` reflete o estado real.

---

# ETAPA 9 — 🔒 Hardening e consolidação de longo prazo

## 9.1 Objetivo

Transformar o conjunto desenvolvido em uma base resistente a falhas, manutenção e crescimento futuro.

## 9.2 Idempotência

Testar:

- webhook duplicado;
- callback clicado duas vezes;
- cron repetido;
- retry após timeout;
- confirmação de envio incompleta;
- migrations reaplicadas onde aplicável;
- timer de estudo disparado/reprocessado duas vezes.

## 9.3 Falhas externas

O Butler deve degradar de forma segura quando:

- Telegram falha;
- Open-Meteo falha;
- D1 retorna erro;
- Durable Object falha;
- usuário bloqueia o bot;
- um scheduler falha mas os outros precisam continuar.

## 9.4 Dados e recuperação

Definir:

- export/backup do D1;
- restauração;
- retenção;
- migração de usuários antigos;
- validação de integridade;
- política para dados órfãos.

## 9.5 Segurança

- secrets fora do repositório;
- webhook secret recomendado;
- comandos administrativos restritos ao proprietário;
- callbacks administrativos não reutilizáveis;
- nenhuma exposição acidental de chat IDs/dados pessoais;
- configuração pessoal migrável para seed privado quando necessário.

## 9.6 Observabilidade

Padronizar logs por domínio:

```text
[weather]
[attendance]
[reminder]
[study]
[admin]
[project]
[course]
```

Registrar o suficiente para diagnosticar sem armazenar conteúdo pessoal desnecessário.

## 9.7 Teste de regressão final

Cobrir jornadas completas:

- onboarding → grade → aula → falta;
- tarefa → lembrete → conclusão;
- Modo Estudo → foco → pausa → continuar mesmo tópico → conclusão explícita → próximo tópico;
- curso → Modo Estudo → conclusão → próximo conteúdo;
- inbox → triagem → tarefa;
- projeto → sessão → onde parei;
- resumo diário com conflito;
- Day-off;
- dois usuários;
- proprietário × usuário comum.

## Gate de saída da Etapa 9

- [ ] principais jornadas ponta a ponta cobertas;
- [ ] política de backup definida;
- [ ] callbacks, timers e schedulers idempotentes;
- [ ] falhas externas degradam com segurança;
- [ ] documentação final sincronizada;
- [ ] dívida técnica residual registrada e priorizada.

---

# 5. Trilhas transversais obrigatórias

Alguns temas não pertencem a uma única etapa. Devem acompanhar o roadmap inteiro.

## 5.1 Multiusuário

Toda feature nova deve responder:

- qual `user_id` é autoridade?
- SQL está filtrado pelo usuário?
- callback contém informação suficiente para validar o dono?
- scheduler/timer pode misturar usuários?
- teste com dois usuários existe?

## 5.2 UX Telegram

Padrões desejados:

- botões inline para confirmação;
- teclado persistente apenas quando realmente útil;
- Voltar e Cancelar consistentes;
- evitar pedir que o usuário redigite informação já fornecida;
- prévia antes de importações e ações em lote;
- mensagens curtas para operação diária;
- detalhes sob demanda;
- em sessões temporizadas, botões contextuais devem refletir exatamente o estado atual.

## 5.3 Banco

Toda mudança persistente deve revisar:

- migration;
- compatibilidade com usuários existentes;
- índices;
- idempotência;
- exclusão/cascade;
- rollback lógico quando aplicável.

## 5.4 Testes

Cada bug real corrigido deve, sempre que possível, virar regressão.

Pirâmide desejada:

```text
muitos testes determinísticos de função
+ testes de domínio
+ testes do dispatcher
+ poucas jornadas ponta a ponta críticas
```

## 5.5 Documentação

Quando o comportamento ativo mudar:

- `docs/ARCHITECTURE.md`;
- README, se for capacidade pública;
- Dossiê Mestre, se alterar mapa estrutural;
- este roadmap, somente se mudar a direção/ordem da trilha.

---

# 6. Política de desenvolvimento por etapa

Cada fase deve seguir o mesmo ciclo:

```text
1. auditar estado atual
2. definir comportamento-alvo
3. definir casos de teste antes da expansão grande
4. implementar em branch pequena
5. testar
6. usar no Telegram real
7. registrar arestas encontradas
8. corrigir
9. atualizar documentação
10. só então fechar a etapa
```

## Definition of Done de uma feature

Uma feature não está concluída apenas quando “funciona no meu chat”. Ela precisa:

- funcionar no caminho de produção;
- respeitar multiusuário;
- possuir fallback/erro compreensível;
- não quebrar handlers anteriores;
- possuir teste adequado ao risco;
- ter schema formal quando necessário;
- ter documentação mínima;
- não depender de código morto para funcionar.

---

# 7. Política de prioridade para novas ideias

Durante o roadmap surgirão novas ideias. Elas devem ser classificadas:

### P0 — correção crítica

Perda de dados, envio errado, vazamento entre usuários, scheduler incorreto, duplicidade grave.

→ interrompe a etapa atual.

### P1 — regressão funcional importante

Feature existente deixou de funcionar ou fluxo central ficou inutilizável.

→ corrigir antes de avançar.

### P2 — melhoria da etapa atual

Aprimora diretamente o objetivo da fase.

→ pode entrar na etapa.

### P3 — feature futura

Boa ideia, mas pertence a outra etapa.

→ documentar no backlog da fase correta, não implementar agora.

### P4 — decoração

Mudança estética ou conveniência sem impacto relevante.

→ só entra se não desviar esforço estrutural.

---

# 8. O que fica deliberadamente fora deste roadmap por enquanto

Não é proibido para sempre; apenas não tem prioridade antes da base ficar madura.

- LLM generativa como núcleo de ações;
- aplicativo mobile próprio do Butler;
- dashboard web completo;
- comandos por voz;
- integrações externas numerosas;
- automação financeira avançada;
- catálogo massivo da Library;
- gamificação extensa;
- redes sociais;
- sincronização com dezenas de plataformas.

A regra é simples: **não aumentar a superfície antes de aumentar a confiabilidade.**

---

# 9. Indicadores de maturidade

O Butler estará evoluindo na direção certa se, ao longo das etapas:

1. diminuir o número de patches necessários para corrigir comportamento;
2. aumentar a cobertura de sequências reais de conversa;
3. reduzir falsos positivos de intenção;
4. permitir mais operações sem redigitação;
5. acompanhar sessões de estudo sem confundir tempo com conclusão;
6. responder “onde parei?” com informação real;
7. montar resumos usando fontes confiáveis;
8. manter zero vazamento entre usuários;
9. sobreviver melhor a falhas externas;
10. ter documentação suficiente para retomar o desenvolvimento sem reconstruir contexto do zero.

---

# 10. Marco de visão final

Ao concluir esta trilha, o Butler deve conseguir funcionar como uma camada organizada sobre a rotina do usuário:

```text
CAPTURA
“O que apareceu?”
        ↓
ORGANIZAÇÃO
“O que isso é?”
        ↓
CONTEXTO
“Com o que isso se relaciona?”
        ↓
EXECUÇÃO
“O que preciso fazer agora?”
        ↓
ACOMPANHAMENTO
“O que foi feito e onde parei?”
        ↓
REVISÃO
“O que ficou, mudou ou merece atenção?”
```

No domínio de estudos isso também significa:

```text
PLANEJAR TÓPICOS
→ FOCAR
→ DESCANSAR
→ CHECAR COMO FOI
→ CONTINUAR O MESMO TÓPICO OU CONCLUIR
→ SÓ ENTÃO AVANÇAR
```

A inteligência do Butler não será medida pela quantidade de respostas que consegue improvisar, mas pela capacidade de **manter uma representação confiável daquilo que o usuário realmente precisa acompanhar**.

---

# 11. Próximo passo oficial

A próxima fase é:

## **ETAPA 1 — Linguagem natural + estabilidade de conversa real**

Primeira entrega concreta:

> **Mapear o repertório atual de linguagem do runtime, criar o corpus-base de português brasileiro e definir a camada estrutural para conjunções, referências, correções e múltiplas intenções sem reativar uma NLU ampla.**

A Etapa 3 — Auxiliar de Estudos — permanece oficialmente posicionada **depois do Acadêmico + Importação e antes de Cursos e Trilhas**.

---

## Registro de manutenção deste roadmap

- **Documento:** Trilha Definitiva de Desenvolvimento do Butler
- **Versão inicial:** 1.0
- **Versão atual:** 1.1
- **Data-base:** 29/08/2026
- **Mudança 1.1:** inclusão da Etapa 3 — Auxiliar de Estudos / Modo Estudo e renumeração das etapas seguintes
- **Responsabilidade:** orientar ordem e critérios das próximas fases
- **Fonte de verdade do runtime:** `docs/ARCHITECTURE.md`
- **Fonte de decisões históricas:** `CONTINUIDADE.md`
- **Dossiê Mestre:** `docs/BUTLER_DOSSIE_MESTRE.md`

> Alterações neste roadmap devem representar mudança real de estratégia. Pequenos ajustes de implementação pertencem à documentação da etapa ou à arquitetura, não a este documento.
