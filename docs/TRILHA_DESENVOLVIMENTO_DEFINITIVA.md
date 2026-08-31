# Butler — Trilha Definitiva de Desenvolvimento

**Roadmap mestre de evolução do produto e da arquitetura**  
**Versão:** 1.5  
**Data-base:** 31/08/2026  
**Status:** oficial  
**Fase atual:** **Etapa 2 — Acadêmico completo + importação robusta**

> Este documento define **para onde o Butler deve evoluir e em qual ordem**. Ele não substitui `docs/ARCHITECTURE.md` como fonte de verdade do runtime nem `docs/STATUS_ATUAL.md` como snapshot de andamento.
>
> Se outra IA assumir o projeto, deve continuar a etapa atual e respeitar os gates abaixo. Não criar outro roadmap.

---

# 1. Visão do Butler

O Butler deve evoluir para ser um **assistente pessoal de verdade**, centrado em Telegram, capaz de organizar cotidiano, estudo, universidade, projetos, trabalho, hábitos e interesses sem virar apenas um menu de CRUDs nem uma IA imprevisível.

Experiência desejada:

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
2. **Ação explícita vence contexto antigo.**
3. **Não inventar fatos:** presença, conclusão, gasto, treino, prioridade, compromisso ou progresso dependem de dado real/regra explícita.
4. **Multiusuário por padrão:** informação pessoal isolada por usuário.
5. **Confirmação para escrita derivada.**
6. **Texto natural e botões convivem.**
7. **Uma autoridade por domínio.**
8. **Migration é fonte formal do D1.**
9. **Toda expansão exige regressão.**
10. **Contexto auxilia, não governa.**
11. **Documentação acompanha comportamento.**
12. **CI verde não prova deploy Cloudflare.**
13. **Uma etapa só avança quando o gate estiver fechado.**
14. **Broad NLU/Library preservadas não voltam ao dispatcher central por conveniência.**

---

# 3. Runtime assumido pelo roadmap

```text
Telegram
→ webhook
→ Cloudflare Python Worker
→ cloudflare/src/worker.py
→ cloudflare/src/entry.py
→ handlers operacionais
→ D1 / Durable Objects / Telegram Bot API / Open-Meteo
```

A raiz `src/` usa polling/SQLite e é histórica/preservada.

O Core já possui tarefas, compromissos, lembretes, matérias/provas/presença, rotinas, metas, mercado, musculação, Ler/Ver Depois, Day-off, resumos, clima, isolamento multiusuário, administração e redundância temporal via Durable Objects.

---

# 4. Roadmap oficial

```text
ETAPA 0  🧹 Arrumar a casa                         ✅ concluída
             ↓
ETAPA 1  🗣️ Linguagem natural + conversa real     ✅ concluída
             ↓
ETAPA 2  🎓 Acadêmico completo + importação        ▶️ atual
             ↓
ETAPA 3  ⏱️ Auxiliares de Tempo / Modo Estudo     ⏳
             ↓
ETAPA 4  📚 Cursos e trilhas de estudo             ⏳
             ↓
FECHAMENTO 4  🧭 Reformulação do menu por áreas    ⏳
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
             ↓
ETAPA 10 🌐 Abertura pública + capacidade/escala   ⏳
```

Correções urgentes de produção podem ocorrer a qualquer momento, mas não alteram automaticamente a etapa oficial.

---

# ETAPA 0 — 🧹 Arrumar a casa

**Status:** ✅ concluída em 29/08/2026.

Entregas consolidadas:

- inventário estrutural;
- Dossiê Mestre e arquitetura documentada;
- dispatcher/callback/cron testáveis;
- menu principal com uma autoridade;
- lembretes de `daily_items` com uma autoridade;
- migrations formais alinhadas ao schema conhecido;
- política contra patches paralelos sem justificativa;
- separação entre runtime Cloudflare ativo e raiz histórica.

Após incidente em 30/08, o scheduler ganhou redundância via Durable Objects sem criar nova autoridade de negócio.

---

# ETAPA 1 — 🗣️ Linguagem natural + estabilidade de conversa real

**Status:** ✅ concluída em 31/08/2026.  
**Gate final:** `docs/ETAPA_1_6_GATE_FINAL.md`.

## Objetivo atingido

Aumentar o repertório em português brasileiro sem religar uma NLU ampla e opaca. A linguagem passou a ser tratada como estrutura:

```text
AÇÃO
ALVO
TEMPO
QUALIFICADORES
RELAÇÕES
CONTEXTO
CONFIANÇA
```

