# Continuidade do desenvolvimento — Butler

**Data-base:** 31/08/2026

> Este documento registra **decisões duradouras**. Ele não deve ser usado sozinho como snapshot de andamento.
>
> - status atual/handoff: `docs/STATUS_ATUAL.md`;
> - runtime atual: `docs/ARCHITECTURE.md`;
> - visão completa: `docs/BUTLER_DOSSIE_MESTRE.md`;
> - ordem oficial de evolução: `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`;
> - classificação estrutural histórica: `docs/INVENTARIO_ETAPA_0.md`.

---

## 1. Objetivo permanente

Butler é um assistente pessoal via Telegram. A experiência desejada combina organização cotidiana, estudo, universidade, projetos, trabalho, hábitos e interesses sem virar apenas CRUD/menu nem uma IA que decide silenciosamente pelo usuário.

Princípios permanentes:

1. operações críticas são determinísticas;
2. ação explícita vence contexto antigo;
3. não inventar presença, conclusão, gasto, compromisso, treino, progresso ou memória;
4. dados e estado são isolados por usuário;
5. escrita ambígua exige confirmação quando há risco;
6. botões e linguagem natural coexistem;
7. contexto auxilia, mas não sequestra mudança de assunto;
8. comportamento novo exige regressão;
9. nova funcionalidade deve entrar no módulo autoritativo sempre que possível;
10. documentação deve separar claramente ativo, legado, preservado e planejado;
11. CI verde não deve ser confundido com deploy Cloudflare validado;
12. não criar novo roadmap quando já existe uma etapa oficial aberta.

---

## 2. Runtime oficial

Produção:

```text
Telegram Webhook
→ Cloudflare Python Worker
→ D1 / Durable Objects
→ Telegram Bot API
```

Entrypoints:

```text
cloudflare/src/worker.py
cloudflare/src/entry.py
```

A raiz `src/` continua preservada como runtime histórico polling/SQLite e não governa produção.

---

## 3. Decisão arquitetural atual

Uma geração anterior tentou centralizar linguagem/contexto em:

```text
context_router.py
intent_parser.py
action_policy.py
context_memory.py
suggestion_engine.py
Butler Library
```

Esse trabalho foi preservado, mas **não é o roteador central do webhook atual**.

A produção privilegia:

- handlers explícitos e ordenados;
- fast paths conservadores;
- famílias linguísticas compartilhadas sem efeitos colaterais;
- estados guiados;
- módulos autoritativos por domínio;
- contexto operacional curto;
- fallback estreito.

Reativação de qualquer camada preservada precisa definir antes:

- posição no dispatcher;
- precedência contra o Core;
- política de escrita;
- isolamento por usuário;
- regressão de fluxo real;
- flags coerentes no `/health`.

---

## 4. Resultado duradouro da Etapa 0

A fase “arrumar a casa” estabeleceu regras que continuam válidas.

### Dispatcher

`entry.py` é a autoridade da precedência e expõe funções testáveis para mensagens, callbacks e cron.

### Menu

`operational_menu.py` é a autoridade do menu principal. Outros módulos podem manter submenus próprios, mas não uma segunda definição concorrente do menu principal.

### Lembretes

`reliable_reminders.py` é a autoridade temporal para `daily_items`.

A antiga cadeia duplicada em `quality_patch.py`/`conversation_layer.py` foi removida e `reminder_policy.py` deixou de existir.

### Schema

`cloudflare/migrations/` é a fonte formal de evolução D1. `ensure_schema()` é apenas tolerância operacional.

### Exclusão de código

Não apagar por nome, idade ou aparência. Antes de excluir, classificar e demonstrar que o runtime não depende do componente.

---

## 5. Linguagem natural — decisões consolidadas da Etapa 1

A Etapa 1 foi concluída em 31/08/2026. Seus contratos passam a ser invariantes para as próximas etapas.

### Base linguística comum

`language_primitives.py` concentra famílias linguísticas, relações, referências, correções e polaridade compartilháveis.

