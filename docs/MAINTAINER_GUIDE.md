# Guia de manutenção do Butler

Este guia existe para que outra pessoa ou IA consiga alterar o Butler sem depender do histórico das conversas que originaram o projeto.

## 1. Comece por estes arquivos

Leia nesta ordem:

1. `docs/STATUS_ATUAL.md` — fase, subetapa, decisões recentes e próximo passo;
2. `docs/BUTLER_DOSSIE_MESTRE.md` — visão completa do produto;
3. `docs/ARCHITECTURE.md` — arquitetura **real de produção**;
4. `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md` — ordem oficial de evolução;
5. documento da subetapa atual, hoje `docs/ETAPA_1_4_CORRECOES.md`;
6. `cloudflare/src/entry.py` — prioridade dos handlers;
7. `cloudflare/src/worker.py` — entrypoint, cron e reconciliação de Durable Objects;
8. `cloudflare/src/README.md` — mapa de módulos;
9. `cloudflare/migrations/` — evolução do D1;
10. testes em `cloudflare/tests/`.

`CONTINUIDADE.md` registra decisões duradouras. `AUDIT_MAIN_2026-08.md` e `INVENTARIO_ETAPA_0.md` são snapshots históricos e não devem ser usados sozinhos para inferir o runtime atual.

## 2. Qual runtime devo editar?

### Produção

Edite `cloudflare/`.

A implantação real usa Telegram Webhook + Cloudflare Python Worker + D1 + Durable Objects.

### Legado/preservado

`src/` na raiz usa polling + SQLite. Não é a produção atual.

Se uma correção precisa valer no bot implantado, alterar apenas `src/` não resolve.

## 3. Contrato de handlers

Handlers de mensagem seguem este contrato informal:

```python
async def handle_message(db, token, message) -> bool:
    ...
    return True   # consumiu a mensagem
    return False  # outro handler pode tentar
```

Regras:

- retornar `True` somente depois de assumir responsabilidade pela mensagem;
- não gravar dados e depois retornar `False`;
- evitar capturar frases genéricas cedo demais;
- estados guiados devem ter botão/forma de cancelamento;
- qualquer escrita deve permanecer limitada ao `user_id`/`chat_id` correto.

## 4. Ordem de precedência

Em caso de conflito, a intenção operacional explícita deve vencer conteúdo incidental.

Exemplo:

```text
"me lembra de procurar jogos"
```

é um lembrete, não uma consulta à biblioteca de jogos.

Na prática, a precedência é garantida pela ordem de `entry.py`, pelas famílias linguísticas compartilhadas e pelos fast paths conservadores — não pelo antigo `context_router.py`.

Na Etapa 1.4, `correction_patch` precisa vir antes dos parsers de criação, porque `não, 16h` deve corrigir o item recém-criado, não criar outro.

## 5. Linguagem natural e contexto curto

A Etapa 1 introduziu autoridades explícitas:

```text
language_primitives.py
→ famílias linguísticas e polaridade
→ sem D1, Telegram ou CRUD

short_context.py
→ contexto curto expirável e isolado por usuário

correction_patch.py
→ correção segura do item recém-criado
```

Regras:

- reconhecimento linguístico não autoriza escrita sozinho;
- contexto velho não pode sequestrar mudança de assunto;
- contexto é isolado por `user_id`;
- a janela inicial do contexto curto é de 30 minutos;
- referências posicionais devem usar a ordem que o usuário viu;
- correção silenciosa só usa alvo marcado como recém-criado/corrigido;
- broad NLU e memória pessoal genérica continuam desativadas.

## 6. Estados de conversa

Estados ficam principalmente em `user_sessions`.

Convenções existentes:

- `guard_*` — `runtime_guard.py`;
- `later_*` — Ler/Ver Depois;
- estados de tarefa/compromisso — `app.py` e módulos especializados;
- estados acadêmicos/presença — módulos `academic_*` e `attendance_*`.

Ao criar estado novo:

