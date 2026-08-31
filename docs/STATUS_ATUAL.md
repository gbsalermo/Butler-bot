# Butler — Status Atual e Handoff

**Data-base:** 31/08/2026  
**Branch de produção:** `main`  
**Etapa 1 — Linguagem natural:** ✅ concluída  
**Etapa 2 — Importação acadêmica confiável:** ✅ concluída  
**Próxima fase oficial:** **Etapa 3 — Auxiliares de Tempo / Modo Estudo**  
**Snapshot técnico validado:** `1542ec1e1f932fdcc75b32d097ddee0089ee2034`

> Este é o primeiro arquivo para uma nova IA/agente consultar ao assumir o Butler. Para runtime use `ARCHITECTURE.md`; para decisões duradouras use `CONTINUIDADE.md`; para ordem futura use `TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`. O fechamento acadêmico está em `ETAPA_2_GATE_FINAL.md`.

---

## 1. O projeto em uma frase

Butler é um assistente pessoal multiusuário via Telegram que combina organização cotidiana, universidade, tarefas, compromissos, lembretes, rotinas, metas, musculação, mercado, clima e acompanhamento temporal confiável, mantendo operações críticas determinísticas e linguagem natural conservadora.

Produção:

```text
Telegram
→ webhook
→ Cloudflare Python Worker
→ cloudflare/src/worker.py
→ cloudflare/src/entry.py
→ handlers operacionais
→ D1 / Durable Objects / Telegram Bot API / Open-Meteo
```

A raiz `src/` continua histórica/preservada e não governa produção.

---

## 2. Estado do roadmap

```text
0. 🧹 Arrumar a casa                         ✅ concluída
1. 🗣️ Linguagem natural + conversa real     ✅ concluída
2. 🎓 Importação acadêmica confiável         ✅ concluída
3. ⏱️ Auxiliares de Tempo / Modo Estudo     ▶️ próxima etapa
4. 📚 Cursos e trilhas de estudo             ⏳ planejada
   fechamento: menu por áreas da vida        ⏳ planejado
5. 📥 Caixa de entrada                       ⏳ planejada
6. 🗂️ Projetos e trabalho                    ⏳ planejada
7. 🧭 Resumo/contexto/priorização             ⏳ planejada
8. 🧠 Memória + Library seletiva             ⏳ planejada
9. 🔒 Hardening                              ⏳ planejada
10. 🌐 Abertura pública/capacidade/escala    ⏳ planejada
```

O arquivo `TRILHA_DESENVOLVIMENTO_DEFINITIVA.md` continua sendo a autoridade da **ordem e dos gates**. Este `STATUS_ATUAL.md` é a autoridade do ponto de continuidade quando rótulos históricos de status em documentos maiores ainda não tiverem sido sincronizados.

---

## 3. Resultado consolidado da Etapa 1

A linguagem natural foi estruturada sem religar NLU ampla/opaca.

Ativos:

- `language_primitives.py` — famílias, relações, referências e polaridade sem CRUD;
- `short_context.py` — contexto curto de 30 min, isolamento por usuário e referências posicionais;
- `correction_patch.py` — auto-reparo recente seguro (`não, 16h`, `quinta não, sexta`, correção de título, `desfaz`);
- `compound_router.py` — mensagens compostas, conjunções, preview e lote confirmado de 2–5 ações;
- `temporal_language.py` — reconhecimento de alertas relativos/timers reservado para a Etapa 3.

Invariante permanente:

```text
reconhecer linguagem ≠ autorizar escrita
```

Gate final: `docs/ETAPA_1_6_GATE_FINAL.md`.

---

## 4. Resultado consolidado da Etapa 2

### Decisão de produto

O formato acadêmico atual foi validado como suficiente e **não foi remodelado**.

Permanece:

```text
subjects
→ nome
→ ativa/trancada

subject_sessions
→ dia da semana
→ início
→ fim
→ local
```

Não foram adicionados professor, carga horária, semestre, novo modelo de avaliações ou migration acadêmica.

### Novo importador de primeiro acesso

`academic_import.py` é a camada de confiança para **novo usuário sem matérias cadastradas**.

Fluxo:

```text
PDF textual/TXT
→ extração de texto existente
→ parse_schedule_report
→ validação + deduplicação
→ prévia
→ confirmação explícita
→ subjects + subject_sessions atuais
```

Se houver qualquer trecho acadêmico ambíguo:

```text
itens seguros + issue
→ mostra o que entendeu
→ mostra trecho problemático + motivo
→ NÃO persiste nada
```

O importador trata conservadoramente:

- `35M45`, `24M23`, `2T23` e demais códigos válidos do contrato atual;
- múltiplos dias;
- múltiplos códigos na mesma matéria;
- linhas repetidas por extração de PDF;
- nome quebrado em linhas;
- ordem vertical `matéria → local → horário`;
- local depois do código;
- local ausente;
- cabeçalhos/rodapés comuns;
- códigos inválidos, invertidos, repetidos ou não contíguos como revisão obrigatória.

Usuário que já possui matérias continua no comportamento acadêmico existente; a Etapa 2 não transformou reimportação em uma reforma estrutural.