Regra permanente:

```text
reconhecer linguagem
≠
autorizar escrita
```

O módulo não acessa D1, não envia Telegram e não executa CRUD. O domínio continua responsável por validar e persistir.

### Contexto curto

`short_context.py` é a autoridade do contexto operacional curto.

Regras:

- isolamento por `user_id`;
- janela inicial de 30 minutos;
- barreira de mudança explícita de assunto;
- referências `essa/ela/ele/a anterior/a outra`;
- referências posicionais baseadas na lista realmente mostrada;
- histórico de alvos recentes;
- listas candidatas sobrevivem a referências sequenciais quando o foco continua dentro da mesma lista;
- item novo fora da lista não herda candidatos antigos;
- não criar outra memória curta paralela.

Chamadores legados de `conversation_layer._remember/_context` seguem esse contrato unificado.

### Correção / auto-reparo

`correction_patch.py` permite reparar o item recém-criado/corrigido sem duplicá-lo quando o contexto é seguro.

Exemplos suportados:

```text
não, 16h
quinta não, sexta
não é dentista, é oftalmo
dentista não, oftalmo
deixa como tava
```

Contexto de lista não é corrigido silenciosamente.

### Frases compostas

`compound_router.py` é uma camada neutra de segmentação. O roteador histórico que misturava acadêmico, culinária, pets e memória não deve ser reativado.

Regras permanentes:

- conjunção descreve relação; não autoriza segunda escrita por si só;
- causa/condição/concessão são contexto;
- `ou` representa alternativa e não executa ambos os lados;
- `pão e leite` ou `João e Maria` não são artificialmente separados;
- lotes totalmente determinísticos de 2 a 5 tarefas/compromissos/lembretes podem ser confirmados em conjunto;
- lote incompleto não grava metade;
- confirmação de lote expira em 10 minutos;
- persistência do lote usa um único `INSERT` multi-values;
- grafia/acentos originais são preservados;
- a ordem criada alimenta o contexto posicional.

### Tempo relativo reservado

`temporal_language.py` reconhece `relative_alert` e `timer`, mas a Etapa 1 não executa cronômetros rápidos.

```text
me lembra daqui a 5 minutos
cronometra 30 minutos
```

não devem ser degradados para tarefa comum. A execução persistente pertence à Etapa 3.

Documento final: `docs/ETAPA_1_6_GATE_FINAL.md`.

---

## 6. Política conversa × ação

A direção conceitual permanece:

```text
comentário → conversa
pedido explícito → ação validada pelo Core
problema → ajuda/sugestão quando apropriado
ambiguidade → confirmação
correção explícita recente → auto-reparo somente quando o alvo é seguro
```

A implementação atual é distribuída por handlers e primitivas comuns, não por `action_policy.py` global.

Exceção consciente: frases domésticas claras como `acabou o café` atualmente atualizam diretamente a lista de itens faltando. Mudar isso é decisão funcional separada e deve ter regressão própria.

---

## 7. Scheduler, entrega e redundância

Princípios permanentes:

- não enviar aviso obsoleto muito depois do horário;
- registrar envio crítico como concluído somente quando a entrega tiver confirmação adequada;
- `notification_log` protege idempotência;
- falha de um subsistema não derruba os demais;
- callbacks repetidos não podem repetir efeito crítico;
- Day-off deve ser respeitado conforme a política de cada categoria;
- Cron Trigger não deve ser tratado como único relógio confiável.

Cron operacional:

```text
day_off
→ attendance
→ daily_items
→ routines
→ summaries
→ legado/compatibilidade
```

Após o incidente de 30/08/2026, existe contingência persistente via Durable Objects:

```text
PersonalAlarm
→ tarefas com horário
→ compromissos
→ lembretes simples
→ checkpoints de rotina
→ resumo matinal
→ fechamento semanal
```

`AttendanceAlarm` permanece separado para aula/presença.

Após webhook, a reconciliação de alarms usa `ctx.waitUntil(...)` para não atrasar a resposta interativa. No cron, ela continua síncrona.