Reconhecer não autoriza escrita sozinho.

## 1.1 — Auditoria da linguagem ativa ✅

- mapa dos handlers que realmente alcançam produção;
- corpus executável;
- primeiras primitivas comuns;
- regressões de falso positivo/negação.

Documento: `ETAPA_1_AUDITORIA_LINGUAGEM.md`.

## 1.2 — Base Linguística Comum ✅

- `language_primitives.py`;
- famílias compartilhadas de ação;
- polaridade explícita;
- menos verbos/normalizadores duplicados;
- separação entre interpretação e persistência.

Documento: `ETAPA_1_2_BASE_LINGUISTICA.md`.

## 1.3 — Referências + Contexto Curto ✅

- `short_context.py` como autoridade;
- janela de 30 minutos;
- isolamento por usuário;
- `essa/ela/ele/a anterior/a outra`;
- `a primeira/a segunda/a terceira` usando ordem mostrada;
- barreira de mudança de assunto;
- listas candidatas preservadas durante referências sequenciais quando o foco permanece na mesma lista;
- item novo fora da lista não herda contexto posicional antigo.

Documento: `ETAPA_1_3_CONTEXTO_REFERENCIAS.md`.

## 1.4 — Correção e auto-reparo ✅

Suporta, com alvo recente seguro:

```text
não, 16h
quinta não, sexta
não é dentista, é oftalmo
dentista não, oftalmo
deixa como tava
```

O mesmo registro é atualizado; contexto vindo de lista não é alterado silenciosamente.

Documento: `ETAPA_1_4_CORRECOES.md`.

## 1.5 — Mensagens compostas e conjunções ✅

Cobertura estrutural de relações como:

```text
e / também / além disso
mas / porém / só que
porque / pois
então / por isso
se / caso
quando / enquanto
antes / depois / em seguida
embora
ou
```

Regras:

- conjunção não significa segunda escrita;
- causa/condição/concessão são contexto;
- alternativa não executa os dois lados;
- `pão e leite`/`João e Maria` não são separados artificialmente;
- 2–5 tarefas/compromissos/lembretes completos podem receber preview e confirmação `Registrar tudo`;
- lote incompleto não grava metade;
- confirmação expira em 10 minutos;
- persistência usa um único `INSERT` multi-values;
- grafia original é preservada;
- 6+ ações não entram no lote automático.

Documento: `ETAPA_1_5_FRASES_COMPOSTAS.md`.

## 1.6 — Conversas completas ✅

Gate de integração validou:

- sequências de referências sobre a mesma lista/lote;
- mudança de assunto;
- contexto vencido;
- dois usuários simultâneos;
- negação e auto-reparo;
- causa/alternativa;
- texto original em lote;
- contrato sem persistência para temporizadores rápidos da futura Etapa 3;
- regressão completa verde após merge `f08bff2e4edf5303f8b79a5a420ecd80356043fa`.

## Invariante que segue adiante

O Core/domínio continua sendo autoridade de escrita. Linguagem, contexto e segmentação só resolvem intenção/alvo e acionam confirmação quando necessária.

---

# ETAPA 2 — 🎓 Acadêmico completo + importação robusta

**Status:** ▶️ etapa atual.

## Objetivo

Transformar o domínio acadêmico em base sólida, editável e reutilizável para futuras importações, Modo Estudo e Cursos.

## 2.1 — Inventário e autoridade acadêmica

Antes de adicionar telas/handlers:

- mapear `subjects`, `subject_sessions`, provas, presença, importação e onboarding atuais;
- identificar sobreposição entre `academic_intelligence`, `attendance_*`, `exam_*`, `production_usability` e `app.py`;
- definir autoridade por operação;
- proteger comportamento atual com regressão.

## 2.2 — Edição completa de matéria

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

Múltiplos horários não devem exigir duplicar artificialmente a matéria.

## 2.3 — Modelo acadêmico normalizado

```text
Matéria
 ├─ horários[]
 ├─ avaliações[]
 ├─ trabalhos[]
 ├─ aulas previstas[]
 ├─ registros de presença/falta[]
 └─ observações
```

Aula prevista nunca implica presença.

## 2.4 — Importação como pipeline

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

## 2.5 — SIGAA como primeiro adaptador

Fonte recomendada:

```text
Componente Curricular | Local | Horário
```

Aceitar:

- PDF com texto pesquisável/selecionável;
- TXT.

Produção não deve depender de OCR.