1. use prefixo do domínio;
2. salve somente dados mínimos no payload;
3. implemente cancelamento;
4. limpe o estado ao concluir;
5. teste troca de assunto;
6. nunca compartilhe estado entre usuários.

## 7. SQL/D1

Todo acesso deve incluir o usuário quando a entidade for pessoal.

Prefira:

```sql
WHERE user_id=? AND id=?
```

em vez de consultar somente pelo `id`.

Para mudanças de schema:

- crie migration numerada;
- não dependa somente de `CREATE TABLE IF NOT EXISTS` dentro do handler;
- `ensure_schema()` pode existir como proteção de implantação incremental, mas não substitui a migration;
- documente qual módulo é dono da tabela.

As subetapas 1.1–1.4 reutilizam estruturas existentes e não adicionaram migration até o snapshot de 31/08/2026.

## 8. Patches e monkeypatches

O projeto acumulou módulos que modificam símbolos de outros módulos em runtime.

Antes de criar um novo patch:

1. verifique se o comportamento pode ser implementado diretamente no módulo autoritativo;
2. se ainda precisar de patch, documente qual símbolo substitui;
3. documente quem havia substituído o mesmo símbolo antes;
4. registre a posição necessária na sequência de `install_*()` de `entry.py`;
5. adicione teste que demonstre o comportamento final após todas as instalações.

**Evite criar `*_fix2.py`, `*_final.py` ou novas camadas paralelas.** A estratégia atual é consolidar domínio por domínio quando houver cobertura suficiente.

## 9. Como comentar código neste projeto

Comentários devem explicar **por quê**, prioridade, invariantes ou riscos — não repetir a linha seguinte.

Bom:

```python
# Auto-reparo vem antes dos parsers de criação para que uma correção temporal
# do turno anterior não seja interpretada como um item novo.
if await handle_correction_message(...):
    return True
```

Ruim:

```python
# chama a função
await handle_correction_message(...)
```

### Todo módulo novo deve começar com docstring

Modelo:

```python
"""Responsabilidade principal do módulo.

Chamado por: entry.py -> handler X.
Grava em: tabela Y.
Não deve: assumir presença / escrever sem confirmação / etc.
"""
```

### Funções que merecem docstring

Priorize funções que:

- alteram banco;
- resolvem contexto/referência;
- fazem monkeypatch;
- têm janela temporal;
- fazem deduplicação/idempotência;
- possuem regras de negócio não óbvias.

## 10. Menus

O menu visível de produção é autoritativo em `operational_menu.py`. Patches que sincronizam `app.MAIN_KB`/`app.COTIDIANO_KB` existem para fluxos de fallback e precisam permanecer coerentes.

Ao adicionar botão:

- adicione ao menu autoritativo;
- verifique `BASE_BUTTONS`/`EXACT_BUTTONS` quando aplicável;
- verifique navegação de volta;
- teste clique e texto digitado com o mesmo nome;
- confirme que estados temporários não capturam o botão por engano.

Ler/Ver Depois possui atualmente as categorias visíveis **Livros, Filmes, Cursos e Outras**. Isso não significa que a Etapa 4 de Cursos/Trilhas esteja implementada.

## 11. Lembretes, scheduler e Durable Objects

Nunca crie um segundo scheduler para a mesma obrigação sem estratégia explícita de idempotência e autoridade.

Hoje:

- `reliable_reminders.py` é autoridade de tarefas/compromissos/lembretes simples;
- `scheduled_delivery_guard.py` protege entrega crítica;
- `notification_log` é a principal barreira de duplicidade;
- `PersonalAlarm` fornece contingência persistente para eventos pessoais;
- `AttendanceAlarm` permanece separado para aula/presença;
- Cron Trigger continua primeira linha, mas não deve ser tratado como ponto único de falha.

**`reminder_policy.py` não existe mais.** Ele foi removido na Etapa 0 após a eliminação do scheduler duplicado que neutralizava.