Fonte SIGAA recomendada continua:

```text
Componente Curricular | Local | Horário
```

Aceitos:

- PDF com texto pesquisável/selecionável;
- TXT.

Sem OCR em produção.

Gate final: `docs/ETAPA_2_GATE_FINAL.md`.

### Validação

- PR #29: caracterização do importador atual;
- merge da caracterização: `0270d48ba51e910514ee99ae7b7bb18861668fd1`;
- PR #30: importação acadêmica confiável;
- merge técnico final: `1542ec1e1f932fdcc75b32d097ddee0089ee2034`;
- suíte da PR: **302 testes passando**;
- regressão pós-merge da `main`: **success**, run #244.

CI verde comprova regressão do repositório; não prova sozinho deploy Cloudflare.

---

## 5. Próxima etapa — Etapa 3

Documento existente: `docs/ETAPA_3_ASSISTENTES_DE_TEMPO.md`.

A Etapa 3 possui dois assistentes irmãos.

### 3A — Assistente Geral de Tempo

Transformar em execução persistente o contrato linguístico já preparado:

```text
me lembra de desligar o ovo daqui a 5 minutos
me avisa daqui a 20 minutos
me lembra daqui a 1 hora de tirar a roupa do varal
cronometra 30 minutos
inicia um timer de 45 segundos
```

Requisitos:

- alertas rápidos não viram tarefas normais;
- persistem sem depender da conversa aberta;
- sobrevivem a restart/redeploy;
- usar Durable Object/alarm/infra temporal existente, nunca `sleep()` no Worker;
- idempotência de disparo;
- cancelamento seguro;
- dois usuários isolados;
- política de Day-off definida.

### 3B — Modo Estudo

Exemplo:

```text
Matéria: Cálculo I
Tópicos:
1. Limites
2. Derivadas
3. Integrais

25 min foco / 5 min pausa
```

Invariante obrigatório:

**o tópico só avança quando o usuário explicitamente disser que concluiu ou pulou.**

Fim de timer, pausa ou passagem de tempo nunca concluem conteúdo automaticamente.

---

## 6. Scheduler e redundância

Após o incidente de 30/08/2026 existem duas linhas temporais:

```text
Cron Trigger
+
Durable Objects (PersonalAlarm / AttendanceAlarm)
```

Ambas convergem para regras autoritativas e `notification_log` protege idempotência.

No webhook, reconciliação de alarms usa trabalho pós-resposta para não bloquear respostas interativas.

Detalhes: `docs/SCHEDULER_REDUNDANCY.md`.

---

## 7. Performance

O caminho quente já recebeu:

- cache por update de `telegram_chat_id → user_id`;
- cache por update de `user_sessions`;
- gates lexicais antes de D1;
- DDL de presença removido do dispatcher geral;
- reconciliação de Durable Objects fora do tempo de resposta do webhook.

Se a latência voltar a ser um problema, o próximo passo é instrumentar **tempo por handler/D1/Telegram**, não otimizar aleatoriamente.

---

## 8. Funcionalidades operacionais relevantes

Ativas:

- tarefas/pendências;
- compromissos;
- lembretes pessoais;
- agenda Hoje/Amanhã/7 dias;
- matérias/provas/presença/faltas;
- importação acadêmica por PDF textual/TXT;
- rotinas e metas;
- mercado/itens faltando;
- musculação/progresso;
- Ler/Ver Depois: Livros, Filmes, Cursos e Outras;
- Day-off;
- resumos matinal/semanal;
- clima Open-Meteo com comentário humano;
- administração do proprietário;
- scheduler redundante.

`🎓 Cursos` em Ler/Ver Depois continua sendo backlog simples, não o módulo de Cursos/Trilhas da Etapa 4.

---

## 9. Banco e migrations

Migrations formais conhecidas:

```text
0001_initial.sql
0002_app_state.sql
0003_attendance.sql
0004_conversation_context.sql
0005_goal_profiles.sql
0006_weather_preferences.sql
0007_admin_pending_announcements.sql
0008_later_items.sql
0009_ru_menu.sql
```

A Etapa 2 não adicionou migration.

Migration continua sendo fonte formal; `ensure_schema()` é defesa operacional, não substituto.

---

## 10. Instrução para a próxima IA

1. confirmar commits posteriores a `1542ec1e1f932fdcc75b32d097ddee0089ee2034`;
2. ler `docs/ETAPA_3_ASSISTENTES_DE_TEMPO.md` e a Trilha Definitiva;
3. iniciar **Etapa 3 — Auxiliares de Tempo / Modo Estudo**;
4. começar pela infraestrutura persistente do Assistente Geral de Tempo ou pela ordem indicada no documento da Etapa 3, sem criar roadmap paralelo;
5. preservar o invariante de progresso explícito do Modo Estudo;
6. não transformar alertas rápidos em `daily_items` de tarefa;
7. não reabrir o modelo acadêmico sem nova decisão explícita do produto;
8. não religar Broad NLU/Library histórica como atalho.

**Próximo trabalho oficial: Etapa 3 — Assistente Geral de Tempo + Modo Estudo.**