## 2.6 — Onboarding

Primeiro acesso deve:

- explicar formato aceito;
- mostrar a fonte recomendada no painel principal do SIGAA;
- permitir cadastro manual;
- permitir pular importação;
- não bloquear o uso geral do Butler.

README/documentação devem refletir o mesmo contrato.

## Gate de saída da Etapa 2

- [ ] autoridades acadêmicas mapeadas;
- [ ] matéria editável integralmente;
- [ ] múltiplos horários sem duplicação artificial;
- [ ] modelo interno normalizado/documentado;
- [ ] avaliações/trabalhos coerentes com matéria;
- [ ] SIGAA usa pipeline com prévia;
- [ ] parser separado do modelo interno;
- [ ] importação não grava sem confirmação;
- [ ] presença continua explícita;
- [ ] onboarding documentado/testado;
- [ ] isolamento multiusuário;
- [ ] regressão completa verde.

**Etapa 3 não começa antes deste gate.**

---

# ETAPA 3 — ⏱️ Auxiliares de Tempo / Modo Estudo

## Objetivo

Criar serviços temporais ativos sem transformar tempo decorrido em progresso fictício.

Documento: `ETAPA_3_ASSISTENTES_DE_TEMPO.md`.

## 3A — Modo Estudo

```text
Matéria: Cálculo I
Tópicos:
1. Limites
2. Derivadas
3. Integrais

Modo: 25 min foco / 5 min pausa
```

Regras:

- foco/pausa configuráveis;
- tópicos ordenados;
- conclusão/pulo explícitos;
- fim do timer **não conclui tópico**;
- sessão pode pausar/cancelar;
- histórico registra o que realmente ocorreu.

## 3B — Assistente Geral de Tempo

A Etapa 1 já prepara:

```text
me lembra daqui a 5 minutos...
tenho que ligar daqui a 10 minutos...
cronometra 30 minutos...
```

Execução deverá ser persistente via infraestrutura temporal, nunca `sleep()` no Worker.

## Gate

- [ ] timers persistentes/rearmáveis;
- [ ] idempotência;
- [ ] alertas rápidos não poluem lista de tarefas;
- [ ] Modo Estudo mantém tópico atual;
- [ ] conclusão explícita;
- [ ] pausa/cancelamento seguros;
- [ ] Day-off definido;
- [ ] dois usuários isolados;
- [ ] regressão de restart/rearme.

---

# ETAPA 4 — 📚 Cursos e trilhas de estudo

## Objetivo

Representar aprendizado de longo prazo e integrar o próximo conteúdo ao cotidiano/Modo Estudo.

```text
Curso
→ módulos[]
   → conteúdos/submódulos[]
      → materiais[]
      → atividades[]
      → progresso
```

### Curso autogerido

Próximo conteúdo permanece pendente até conclusão/pulo explícito.

### Curso ao vivo

Segue calendário fixo; aula perdida não desloca automaticamente o curso inteiro.

### Importação

Agrupar material relacionado (aula, exercício, solução, revisão, PDF) antes de persistir. Baixa confiança exige prévia/confirmação.

`🎓 Cursos` em Ler/Ver Depois continua sendo captura simples, não esta etapa.

## Gate funcional

- [ ] Curso → Módulo → Conteúdo;
- [ ] progresso explícito;
- [ ] modos autogerido/ao vivo distintos;
- [ ] importação com prévia;
- [ ] integração com Modo Estudo;
- [ ] histórico preservado ao editar.

## Fechamento obrigatório da Etapa 4 — menu por áreas da vida

Antes da Etapa 5:

- inventariar menus ativos;
- comparar pelo menos dois protótipos;
- reorganizar por áreas humanas da vida;
- preservar atalhos frequentes;
- manter linguagem natural independente do menu;
- esconder ações exclusivas do proprietário;
- manter Voltar/Cancelar consistentes;
- manter Day-off protegido contra toque acidental;
- adicionar regressões de navegação.

Documento: `ETAPA_4_FECHAMENTO_REFORMULACAO_MENU_AREAS_DA_VIDA.md`.

---

# ETAPA 5 — 📥 Caixa de entrada / captura rápida

## Objetivo

Capturar algo sem exigir classificação imediata.

```text
anota isso pra eu organizar depois
joga na inbox: revisar autenticação do SGL
```

Gate:

- [ ] captura por botão/texto;
- [ ] listar/processar/arquivar;
- [ ] conversão segura para domínios;
- [ ] sem duplicação ao converter;
- [ ] isolamento multiusuário.