Após webhook, a reconciliação dos Durable Objects deve continuar fora do caminho crítico com `ctx.waitUntil(...)`. No cron, a reconciliação permanece síncrona.

Ao alterar horário de aviso, atualize também:

- `/health` quando aplicável;
- `docs/SCHEDULER_REDUNDANCY.md` se mudar a arquitetura temporal;
- documentação de domínio;
- chaves/idempotência;
- teste correspondente.

## 12. Desempenho do caminho quente

`performance_patch.py` mantém cache **somente durante um update** para:

- `telegram_chat_id → user_id`;
- `user_sessions`.

Não transforme isso em cache global persistente sem desenho explícito de invalidação.

Outras decisões de latência já tomadas:

- gates lexicais antes de consultar contexto/D1 quando a mensagem é irrelevante;
- DDL de presença fora do dispatcher geral;
- sincronização global de alarms fora da resposta interativa.

## 13. Dados do proprietário

O projeto suporta usuários genéricos, mas ainda possui bootstrap pessoal versionado em `owner_profile.py` e `settings.py`.

Regras:

- nunca aplicar dados do proprietário em outro usuário;
- `is_owner(chat_id)` deve continuar sendo a barreira;
- novos defaults genéricos não devem depender do bootstrap pessoal;
- se o projeto for distribuído para terceiros, migrar esses dados para configuração/seed privado antes.

## 14. Fast paths

Fast paths existem para ações claras e frequentes.

Eles devem ser conservadores. Um fast path amplo demais impede handlers especializados de rodarem.

Ao adicionar frase natural:

- prefira família semântica, não uma frase única;
- use `language_primitives.py` quando a regra for compartilhável;
- teste negativas próximas;
- teste palavras de outro domínio dentro do conteúdo;
- teste seguimento temporal (`hoje`, `amanhã`, `15h`);
- teste mudança brusca de assunto;
- teste sequência de turnos quando houver contexto.

## 15. Clima

`weather_service.py` continua responsável pelos dados objetivos e Open-Meteo. `weather_personality.py` pode enriquecer a apresentação, mas não deve inventar temperatura, chuva, vento ou probabilidade.

Falha meteorológica não pode derrubar agenda/resumo.

## 16. Testes

Na pasta `cloudflare/`:

```bash
pytest -q
```

A suíte roda em CPython. O Worker real roda com objetos `js`/Pyodide; `tests/conftest.py` fornece somente stubs de import para permitir testes determinísticos.

Não use esses stubs como evidência de que uma chamada real ao Telegram/Cloudflare funciona.

### Cobertura mínima para uma mudança operacional

Teste pelo menos:

- frase feliz;
- variação informal;
- frase parecida que não deve acionar;
- usuário A e usuário B quando há estado/memória;
- repetição/idempotência quando há scheduler;
- navegação/cancelamento quando há wizard;
- sequência completa quando houver contexto/correção.

## 17. Logs e exceções

O Worker deliberadamente isola alguns schedulers para que uma falha não derrube os demais.

Não faça `except Exception: pass` em caminhos críticos novos. Quando tolerar erro:

- explique por que ele é recuperável;
- registre contexto seguro suficiente;
- nunca logue token;
- não marque notificação como entregue se o envio falhou.

## 18. Checklist antes do PR

- [ ] Li `docs/STATUS_ATUAL.md` e continuei a etapa correta?
- [ ] Alterei o runtime correto?
- [ ] Verifiquei a ordem de handlers?
- [ ] Verifiquei monkeypatches sobre o mesmo símbolo?
- [ ] Mantive isolamento por usuário?
- [ ] Existe cancelamento para estado guiado?
- [ ] Migration/documentação foram atualizadas?
- [ ] `pytest -q` passa?
- [ ] O comportamento declarado no `/health` continua verdadeiro?
- [ ] README/arquitetura ainda correspondem ao código?
- [ ] Não criei outra camada paralela sem necessidade?
- [ ] Diferenciei regressão/CI de deploy real na Cloudflare?