A redundância não cria uma segunda autoridade de negócio: Cron e Durable Objects convergem para os mesmos dispatchers e idempotência.

Detalhes: `docs/SCHEDULER_REDUNDANCY.md`.

---

## 8. Performance do caminho quente

`performance_patch.py` pode manter cache somente durante o update atual para:

```text
telegram_chat_id → user_id
user_sessions
```

Não transformar isso em cache global persistente sem política de invalidação.

Decisões já tomadas:

- gate lexical antes de consultas de contexto quando a mensagem é irrelevante;
- DDL defensivo de presença fora do dispatcher geral;
- reconciliação global de Durable Objects fora do tempo de resposta do webhook.

Se houver nova queixa de lentidão, instrumentar tempo por handler/D1/Telegram antes de otimizar novamente.

---

## 9. Acadêmico — próxima frente oficial

Aulas são previstas; presença nunca é presumida.

O sistema pode avisar, perguntar e registrar resposta explícita, além de calcular limites de faltas conforme configuração.

A **Etapa 2** é a próxima etapa oficial e deve:

- consolidar a família acadêmica/presença;
- concluir edição completa de matérias;
- suportar múltiplos horários/localizações;
- normalizar o modelo acadêmico;
- transformar importação em pipeline com prévia/confirmação;
- usar SIGAA como primeiro adaptador oficial;
- explicar no onboarding o formato aceito/recomendado;
- preparar reaproveitamento do motor de importação para cursos.

Fonte SIGAA recomendada:

```text
Componente Curricular | Local | Horário
```

Aceitar PDF com texto pesquisável e TXT. Produção não deve depender de OCR.

---

## 10. Musculação

O perfil proprietário preserva o Protocol Mass de 12 semanas; usuários genéricos podem possuir ficha própria.

Regras permanentes:

- não aplicar protocolo pessoal a outro usuário;
- registrar carga/repetição somente quando informadas;
- substituição não apaga histórico;
- evolução usa dados realmente registrados.

---

## 11. Ler/Ver Depois

A lista operacional atual possui categorias visíveis:

```text
Livros
Filmes
Cursos
Outras
```

A categoria `Cursos` é apenas captura simples. Ela não significa que o módulo completo de Cursos/Trilhas esteja ativo.

---

## 12. Cursos, Auxiliares de Tempo e trilhas

Essas frentes são parte oficial do roadmap, mas não são funcionalidades completas ativas ainda.

### Etapa 3 — Auxiliares de Tempo / Modo Estudo

Planejada para sessões de estudo, foco/pausa, tópico atual e assistente geral de tempo persistente.

Invariante do Modo Estudo: tópico só avança quando o usuário explicitamente conclui/pula; fim de timer não conclui tópico.

### Etapa 4 — Cursos e trilhas

Modelo conceitual:

```text
Curso
→ módulo
   → conteúdo/submódulo
      → materiais/atividades
      → progresso
```

Decisões já tomadas:

- curso autogerido mantém próximo conteúdo pendente até conclusão/pulo explícito;
- curso ao vivo segue calendário fixo e não desloca aula automaticamente;
- conclusão é explícita;
- importador agrupa mídias/listas/soluções/revisões/materiais relacionados antes de salvar;
- baixa confiança exige prévia/confirmação;
- ao fechar a Etapa 4, reformular o menu por áreas da vida antes de iniciar a Etapa 5.

---

## 13. Projetos, Inbox e priorização

Compromissos do roadmap oficial:

- Caixa de entrada para captura rápida sem classificação imediata;
- Projetos/Trabalho com estado, próximos passos, bloqueios e “onde parei?”;
- Priorização do dia/semana baseada em regras explicáveis e dados reais;
- integração posterior com cursos, agenda, clima, rotinas e pendências.

Não implementar essas frentes antes dos gates definidos na Trilha.

---

## 14. Library e conhecimento

