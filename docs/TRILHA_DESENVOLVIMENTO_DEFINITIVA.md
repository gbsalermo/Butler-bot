# Butler — Trilha Definitiva de Desenvolvimento

**Roadmap mestre de evolução do produto e da arquitetura**  
**Versão:** 1.2  
**Data-base:** 31/08/2026  
**Status:** oficial  
**Fase atual:** **Etapa 1 — Linguagem natural + estabilidade de conversa real**  
**Subetapa atual:** **1.4 — Correção e auto-reparo conversacional**

> Este documento define **para onde o Butler deve evoluir e em qual ordem**. Ele não substitui `docs/ARCHITECTURE.md` como fonte de verdade do runtime nem `docs/STATUS_ATUAL.md` como snapshot de andamento.
>
> Se outra IA assumir o projeto, ela deve **continuar a etapa atual e respeitar os gates abaixo**, não criar outro roadmap.

---

# 1. Visão do Butler

O Butler deve evoluir para ser um **assistente pessoal de verdade**, centrado em Telegram, capaz de organizar cotidiano, estudo, universidade, projetos, trabalho, hábitos e interesses sem virar apenas um menu de CRUDs nem uma IA imprevisível.

A meta é conhecer o estado real da vida operacional do usuário e ajudá-lo a agir sobre ele.

Exemplos de experiência desejada:

```text
O que eu tenho hoje?
O que ficou de ontem?
Onde eu parei nesse projeto?
Essa matéria mudou de horário, ajusta aí.
Não vou conseguir treinar hoje porque vou viajar.
Anota isso para eu organizar depois.
Quero estudar Cálculo agora: limites, derivadas e integrais.
Qual é a próxima coisa realmente importante?
```

---

# 2. Princípios não negociáveis

1. **Core determinístico:** ações críticas não dependem de interpretação ampla ou imprevisível.
2. **Ação explícita vence contexto antigo:** mudança clara de assunto é respeitada imediatamente.
3. **Não inventar fatos:** presença, conclusão, gasto, treino, prioridade, compromisso ou progresso dependem de dado real/regra explícita.
4. **Multiusuário por padrão:** toda informação pessoal é isolada por usuário.
5. **Confirmação para escrita derivada:** inferência/sugestão não autoriza persistência silenciosa.
6. **Texto natural e botões convivem.**
7. **Uma autoridade por domínio:** evitar duas políticas concorrentes para a mesma obrigação.
8. **Migration é fonte formal do D1.**
9. **Toda expansão exige regressão.**
10. **Não criar patch por reflexo.**
11. **Contexto auxilia, não governa.**
12. **Documentação acompanha comportamento.**
13. **CI verde não prova deploy Cloudflare.**
14. **Uma etapa só avança quando o gate estiver fechado.**

---

# 3. Estado atual assumido pelo roadmap

Produção:

```text
Telegram
→ webhook
→ Cloudflare Python Worker
→ cloudflare/src/worker.py
→ cloudflare/src/entry.py
→ handlers operacionais
→ D1 / Durable Objects / Telegram Bot API
```

O runtime antigo em `src/` usa polling/SQLite e é histórico/preservado.

O Core já possui:

- tarefas, pendências, compromissos e lembretes;
- matérias, provas, presença e faltas;
- importação SIGAA por PDF textual/TXT;
- rotinas e metas;
- mercado/itens faltando;
- musculação e progresso;
- Ler/Ver Depois;
- Day-off;
- resumos matinal e semanal;
- clima;
- isolamento multiusuário;
- recursos administrativos do proprietário;
- redundância de scheduler via Durable Objects;
- linguagem natural operacional conservadora;
- contexto curto/referências;
- primeira fatia de auto-reparo temporal.

A arquitetura ampla antiga de NLU/memória/Library continua preservada, mas não está ligada como dispatcher central.

---

# 4. Roadmap oficial

```text
ETAPA 0  🧹 Arrumar a casa                         ✅ concluída
             ↓
ETAPA 1  🗣️ Linguagem natural + conversa real     🚧 em andamento
             ↓
ETAPA 2  🎓 Acadêmico completo + importação        ⏳
             ↓
ETAPA 3  ⏱️ Auxiliares de Tempo / Modo Estudo     ⏳
             ↓
ETAPA 4  📚 Cursos e trilhas de estudo             ⏳
             ↓
ETAPA 5  📥 Caixa de entrada                       ⏳
             ↓
ETAPA 6  🗂️ Projetos e trabalho                    ⏳
             ↓
ETAPA 7  🧭 Resumo/contexto/priorização             ⏳
             ↓
ETAPA 8  🧠 Memória + Library seletiva             ⏳
             ↓
ETAPA 9  🔒 Hardening                              ⏳
```

