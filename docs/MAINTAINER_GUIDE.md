# Guia de manutenção do Butler

Este guia existe para que outra pessoa consiga alterar o Butler sem depender do histórico das conversas que originaram o projeto.

## 1. Comece por estes arquivos

Leia nesta ordem:

1. `README.md` — visão geral;
2. `docs/ARCHITECTURE.md` — arquitetura **real de produção**;
3. `cloudflare/src/entry.py` — prioridade dos handlers;
4. `cloudflare/src/worker.py` — entrypoint e cron;
5. `cloudflare/src/README.md` — mapa de módulos;
6. `cloudflare/migrations/` — evolução do D1;
7. testes em `cloudflare/tests/`.

`CONTINUIDADE.md` é útil para decisões históricas, mas não deve ser usado sozinho para inferir o dispatcher atual.

## 2. Qual runtime devo editar?

### Produção

Edite `cloudflare/`.

A implantação real usa Telegram Webhook + Cloudflare Python Worker + D1.

### Legado/fallback

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

Na prática, a precedência hoje é garantida mais pela ordem dos handlers de `entry.py` e pelos fast paths do que pelo antigo `context_router.py`.

## 5. Estados de conversa

Estados ficam principalmente em `user_sessions`.

Convenções existentes:

- `guard_*` — `runtime_guard.py`;
- `later_*` — Ler/Ver Depois;
- estados de tarefa/compromisso — `app.py` e patches especializados;
- estados acadêmicos/presença — módulos `academic_*` e `attendance_*`.

Ao criar estado novo:

1. use prefixo do domínio;
2. salve somente dados mínimos no payload;
3. implemente cancelamento;
4. limpe o estado ao concluir;
5. teste troca de assunto;
6. nunca compartilhe estado entre usuários.

## 6. SQL/D1

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

## 7. Patches e monkeypatches

O projeto acumulou módulos que modificam símbolos de outros módulos em runtime.

Exemplos:

```python
app.ensure_user = fast_ensure_user
conversation_layer._pre_send_item_reminders = ...
routine_integration.send_message = _checked_send
```

Antes de criar um novo patch:

1. verifique se o comportamento pode ser implementado diretamente no módulo autoritativo;
2. se ainda precisar de patch, documente qual símbolo substitui;
3. documente quem havia substituído o mesmo símbolo antes;
4. registre a posição necessária na sequência de `install_*()` de `entry.py`;
5. adicione teste que demonstre o comportamento final após todas as instalações.

**Evite criar `*_fix2.py`, `*_final.py` ou novas camadas paralelas.** A próxima limpeza arquitetural deve consolidar patches no módulo dono quando houver cobertura suficiente.

## 8. Como comentar código neste projeto

Comentários devem explicar **por quê**, prioridade, invariantes ou riscos — não repetir a linha seguinte.

Bom:

```python
# Precisa rodar depois de quality_patch: esta política desativa o scheduler
# de itens legado e deixa reliable_reminders como única autoridade.
install_reminder_policy()
```

Ruim:

```python
# chama a função
install_reminder_policy()
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

## 9. Menus

Existem menus-base em `app.py` e menus operacionais em `operational_menu.py`.

O menu visível de produção deve ser considerado autoritativo em `operational_menu.py`. Patches que alteram `app.MAIN_KB`/`app.COTIDIANO_KB` existem para fluxos de fallback e precisam permanecer coerentes.

Ao adicionar botão:

- adicione ao menu autoritativo;
- verifique `BASE_BUTTONS`/`EXACT_BUTTONS` quando aplicável;
- verifique navegação de volta;
- teste clique e texto digitado com o mesmo nome;
- confirme que estados temporários não capturam o botão por engano.

## 10. Lembretes e scheduler

Nunca crie um segundo scheduler para a mesma obrigação sem uma estratégia explícita de supressão.

Hoje:

- `reliable_reminders.py` é autoridade de tarefas/compromissos/lembretes simples;
- `reminder_policy.py` desliga o item scheduler antigo da `conversation_layer`;
- `scheduled_delivery_guard.py` exige confirmação real do Telegram antes de considerar entrega válida;
- `notification_log` é a principal barreira de duplicidade.

Ao alterar horário de aviso, atualize também:

- `/health`;
- documentação;
- chaves/supressões legadas quando necessário;
- teste correspondente.

## 11. Dados do proprietário

O projeto suporta usuários genéricos, mas ainda possui bootstrap pessoal versionado em `owner_profile.py` e `settings.py`.

Regras:

- nunca aplicar dados do proprietário em outro usuário;
- `is_owner(chat_id)` deve continuar sendo a barreira;
- novos defaults genéricos não devem depender do bootstrap pessoal;
- se o projeto for distribuído para terceiros, migrar esses dados para configuração/seed privado antes.

## 12. Fast paths

Fast paths existem para ações claras e frequentes.

Eles devem ser conservadores. Um fast path amplo demais impede handlers especializados de rodarem.

Ao adicionar frase natural:

- prefira família semântica, não uma frase única;
- teste negativas próximas;
- teste palavras de outro domínio dentro do conteúdo;
- teste seguimento temporal (`hoje`, `amanhã`, `15h`);
- teste mudança brusca de assunto.

## 13. Testes

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
- navegação/cancelamento quando há wizard.

## 14. Logs e exceções

O Worker deliberadamente isola alguns schedulers para que uma falha não derrube os demais.

Não faça `except Exception: pass` em caminhos críticos novos. Quando tolerar erro:

- explique por que ele é recuperável;
- registre contexto seguro suficiente;
- nunca logue token;
- não marque notificação como entregue se o envio falhou.

## 15. Checklist antes do PR

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
