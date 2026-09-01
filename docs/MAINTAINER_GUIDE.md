# Guia de manutenção do Butler

**Data-base:** 01/09/2026

Este guia existe para evitar que uma correção pequena volte a criar autoridades concorrentes, estados frágeis ou documentação incompatível com produção.

---

## 1. Antes de alterar qualquer coisa

Leia nesta ordem:

1. `docs/STATUS_ATUAL.md` — ponto exato do roadmap;
2. `CONTINUIDADE.md` — decisões duradouras;
3. `docs/ARCHITECTURE.md` — runtime real;
4. `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md` — ordem oficial;
5. documento/gate da etapa atual;
6. `cloudflare/src/entry.py` e o módulo autoritativo envolvido.

Não crie novo roadmap, não reorganize etapas e não avance gate por conveniência.

O ponto atual depois da Etapa 4.6 é:

```text
FECHAMENTO OBRIGATÓRIO DA ETAPA 4
→ menu por áreas da vida
→ somente depois Etapa 5
```

---

## 2. Runtime que realmente importa

Produção:

```text
Telegram
→ cloudflare/src/worker.py
→ cloudflare/src/entry.py
→ handlers ativos
→ D1 / Durable Objects / APIs externas
```

A raiz `src/` é histórica/preservada. Corrigir somente ali não corrige o bot de produção.

Antes de mexer num arquivo, prove que ele é alcançado pelo runtime ativo.

---

## 3. Uma autoridade por domínio

Regra prática:

```text
nova regra de negócio
→ localizar módulo dono
→ implementar no dono
→ expor por handler/ponte
→ teste
```

Evite criar `*_patch.py`/`*_fix.py` por reflexo.

Uma camada paralela só é aceitável quando existe fronteira real ou limitação técnica. Exemplo válido: `course_study_bridge.py` liga Cursos e Modo Estudo sem transformar um deles na autoridade do outro.

Autoridades importantes:

| Domínio | Autoridade/camada principal |
|---|---|
| Dispatcher | `entry.py` |
| Menu principal | `operational_menu.py` |
| Contexto curto | `short_context.py` |
| Linguagem comum | `language_primitives.py` |
| `daily_items` temporais | `reliable_reminders.py` |
| Modo Estudo | `study_mode.py` |
| Cursos — persistência | `course_domain.py` |
| Cursos — CRUD Telegram | `course_operational.py` |
| Cursos — progresso/integrações UX | `course_stage4.py` |
| Cursos ↔ Modo Estudo | `course_study_bridge.py` |
| Importação de Cursos | `course_importer.py`, persistindo via `course_domain.py` |
| Ler/Ver Depois | `production_usability_patch.py` |
| Alarmes persistentes | `personal_alarm.py`, `attendance_alarm.py` |

---

## 4. Dispatcher primeiro, regex depois

Handlers são ordenados. Se uma mensagem entra no domínio errado:

1. reproduza;
2. descubra qual handler anterior retornou `True`;
3. verifique estado atual e precedência;
4. só depois ajuste interpretação/roteamento.

Não trate sintoma acrescentando regex em outro módulo sem entender quem sequestrou a mensagem.

Ação explícita deve vencer contexto antigo.

---

## 5. Estados guiados

Todo fluxo multi-turno deve preservar o objeto já escolhido no payload quando o próximo turno só pede um valor.

Exemplo correto:

```text
usuário escolhe tarefa #1
→ state guarda task_id
→ próximo turno recebe "amanhã às 8h"
→ atualiza aquele task_id
```

Exemplo incorreto:

```text
usuário escolhe tarefa #1
→ próximo turno recebe data
→ parser tenta identificar a tarefa outra vez
```

Para listas numeradas temporárias, preserve os IDs da lista exibida. Não reconsulte uma ordem nova e interprete `1` contra uma lista que o usuário nunca viu.

O mesmo vale para listas filtradas, como hábitos elegíveis para vínculo com rotina.