Correções urgentes de produção podem ocorrer a qualquer momento, mas não alteram automaticamente a etapa oficial.

---

# ETAPA 0 — 🧹 Arrumar a casa

**Status:** ✅ concluída em 29/08/2026.

## Objetivo

Transformar a `main` em base compreensível, auditável e segura antes de grandes expansões.

## Entregas consolidadas

- inventário estrutural;
- Dossiê Mestre;
- arquitetura documentada;
- dispatcher/callback/cron testáveis;
- menu principal com uma autoridade;
- lembretes de `daily_items` com uma autoridade;
- migrations formais alinhadas ao schema conhecido;
- código removido apenas com prova de desuso;
- documentação separando ativo/legado/preservado;
- política contra novos patches paralelos sem justificativa.

## Decisões posteriores que reforçam a Etapa 0

Após um incidente em 30/08, o scheduler ganhou redundância via Durable Objects, mantendo os dispatchers autoritativos e `notification_log` como barreira de duplicidade.

O caminho quente também recebeu otimizações de D1/latência sem alterar as autoridades de domínio.

---

# ETAPA 1 — 🗣️ Linguagem natural + estabilidade de conversa real

**Status:** 🚧 em andamento.

## Objetivo

Aumentar o repertório do Butler em português brasileiro sem religar uma NLU ampla, opaca e propensa a falsos positivos.

A linguagem deve ser tratada como **estrutura**, não como lista infinita de frases decoradas.

## Modelo desejado

Quando aplicável, decompor:

```text
AÇÃO
ALVO
TEMPO
QUALIFICADORES
RELAÇÕES
CONTEXTO
CONFIANÇA
```

Reconhecer esses elementos **não autoriza escrita sozinho**.

## Subetapas

### 1.1 — Auditoria da linguagem ativa

**Status:** ✅ concluída.

Entregas:

- mapa do que realmente alcança o dispatcher;
- primitivas iniciais;
- corpus versionado executável;
- regressões de negação/falso positivo.

Documento: `ETAPA_1_AUDITORIA_LINGUAGEM.md`.

### 1.2 — Base Linguística Comum

**Status:** ✅ concluída.

Entregas:

- `language_primitives.py`;
- famílias compartilhadas de lembrete, tarefa, compromisso e ações principais;
- polaridade explícita;
- remoção de criação duplicada de lembrete;
- separação entre reconhecimento e persistência.

Documento: `ETAPA_1_2_BASE_LINGUISTICA.md`.

### 1.3 — Referências + Contexto Curto

**Status:** ✅ concluída.

Entregas:

- `short_context.py` como autoridade;
- janela inicial de 30 minutos;
- isolamento por usuário;
- referências `essa/ela/a segunda/a anterior/...`;
- listas posicionais usando a ordem realmente mostrada;
- barreira de mudança explícita de assunto;
- contrato legado de `conversation_layer` redirecionado ao contexto curto;
- regressões de sequências e dois usuários.

Documento: `ETAPA_1_3_CONTEXTO_REFERENCIAS.md`.

### 1.4 — Correção e auto-reparo

**Status:** 🚧 em andamento.

Primeira fatia já mesclada:

```text
marca dentista amanhã às 15h
→ não, 16h
```

O mesmo registro é atualizado quando o contexto é seguro (`source=created/corrected`). Contexto de lista não é alterado silenciosamente.

Falta:

- `deixa como tava` com rollback seguro;
- correção explícita de título/alvo;
- correções em fluxo guiado quando aplicável;
- sequências maiores de 3–8 turnos;
- regressões adicionais de negação/referência.

Documento: `ETAPA_1_4_CORRECOES.md`.

### 1.5 — Mensagens compostas, conjunções e múltiplas intenções

**Próxima frente dentro da Etapa 1 após fechar a 1.4**, salvo correção de produção prioritária.

Cobertura estrutural desejada:

```text
e
mas
porém
só que
porque
então
se
quando
enquanto
antes
depois
assim que
até
caso
embora
além disso
```

Regra: conjunção descreve relação; não significa automaticamente uma segunda escrita.

Exemplo:

```text
Não vou treinar porque estou viajando.
```

`viajando` é motivo, não compromisso automático.

Mensagens com vários blocos devem ser segmentadas conservadoramente:

```text
Tenho aula às 10 e depois quero trabalhar no front.
```

Se um bloco for claro e outro ambíguo, executar/confirmar cada parte conforme sua confiança; não rejeitar tudo nem gravar tudo cegamente.

## Corpus da Etapa 1

Meta de consolidação:

- pelo menos 100 frases simples;
- 100 com conjunções;
- 50 com referência contextual;
- 50 correções/negações;
- 50 múltiplas intenções;
- 50 falsos positivos deliberados;
- sequências de 3–8 turnos;
- casos multiusuário.

O corpus deve crescer com erros reais de produção.

## Gate de saída da Etapa 1

- [ ] principais conjunções cobertas estruturalmente;
- [ ] mensagens compostas segmentadas com segurança;
- [x] referências curtas funcionam em sequências reais básicas;
- [x] contexto é isolado por usuário;
- [x] primeira fatia de correção do turno anterior funciona;
- [ ] 1.4 completa, incluindo rollback/título quando aplicável;
- [ ] corpus consolidado no volume/variedade necessários;
- [ ] sequências de 3–8 turnos ampliadas;
- [ ] falsos positivos permanecem baixos;
- [ ] Core continua sendo autoridade de escrita;
- [ ] regressão completa verde após fechamento do gate.

**Etapa 2 não começa antes desse gate.**

---

# ETAPA 2 — 🎓 Acadêmico completo + importação robusta

## Objetivo

Transformar o domínio acadêmico em base sólida, editável e reutilizável para futuras importações, Modo Estudo e Cursos.

## Escopo

### Edição completa de matéria

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

### Modelo acadêmico normalizado

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

### Importação como pipeline

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

Nunca `parser → banco` diretamente.

### SIGAA

Primeiro adaptador oficial.

Entrada recomendada:

```text
Componente Curricular | Local | Horário
```

Aceitar PDF com texto pesquisável e TXT, sem depender de OCR.

### Onboarding

- explicar formato aceito/recomendado;
- permitir cadastro manual;
- permitir pular importação;
- não bloquear o uso geral do Butler.

## Gate de saída

- [ ] matéria editável integralmente;
- [ ] múltiplos horários sem duplicação artificial;
- [ ] SIGAA usa pipeline com prévia;
- [ ] parser separado do modelo interno;
- [ ] importação não grava sem confirmação;
- [ ] presença continua explícita;
- [ ] onboarding documentado/testado;
- [ ] família acadêmica/presença consolidada o suficiente para ter autoridades claras.

---

# ETAPA 3 — ⏱️ Auxiliares de Tempo / Modo Estudo

## Objetivo

Criar serviços temporais ativos que acompanhem o usuário sem transformar tempo decorrido em progresso fictício.

Documento de apoio: `ETAPA_3_ASSISTENTES_DE_TEMPO.md`.

## 3A — Modo Estudo

Exemplo:

```text
Matéria: Cálculo I
Tópicos:
1. Limites
2. Derivadas
3. Integrais

Modo: 25 min foco / 5 min pausa
```

O Butler mantém `Limites` como tópico atual até conclusão/pulo explícito.

Fluxos naturais desejados:

```text
modo estudo
quero estudar agora
vou estudar cálculo: limites, derivadas e integrais
```

Regras:

- foco/pausa configuráveis;
- tópicos ordenados;
- conclusão explícita;
- pausa não conclui tópico;
- sessão pode pausar/cancelar;
- histórico registra o que realmente ocorreu.

## 3B — Assistente Geral de Tempo

A Etapa 1 já prepara linguagem como:

```text
daqui a 5 minutos
em 1 hora
cronometra 30 minutos
inicia um timer de 45 segundos
```

A Etapa 3 deve transformar isso em execução persistente confiável, usando o padrão temporal já consolidado do Butler.

## Gate de saída

- [ ] timers persistem sem depender de conversa aberta;
- [ ] idempotência de disparo;
- [ ] Modo Estudo acompanha tópico atual;
- [ ] conclusão é explícita;
- [ ] pausa/cancelamento seguros;
- [ ] Day-off/política temporal definidos;
- [ ] dois usuários isolados;
- [ ] regressão de reinício/rearme.

---

# ETAPA 4 — 📚 Cursos e trilhas de estudo

## Objetivo