---

# ETAPA 6 — 🗂️ Projetos e trabalho

## Objetivo

Acompanhar projetos reais e responder “onde parei?”.

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

Gate:

- [ ] CRUD/estado confiável;
- [ ] próximo passo explícito;
- [ ] bloqueios;
- [ ] histórico/sessões;
- [ ] relação com tarefas/agenda;
- [ ] “onde parei?” baseado em dado real.

---

# ETAPA 7 — 🧭 Resumo, contexto operacional e priorização

## Objetivo

Transformar dados existentes em orientação útil sem prioridade opaca.

Fontes: agenda, pendências, projetos, cursos, acadêmico, rotinas, clima, Day-off, prazos e bloqueios.

Priorização deve ser explicável e editável pelo usuário.

Gate:

- [ ] resumo usa dados reais;
- [ ] regras de prioridade visíveis/testáveis;
- [ ] usuário pode ignorar/reordenar;
- [ ] clima/Day-off influenciam só onde fizer sentido;
- [ ] recomendação não é apresentada como fato absoluto.

---

# ETAPA 8 — 🧠 Memória + Library seletiva

## Objetivo

Reaproveitar seletivamente memória, sugestões e conhecimento preservados sem entregar o Core a uma arquitetura ampla.

Candidatos incluem `context_router`, `intent_parser`, `action_policy`, `context_memory`, `suggestion_engine`, `deterministic_memory`, `butler_library`, catálogo e `knowledge/`.

Cada reativação precisa definir:

- caso de uso;
- posição no dispatcher;
- leitura/escrita;
- expiração/invalidação;
- isolamento;
- precedência contra Core;
- confirmação antes de persistir;
- regressão.

Library pode responder/sugerir; persistência operacional continua no Core.

---

# ETAPA 9 — 🔒 Hardening

## Objetivo

Preparar operação duradoura.

Escopo:

- backup/export/restore D1;
- retenção e migrations observáveis;
- secrets/webhook security/least privilege;
- redução de `app.py` e compatibilidades antigas;
- consolidação de patches no módulo dono;
- saúde de cron/DO/Telegram/migrations/latência;
- dívida técnica crítica.

Gate:

- [ ] backup/restore praticável;
- [ ] observabilidade mínima;
- [ ] secrets/configuração pessoal tratados;
- [ ] dívida crítica reduzida;
- [ ] documentação operacional/deploy completa.

Hardening não libera automaticamente o bot ao público.

---

# ETAPA 10 — 🌐 Abertura pública, capacidade e escala

## Objetivo

Medir e otimizar o sistema real antes da liberação pública irrestrita.

Medir:

```text
Telegram
→ Worker
→ handlers
→ D1
→ Durable Objects
→ scheduler
→ Telegram Bot API
```

Auditar limites/preços vigentes, requests/CPU, D1 reads/writes/storage, índices/scans, jobs por minuto, históricos, Durable Objects, Telegram 429/retry, rate limiting, privacidade e onboarding público.

Criar perfis de uso leve/moderado/intenso e estimar capacidade com margem.

Executar carga progressiva e banco sintético grande, por exemplo:

```text
10 → 50 → 100 → 250 → 500 → 1.000 → 2.500 → 5.000 → ...
```

Abrir por ondas:

```text
uso interno
→ beta fechado
→ dezenas
→ centenas
→ aumento progressivo
→ público irrestrito
```

Upgrade de plano não substitui otimização.

Documento: `ETAPA_10_ABERTURA_PUBLICA_ESCALA.md`.

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

Precisa de cancelamento, voltar quando fizer sentido, limpeza de estado, troca segura de assunto e isolamento por usuário.

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

Definir fonte do dado, horário, tolerância, idempotência, Day-off, retry/falha e relação com Cron/Durable Objects.

---

# 6. Gate global de qualidade

Uma feature/subetapa só é concluída quando, conforme aplicável:

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

1. abrir `docs/STATUS_ATUAL.md`;
2. confirmar commits posteriores ao snapshot;
3. ler esta Trilha para entender a ordem;
4. abrir os documentos da etapa atual;
5. conferir `ARCHITECTURE.md` e `entry.py` antes de editar;
6. continuar o gate aberto;
7. não pular etapa;
8. correções de produção podem ocorrer fora da sequência, mas devem retornar ao gate oficial.

**No fechamento de 31/08/2026: Etapa 1 concluída; iniciar Etapa 2 pelo inventário/autoridade do domínio acadêmico.**