---

## 6. Cancelamento e mudança de assunto

Fluxos guiados devem, quando aplicável:

- aceitar cancelamento;
- limpar estado temporário;
- permitir voltar;
- não capturar indefinidamente mensagens de outro domínio;
- manter payload mínimo e identificadores confiáveis.

Confirmações de escrita derivada devem expirar ou ser invalidadas quando o contexto deixa de ser seguro.

---

## 7. Multiusuário

Toda operação pessoal precisa restringir leitura/escrita ao `user_id` correto.

Nunca aceite um `id` vindo do estado/usuário como prova de propriedade. A consulta/mutação da autoridade deve validar também o usuário.

Teste obrigatório para persistência pessoal nova:

```text
usuário A cria
usuário B tenta listar/abrir/editar
→ não consegue
```

Cursos, estudos, tarefas, metas e demais domínios devem manter esse contrato.

---

## 8. Banco e migrations

Fonte formal:

```text
cloudflare/migrations/
```

Migrations atuais vão de:

```text
0001_initial.sql
...
0013_courses.sql
0014_course_study_links.sql
```

`ensure_schema()` é tolerância operacional e **não substitui migration**.

Nova persistência segue:

```text
migration
→ backfill se necessário
→ índice quando justificado
→ testes
→ documentação
```

Migration destrutiva exige export/backup D1 e plano de rollback.

---

## 9. Regras permanentes de linguagem

`language_primitives.py` e contexto podem reconhecer intenção, mas:

```text
reconhecer ≠ autorizar escrita
```

Não invente:

- presença;
- conclusão;
- prioridade;
- carga/repetição;
- progresso de curso;
- gasto;
- compromisso;
- memória pessoal.

Ambiguidade com efeito persistente exige confirmação quando não houver alvo/regra determinística suficiente.

---

## 10. Cursos estruturados

`📘 Cursos` está implementado até o gate 4.6.

**Não confundir com `🎓 Cursos` de Ler/Ver Depois.** Esse último continua sendo backlog simples.

### Persistência

`course_domain.py` é a autoridade. `course_operational.py`, `course_stage4.py` e `course_importer.py` não devem criar SQL concorrente de mutação do domínio.

### Progresso

Invariantes:

```text
abrir conteúdo             ≠ concluir
Continuar curso            ≠ concluir
tempo estudado             ≠ concluir
fim de sessão de estudo    ≠ concluir
último conteúdo resolvido  ≠ concluir curso
```

Mudança de status precisa de ação explícita.

### Modo Estudo

`course_study_bridge.py` cria vínculo e sessão, mas conclusão no Modo Estudo não sincroniza conclusão do conteúdo do curso.

Não adicione sincronização automática sem reabrir formalmente a decisão de produto e seu gate.

### Importação

Pipeline obrigatório:

```text
entrada
→ parser determinístico
→ validação completa
→ prévia
→ confirmação
→ persistência via course_domain
```

Não use `parser → banco` direto. Não adivinhe linhas ambíguas. Não introduza OCR como dependência silenciosa.

---

## 11. Menu

A autoridade atual é `operational_menu.py`.

Menu antes do fechamento da Etapa 4:

```text
➕ Adicionar      | 🗓️ Hoje
🛒 Item faltando | 📚 Matérias
🏠 Cotidiano      | 🏋️ Musculação
📘 Cursos
📖 Manual
🌙 Day-off
```

`🌙 Day-off` deve continuar protegido contra toque acidental.

O próximo trabalho oficial é reorganizar esse menu por áreas humanas da vida. Ao fazê-lo:

- inventarie menus ativos antes;
- compare os protótipos previstos no documento de fechamento;
- preserve atalhos frequentes;
- não quebre linguagem natural fora do menu;
- esconda ações de proprietário para usuários comuns;
- mantenha Voltar/Cancelar consistentes;
- adicione regressões de navegação.

---

