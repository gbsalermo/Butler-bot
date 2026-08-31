# Butler — Status Atual e Handoff

**Data-base:** 31/08/2026  
**Branch de produção:** `main`  
**Snapshot técnico validado da Etapa 1:** `f08bff2e4edf5303f8b79a5a420ecd80356043fa`  
**Handoff documental da Etapa 1:** `e3220d95aed43b1e5730709e56aa07d6716e77d9`  
**Fase oficial:** **Etapa 2 — Importação acadêmica confiável**  
**Subetapa em andamento:** **2.1 — Caracterização do importador atual**

> Este é o primeiro arquivo para uma nova IA/agente consultar ao assumir o Butler. Para runtime use `ARCHITECTURE.md`; para decisões duradouras use `CONTINUIDADE.md`; para ordem futura use `TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`. O escopo atualizado da Etapa 2 está em `ETAPA_2_1_INVENTARIO_ACADEMICO.md`.

---

## 1. O projeto em uma frase

Butler é um assistente pessoal multiusuário via Telegram que combina organização cotidiana, universidade, tarefas, compromissos, rotinas, metas, musculação, mercado, clima e acompanhamento temporal confiável, mantendo operações críticas determinísticas e linguagem natural conservadora.

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
2. 🎓 Importação acadêmica confiável         🚧 em andamento — 2.1
3. ⏱️ Auxiliares de Tempo / Modo Estudo     ⏳ planejada
4. 📚 Cursos e trilhas de estudo             ⏳ planejada
   fechamento: menu por áreas da vida        ⏳ planejado
5. 📥 Caixa de entrada                       ⏳ planejada
6. 🗂️ Projetos e trabalho                    ⏳ planejada
7. 🧭 Resumo/contexto/priorização             ⏳ planejada
8. 🧠 Memória + Library seletiva             ⏳ planejada
9. 🔒 Hardening                              ⏳ planejada
10. 🌐 Abertura pública/capacidade/escala    ⏳ planejada
```

### Etapa 1 — concluída

| Subetapa | Status | Resultado principal |
|---|---|---|
| 1.1 Auditoria da linguagem | ✅ | mapa da linguagem ativa, corpus e primitivas determinísticas |
| 1.2 Base Linguística Comum | ✅ | famílias compartilhadas, polaridade e redução de parsers concorrentes |
| 1.3 Referências + Contexto Curto | ✅ | `short_context.py`, expiração, isolamento, referências e listas posicionais |
| 1.4 Correção / Auto-reparo | ✅ | correção temporal/título, elipse e rollback seguro sem duplicar item |
| 1.5 Frases compostas | ✅ | conjunções, preview e lote seguro de 2–5 ações com confirmação |
| 1.6 Conversas completas | ✅ | integração multi-turno, dois usuários, expiração, barreira de assunto e gate final |

Documento final: `docs/ETAPA_1_6_GATE_FINAL.md`.

---

## 3. Decisão de produto para a Etapa 2

O formato acadêmico atual foi validado como **suficiente e excelente para o uso desejado**.

A Etapa 2 **não é uma reforma do modelo acadêmico**.

Objetivo oficial:

> aumentar a confiança ao extrair e cadastrar as matérias de novos usuários.

Ficam fora do escopo, salvo bug mínimo explicitamente aprovado:

- redesenhar `subjects` ou `subject_sessions`;
- adicionar professor/carga horária/semestre/observações;
- criar novo modelo de avaliações/trabalhos;
- refatorar presença/faltas;
- criar migration acadêmica por melhoria arquitetural;
- alterar o formato de matéria/horário que já funciona.

Os achados de reimportação destrutiva e identidade de matéria permanecem documentados como observações técnicas, mas **não puxam esta etapa para uma reestruturação**.

---

## 4. Formato acadêmico que deve permanecer

```text
subjects
→ nome
→ ativa/trancada

subject_sessions
→ dia da semana
→ horário inicial
→ horário final
→ local
```

O sistema atual já permite:

- múltiplos horários por matéria;
- cadastro manual;
- edição de nome/dia/horário/local;
- adicionar/remover aula;
- trancar/remover matéria;
- provas;
- faltas/limite de faltas;
- avisos acadêmicos;
- consultas naturais.

Nada disso precisa ser remodelado na Etapa 2.

---

## 5. Contrato da importação para novos usuários

Fonte SIGAA recomendada:

```text
Componente Curricular | Local | Horário
```

Aceitar:

- PDF com texto pesquisável/selecionável;
- TXT.

Produção não depende de OCR.

Fluxo obrigatório:

```text
arquivo
→ extração
→ validação
→ prévia
→ confirmação explícita
→ cadastro no modelo atual
```

O Butler deve preferir marcar uma linha como ambígua a cadastrar matéria errada.

---

## 6. Sequência atual da Etapa 2

```text
2.1 Caracterização do importador atual
→ parser SIGAA + testes do comportamento que já funciona