Representar cursos de longo prazo e integrar seu próximo conteúdo ao cotidiano/Modo Estudo.

## Modelo conceitual

```text
Curso
→ módulos[]
   → conteúdos/submódulos[]
      → materiais[]
      → atividades[]
      → progresso
```

## Dois modos

### Curso autogerido

- próximo conteúdo permanece pendente até conclusão/pulo explícito;
- não avançar só porque passou o dia;
- Butler pode sugerir retomada.

### Curso ao vivo

- segue calendário fixo;
- aula perdida não desloca automaticamente o curso inteiro;
- faltas/pendências são registradas separadamente.

## Importação

O motor deve agrupar material relacionado antes de persistir:

- vídeo/aula;
- lista de exercícios;
- solução;
- revisão;
- PDF/material complementar.

Baixa confiança → prévia/confirmação.

## Relação com Ler/Ver Depois

A categoria `🎓 Cursos` já existe em Ler/Ver Depois como **captura simples**. Ela não é esta Etapa 4.

## Gate de saída

- [ ] estrutura Curso → Módulo → Conteúdo;
- [ ] progresso explícito;
- [ ] modos autogerido e ao vivo diferenciados;
- [ ] importação com prévia/confirmação;
- [ ] integração com Modo Estudo sem acoplamento rígido;
- [ ] histórico preservado ao editar conteúdo.

---

# ETAPA 5 — 📥 Caixa de entrada / captura rápida

## Objetivo

Permitir que o usuário capture algo sem decidir imediatamente se é tarefa, projeto, curso, ideia ou referência.

Exemplos:

```text
anota isso pra eu organizar depois
joga na inbox: revisar autenticação do SGL
```

## Regras

- captura rápida não força classificação;
- item pode ser processado depois;
- converter para tarefa/projeto/etc. exige ação explícita;
- Inbox não vira depósito invisível: deve aparecer em resumo/processamento periódico quando configurado.

## Gate de saída

- [ ] captura por botão e texto;
- [ ] listar/processar/arquivar;
- [ ] conversão segura para domínios;
- [ ] sem duplicação de item ao converter;
- [ ] isolamento multiusuário.

---

# ETAPA 6 — 🗂️ Projetos e trabalho

## Objetivo

Permitir que o Butler acompanhe projetos reais e responda “onde parei?”.

## Modelo mínimo

```text
Projeto
├─ estado
├─ objetivo
├─ próximos passos
├─ tarefas relacionadas
├─ bloqueios
├─ notas/sessões
└─ última atividade relevante
```

## Experiência desejada

```text
onde parei no SGL?
qual o próximo passo do Aconchega Aí?
marca que hoje finalizei a tela de relatórios
esse projeto está bloqueado esperando o backend
```

## Regras

- não inferir conclusão;
- “onde parei?” vem de histórico real;
- projeto não substitui tarefa/agenda; relaciona-se com eles;
- sessões de trabalho podem registrar estado sem obrigar uma tarefa para cada nota.

## Gate de saída

- [ ] CRUD/estado de projeto confiável;
- [ ] próximo passo explícito;
- [ ] bloqueios;
- [ ] histórico/sessões;
- [ ] relação com tarefas/agenda;
- [ ] resposta “onde parei?” baseada em dado real.

---

# ETAPA 7 — 🧭 Resumo, contexto operacional e priorização

## Objetivo

Transformar dados já existentes em orientação útil para hoje/semana sem uma IA inventar prioridade obscura.

## Fontes possíveis

- agenda;
- pendências;
- projetos;
- cursos;
- acadêmico;
- rotinas;
- clima;
- Day-off;
- prazos;
- bloqueios.

## Princípio

Priorização deve ser **explicável**.

Exemplo:

```text
1. Trabalho de Cálculo — vence amanhã
2. Corrigir bug do SGL — bloqueia entrega
3. Inglês — rotina prevista às 21h
```

O Butler deve conseguir dizer por que algo apareceu antes.

## Gate de saída

- [ ] resumo diário/semana usa dados reais;
- [ ] regras de prioridade são visíveis/testáveis;
- [ ] usuário pode ignorar/reordenar sem corromper dados;
- [ ] clima/Day-off influenciam apenas onde fizer sentido;
- [ ] nenhuma prioridade é apresentada como fato absoluto quando for apenas recomendação.

---

# ETAPA 8 — 🧠 Memória + Library seletiva

## Objetivo