Os acervos de culinária, jogos, cultura pop, livros e filosofia continuam preservados.

Direção permanente:

- preferir dados, aliases, tags e índice, não um `if` por exemplo;
- Library pode sugerir, mas ação persistente pertence ao Core;
- preferir dados abertos, domínio público, documentos próprios e resumos/metadados.

A Library genérica continua fora do dispatcher principal até etapa própria de reativação seletiva.

---

## 15. Clima

Open-Meteo continua sendo a fonte objetiva de previsão.

`weather_personality.py` pode acrescentar comentário mais humano à apresentação, mas não pode inventar temperatura, precipitação, vento ou probabilidade.

Falha do clima não derruba agenda/resumo.

---

## 16. Multiusuário e proprietário

Toda persistência pessoal é isolada por usuário.

A barreira `is_owner(chat_id)` não deve ser removida sem mecanismo equivalente.

Recursos administrativos permanecem exclusivos do proprietário. Seeds/configurações pessoais devem migrar para configuração privada antes de distribuição mais ampla.

---

## 17. Banco e migrations

Disciplina obrigatória:

1. migration versionada;
2. backfill explícito quando necessário;
3. índice quando a consulta justificar;
4. `ensure_schema()` apenas quando houver motivo operacional;
5. teste;
6. documentação.

Migrations conhecidas: `0001` a `0008`.

Migration destrutiva exige snapshot/export D1 e plano de rollback.

---

## 18. Patches e dívida técnica

A estratégia de patches permitiu evoluir sem reescrever o Core, mas não deve continuar crescendo indefinidamente.

Regra:

```text
não criar *_fix2.py, *_final.py ou nova camada paralela
sem justificar por que o módulo autoritativo não pode receber a mudança
```

Quando um domínio for trabalhado e houver cobertura suficiente, consolidar a regra no módulo dono e remover compatibilidade antiga em mudança própria ou na etapa funcional correspondente.

---

## 19. Testes

A suíte em `cloudflare/tests/` protege o caminho realmente alcançado pelo dispatcher.

Prioridades:

- sequências completas de conversa;
- falsos positivos;
- dois usuários;
- callbacks repetidos;
- scheduler/idempotência;
- cancelamento/voltar;
- precedência de handlers;
- ausência de round-trips D1 desnecessários no caminho quente.

CI verde é condição necessária para merge, mas não prova deploy Cloudflare.

---

## 20. Ordem oficial de evolução

```text
0. 🧹 Arrumar a casa                         ✅ concluída
1. 🗣️ Linguagem natural + conversa real     ✅ concluída
2. 🎓 Acadêmico + importação robusta         ▶️ próxima etapa
3. ⏱️ Auxiliares de Tempo / Modo Estudo     ⏳
4. 📚 Cursos e trilhas de estudo             ⏳
   fechamento: menu por áreas da vida        ⏳
5. 📥 Caixa de entrada                       ⏳
6. 🗂️ Projetos e trabalho                    ⏳
7. 🧭 Resumo/contexto/priorização             ⏳
8. 🧠 Memória + Library seletiva             ⏳
9. 🔒 Hardening                              ⏳
10. 🌐 Abertura pública/capacidade/escala    ⏳
```

O status detalhado está em `docs/STATUS_ATUAL.md`.

---

## 21. Regra de atualização documental

Ao mudar:

- **status/subetapa/próximo passo:** atualizar `docs/STATUS_ATUAL.md`;
- **runtime/autoridade:** atualizar `docs/ARCHITECTURE.md` e o Dossiê quando material;
- **roadmap/ordem futura:** atualizar a Trilha Definitiva;
- **decisão duradoura:** atualizar este arquivo;
- **classificação estrutural:** atualizar Inventário somente quando a classificação realmente mudar;
- **capacidade pública/uso:** atualizar README;
- **incidente temporal/scheduler:** atualizar `docs/SCHEDULER_REDUNDANCY.md` quando aplicável.

Não duplicar detalhes por conveniência. Cada documento tem uma função clara.