2.2 Extração SIGAA mais robusta
→ variações de PDF/TXT, espaços, quebras de linha, códigos e locais

2.3 Validação/confiança
→ reconhecido / precisa conferir / não reconhecido
→ evitar duplicatas e falsos positivos

2.4 Prévia clara
→ mostrar exatamente matérias, dias, horários e locais que serão cadastrados

2.5 Cadastro inicial seguro
→ somente após confirmação
→ mesmo modelo atual
→ isolamento por usuário

2.6 Onboarding + corpus real
→ orientar novo usuário sobre onde pegar a grade e como exportar
→ cadastro manual continua disponível
```

**Não há etapa de migration/modelo acadêmico prevista neste escopo.**

---

## 7. Autoridades acadêmicas atuais

- `app.py`: cadastro-base, parser SIGAA, importação/preview/persistência atual;
- `academic_polish.py`: edição guiada real e onboarding SIGAA via monkeypatch instalado;
- `academic_intelligence.py`: consultas naturais, provas e lembretes de prova;
- `exam_phrase_patch.py` / `exam_cancel_patch.py`: criação/cancelamento natural de prova;
- `attendance_patch.py`: base de faltas/presença explícita;
- `attendance_enhancement.py`: relatórios/limite e callback aprimorado;
- `attendance_management.py`: editar limite e excluir/corrigir falta;
- `attendance_production_fix.py`: T-10/T0, heartbeat e menu acadêmico final;
- `attendance_alarm.py`: contingência Durable Object para avisos acadêmicos.

A Etapa 2 só deve mexer nessas autoridades quando necessário para melhorar a importação de novos usuários.

---

## 8. Invariantes acadêmicos

- aula prevista nunca implica presença;
- `vou` não grava presença fictícia;
- falta só por ação explícita;
- importação sempre tem prévia;
- imagem/scan não entra como PDF textual;
- dados isolados por usuário;
- cadastro manual permanece disponível;
- bloco ambíguo não deve ser inventado;
- o modelo acadêmico atual deve permanecer estável durante esta etapa.

---

## 9. Linguagem natural consolidada

A Etapa 1 deixou ativos:

- `language_primitives.py` — famílias/relações/referências/polaridade sem CRUD;
- `short_context.py` — contexto de 30 min, referências e listas posicionais;
- `correction_patch.py` — auto-reparo recente seguro;
- `compound_router.py` — mensagens compostas e lote confirmado;
- `temporal_language.py` — classifica alertas relativos/timers para a futura Etapa 3.

Quick timers não devem virar tarefas normais antes da Etapa 3.

---

## 10. Scheduler e performance

Scheduler possui redundância:

```text
Cron Trigger
+
Durable Objects (PersonalAlarm / AttendanceAlarm)
```

`notification_log` protege idempotência.

O caminho quente já recebeu cache por update, gates lexicais e reconciliação de alarms pós-resposta. Se latência voltar a ser problema, instrumentar por handler/D1/Telegram antes de otimizar novamente.

---

## 11. Banco e migrations

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

A lista anterior do handoff parava em `0008`; isso foi corrigido durante a 2.1.

**A Etapa 2 atual não exige nova migration acadêmica.**

Migration continua sendo fonte formal; `ensure_schema()` é defesa operacional, não substituto.

---

## 12. Validação

Fechamento técnico da Etapa 1:

- merge `f08bff2e4edf5303f8b79a5a420ecd80356043fa`;
- regressão pós-merge da `main`: success.

Handoff documental:

- merge `e3220d95aed43b1e5730709e56aa07d6716e77d9`.

Etapa 2.1 trabalha na branch `refactor/etapa-2-1-inventario-academico`.

Os testes de caracterização já cobrem parser SIGAA, múltiplos dias, blocos M/T/N, localização opcional, falsos positivos básicos e onboarding.

CI verde comprova regressão do repositório; não prova sozinho deploy Cloudflare.

---

## 13. Instrução para a próxima IA

1. confirmar commits posteriores;
2. ler `docs/ETAPA_2_1_INVENTARIO_ACADEMICO.md`;
3. preservar o modelo acadêmico atual;
4. fechar 2.1 e iniciar **2.2 — Extração SIGAA mais robusta**;
5. não criar migration/modelo acadêmico novo sem nova decisão explícita do produto;
6. focar novos usuários/primeira grade;
7. não religar NLU/Library histórica como atalho.

**Próximo trabalho oficial: concluir 2.1 e melhorar a confiabilidade do parser/importador SIGAA para novos usuários.**