Reaproveitar seletivamente o trabalho preservado de memória, sugestões e conhecimento sem entregar o controle do Core a uma arquitetura ampla.

## Candidatos preservados

```text
context_router.py
intent_parser.py
action_policy.py
context_memory.py
suggestion_engine.py
deterministic_memory.py
butler_library.py
library_catalog_handler.py
knowledge/
companion_*
conversational_*
```

## Regras de reativação

Cada componente precisa definir:

- valor real para o produto;
- posição no dispatcher;
- política de leitura/escrita;
- expiração/invalidação;
- isolamento multiusuário;
- precedência contra o Core;
- confirmação quando sugerir ação;
- regressão/falso positivo.

Library pode responder/sugerir; persistência operacional continua no Core.

Preferir dados abertos, domínio público, documentos próprios, resumos e metadados.

## Gate de saída

- [ ] memória reativada somente onde há caso de uso claro;
- [ ] nenhuma memória global entre usuários;
- [ ] Library não sequestra intenção operacional;
- [ ] sugestões pedem confirmação antes de escrever;
- [ ] flags `/health` refletem exatamente o que foi ativado.

---

# ETAPA 9 — 🔒 Hardening e consolidação de longo prazo

## Objetivo

Preparar o Butler para operação duradoura e possível distribuição mais ampla.

## Escopo

### Banco e recuperação

- backup/export D1 automatizado;
- retenção definida;
- migrations observáveis;
- rollback testado;
- backfills seguros.

### Segurança

- secrets fora do repositório;
- webhook secret validado;
- perfil do proprietário fora de configuração pública quando necessário;
- revisão de callbacks administrativos;
- least privilege onde aplicável.

### Arquitetura

- reduzir `app.py` gradualmente;
- remover compatibilidades cujo uso já tenha desaparecido;
- consolidar patches no módulo dono;
- decidir destino final do runtime antigo `src/`.

### Observabilidade

- saúde de cron;
- Durable Objects;
- falhas Telegram;
- migrations;
- latência do webhook;
- alarmes vencidos/duplicados;
- sinais multiusuário.

### Produto

Voz, web/app e outras superfícies só entram depois de a base atual estar estável, salvo decisão explícita de roadmap.

## Gate de saída

- [ ] backup/restore praticável;
- [ ] observabilidade mínima de produção;
- [ ] secrets/configuração pessoal tratados;
- [ ] dívida técnica crítica reduzida;
- [ ] compatibilidades antigas justificadas ou removidas;
- [ ] documentação de operação/deploy completa.

---

# 5. Regras transversais de implementação

## Nova persistência

```text
migration
→ backfill se necessário
→ índice se justificado
→ teste
→ documentação
```

## Novo fluxo guiado

Precisa de:

- cancelamento;
- voltar quando fizer sentido;
- limpeza de estado;
- troca de assunto segura;
- isolamento por usuário.

## Novo patch

Antes de criar:

```text
Por que não cabe no módulo dono?
Quem chama?
Qual posição no dispatcher?
Qual símbolo substitui?
Como será removido?
Qual teste protege?
```

## Nova regra temporal

Definir:

- fonte do dado;
- horário;
- tolerância;
- idempotência;
- Day-off;
- retry/falha;
- relação com Cron/Durable Objects.

Não criar scheduler concorrente sem necessidade.

---

# 6. Gate global de qualidade

Uma feature/subetapa só é considerada concluída quando, conforme aplicável:

- módulo autoritativo definido;
- isolamento multiusuário preservado;
- persistência segura;
- migration criada se houver schema novo;
- callbacks/schedulers idempotentes;
- cancelamento/voltar disponíveis;
- caso feliz + falso positivo testados;
- sequências testadas quando há contexto;
- CI verde;
- documentação sincronizada;
- `/health` coerente;
- deploy validado separadamente quando necessário.

---

# 7. Como uma nova IA deve usar este roadmap

1. abra `docs/STATUS_ATUAL.md`;
2. confirme o SHA/commits posteriores;
3. leia este roadmap para entender **por que** a ordem existe;
4. abra o documento da subetapa atual;
5. confira `ARCHITECTURE.md` e `entry.py` antes de editar;
6. continue o gate aberto;
7. não pule para a próxima etapa só porque uma ideia parece mais interessante;
8. correções de produção podem ser feitas fora da sequência, mas devem voltar ao gate oficial depois.

**No snapshot de 31/08/2026: continuar a Etapa 1.4.**