## 12. Ler/Ver Depois

Categorias:

```text
📚 Livros
🎬 Filmes
🎓 Cursos
🗂️ Outras
```

A categoria `🎓 Cursos` **não prova nem substitui** o domínio `📘 Cursos`. Ambos coexistem com finalidades diferentes.

---

## 13. Modo Estudo e regras temporais

Fim de foco não conclui tópico.

Timers rápidos não viram tarefas.

Para qualquer nova regra temporal, documente:

- fonte do horário;
- tolerância;
- idempotência;
- retry/falha;
- efeito do Day-off;
- relação com Cron/Durable Objects;
- chave usada em `notification_log` quando aplicável.

Não use `sleep()` no Worker para persistência temporal.

---

## 14. Scheduler e Durable Objects

Linha primária: Cloudflare Cron.

Contingência: `PersonalAlarm`/`AttendanceAlarm`.

Ambas devem convergir para as mesmas autoridades e barreiras de idempotência.

Depois do webhook, reconciliações globais devem usar `ctx.waitUntil(...)` quando já definido pelo runtime, para não aumentar latência interativa.

---

## 15. Testes

Na pasta `cloudflare/`:

```bash
pytest -q
```

Workflow:

```text
.github/workflows/butler-regression.yml
```

Ele compila `cloudflare/src` e executa a suíte determinística.

Toda mudança funcional precisa, conforme aplicável, de:

- caso feliz;
- falso positivo/erro;
- isolamento multiusuário;
- cancelamento/estado;
- sequência multi-turno;
- regressão de bug quando a mudança nasce de incidente.

Etapa 4 possui suites específicas:

```text
test_stage4_3_course_progress.py
test_stage4_4_course_study_bridge.py
test_stage4_5_course_import.py
test_stage4_6_course_gate.py
```

---

## 16. CI não é deploy

Um PR pode estar verde e o Worker ainda não ter sido publicado.

Sempre diferencie:

```text
GitHub Actions verde
≠
Workers Build/Deploy validado
```

Depois de merge que afeta produção, verifique separadamente o build/deploy de `salbutler-bot` quando houver acesso à Cloudflare.

Não declare produção atualizada apenas porque `pytest` passou.

---

## 17. Documentação

Quando a mudança altera comportamento material:

- `docs/STATUS_ATUAL.md` — andamento/próximo passo;
- `CONTINUIDADE.md` — decisão duradoura;
- `docs/ARCHITECTURE.md` — runtime/autoridade;
- `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md` — apenas quando o andamento oficial do roadmap muda;
- `docs/MANUAL_USUARIO.md` — comportamento visível ao usuário;
- README — visão de entrada do repositório;
- documento específico da etapa/gate.

Evite deixar frases contraditórias do tipo “feature ainda não existe” depois que o gate já foi fechado.

---

## 18. Biblioteca/IA preservadas

Existir no repositório não significa estar no webhook.

Broad NLU, Library genérica e camadas experimentais permanecem preservadas para etapas futuras. Não as ligue ao dispatcher central só para resolver uma lacuna local.

A trilha IA/Groq continua depois da Etapa 10 + gate de estabilidade.

---

## 19. Checklist antes do merge

- [ ] módulo dono identificado;
- [ ] nenhuma autoridade paralela acidental;
- [ ] isolamento multiusuário preservado;
- [ ] migration criada se necessário;
- [ ] estados/cancelamento seguros;
- [ ] testes novos + regressão completa verdes;
- [ ] documentação sincronizada;
- [ ] PR no ponto correto do roadmap;
- [ ] CI do **head final** verde;
- [ ] deploy tratado como verificação separada.

---

## 20. Ponto atual

Subetapas 4.1–4.6: ✅.

Próximo trabalho oficial:

```text
Fechamento da Etapa 4 — menu por áreas da vida
```

Etapa 5 — Caixa de entrada continua bloqueada até esse fechamento e sua regressão.
