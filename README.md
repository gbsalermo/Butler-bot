<p align="center">
  <img src="assets/butler.png" alt="Butler - mascote" width="420">
</p>

# Butler Bot

**Butler** é um assistente pessoal via Telegram focado em organização cotidiana: tarefas, compromissos, estudos, mercado, rotinas, metas, musculação, presença acadêmica, lembretes e uma lista simples de coisas para ler/ver depois.

A produção atual é determinística e roda em **Cloudflare Python Worker + Telegram Webhook + D1**. O projeto também preserva código de experiências anteriores de conversa, memória e Library, mas essas camadas não devem ser confundidas com o dispatcher ativo.

## Antes de alterar o projeto

Leia, nesta ordem:

1. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — fonte de verdade do runtime de produção;
2. [`docs/MAINTAINER_GUIDE.md`](docs/MAINTAINER_GUIDE.md) — regras práticas para manutenção;
3. [`cloudflare/src/README.md`](cloudflare/src/README.md) — mapa módulo por módulo;
4. [`docs/AUDIT_MAIN_2026-08.md`](docs/AUDIT_MAIN_2026-08.md) — inconsistências encontradas na auditoria da `main`;
5. `CONTINUIDADE.md` — decisões históricas e intenção arquitetural.

> **Importante:** o diretório `src/` na raiz é o runtime antigo de polling/SQLite. A produção está em `cloudflare/`. Veja [`src/README.md`](src/README.md).

## Runtime de produção

```text
Telegram
   ↓ webhook
cloudflare/src/worker.py
   ↓
cloudflare/src/entry.py
   ↓
handlers operacionais
   ↓
Cloudflare D1 / Durable Objects / Telegram Bot API
```

`cloudflare/wrangler.jsonc` aponta para `src/worker.py`. `worker.py` adiciona os alarmes persistentes e herda o dispatcher HTTP/scheduler de `entry.py`.

### Dispatcher atual

A produção não usa hoje `context_router.py` + `intent_parser.py` como roteador central. O fluxo real é uma cadeia ordenada de handlers em `entry.py`:

```text
/start/reset
→ diagnóstico
→ usabilidade/menu/navegação
→ fast path operacional
→ presença/provas/acadêmico
→ lembretes/tarefas/mercado/treino/contexto operacional
→ app.py somente para botão/estado guiado necessário
→ fallback
```

A ordem é relevante: um handler que retorna `True` consome a mensagem e impede os seguintes de rodar.

## Funcionalidades ativas

O Core operacional cobre:

- tarefas e pendências;
- compromissos e agenda;
- lembretes simples;
- matérias, grade, provas, presença e faltas;
- lista persistente do que está faltando em casa;
- rotinas e metas;
- musculação, exercícios, séries, carga e progresso;
- Ler/Ver Depois;
- finanças preservadas no Core, embora não sejam destaque do menu operacional atual;
- Day-off;
- resumo matinal e fechamento semanal;
- alarmes persistentes para eventos temporais críticos.

O Butler mantém isolamento por usuário: operações pessoais devem sempre resolver `telegram_chat_id` → `user_id` e limitar SQL ao usuário correto.

## Importação de grade do SIGAA

No primeiro acesso, o Butler orienta o usuário sobre como importar a grade acadêmica. O formato recomendado é a **tabela do painel principal do SIGAA** que contém as colunas:

```text
Componente Curricular | Local | Horário
```

É a mesma visão em que aparecem códigos de horário como `35M45`, `24M23` ou `2T23`. Esses códigos são importantes porque o parser usa o padrão do SIGAA para reconstruir os dias e horários das aulas.

### Formatos aceitos

- **PDF com texto pesquisável/selecionável**;
- arquivo **`.txt`** contendo a grade.

### Formato recomendado

1. Abra no SIGAA o painel principal onde aparecem as matérias, seus locais e horários;
2. use a opção do navegador **Imprimir → Salvar como PDF**;
3. confirme que o texto do PDF continua selecionável/pesquisável;
4. no Butler, abra **📚 Matérias → 📥 Importar grade por PDF/texto**;
5. envie o arquivo e confira a prévia antes de confirmar a importação.

O arquivo precisa preservar, para cada matéria:

```text
nome da matéria
local
código de horário do SIGAA
```

Exemplo mínimo de informação útil:

```text
Física II
PAV III, SALA 07
24M45
```

> **Não envie print, foto, imagem ou PDF escaneado.** A produção não executa OCR. Se a única fonte disponível for uma imagem, ela deve ser convertida externamente para texto/PDF pesquisável antes da importação.

O cadastro manual continua disponível em **⚙️ Gerenciar matérias** caso o usuário não queira ou não consiga importar a grade.

## Linguagem natural

O runtime atual privilegia **fast paths conservadores** para pedidos claros, em vez de uma NLU ampla.

Exemplos esperados:

```text
me lembra de entregar o relatório amanhã às 18h
amanhã tenho dentista às 15h
preciso comprar café
já comprei o café
segunda eu não vou pra Sistemas Digitais
hoje não vou conseguir treinar
cria uma rotina de estudar inglês
```

Princípio: uma ação explícita deve vencer palavras incidentais de outro domínio. Por exemplo, `me lembra de procurar jogos` é um lembrete, não uma consulta de jogos.

## Lembretes e scheduler

O cron roda a cada minuto. A política operacional atual é:

- aula: eventos temporais próprios da camada de presença;
- tarefa com horário: aviso no horário;
- compromisso: aviso 5 minutos antes;
- lembrete pessoal simples: aviso no horário, com tolerância curta para não enviar alerta obsoleto;
- resumo da manhã: 07:00;
- fechamento semanal: domingo 20:00.

`notification_log` protege contra duplicidade. Entregas críticas usam confirmação da resposta da API do Telegram antes de serem consideradas concluídas.

## Patches e compatibilidade

A `main` acumulou módulos `*_patch.py`, `*_fix.py` e `*_integration.py`. Alguns substituem funções de outros módulos no import.

Exemplos importantes:

- `performance_patch.py` otimiza o bootstrap de usuários conhecidos;
- `reminder_policy.py` desliga o scheduler antigo de itens;
- `reliable_reminders.py` é a autoridade atual de lembretes de tarefas/compromissos;
- `scheduled_delivery_guard.py` exige confirmação real do Telegram;
- `operational_menu.py` define os menus operacionais principais;
- `production_usability_patch.py` adiciona Ler/Ver Depois e mantém fallbacks de interface.

Não altere a ordem de `install_*()` em `entry.py` sem verificar quais símbolos são sobrescritos. O mapa completo está em `docs/ARCHITECTURE.md`.

## Banco de dados

A fonte formal da evolução do D1 são as migrations em `cloudflare/migrations/`:

```text
0001_initial.sql
0002_app_state.sql
0003_attendance.sql
0004_conversation_context.sql
0005_goal_profiles.sql
```

Alguns módulos mantêm `ensure_schema()` idempotente como proteção incremental, mas isso não substitui uma migration.

`runtime_schema.py` é um helper preservado; ele não é o bootstrap automático do dispatcher atual.

## Butler Library e arquitetura preservada

O repositório contém acervos de culinária, jogos, cultura pop, livros e filosofia em `cloudflare/src/knowledge/`, além de módulos como:

```text
context_router.py
intent_parser.py
action_policy.py
context_memory.py
suggestion_engine.py
library_catalog_handler.py
butler_library.py
```

Esses componentes preservam trabalho útil e continuam testáveis, porém **o dispatcher genérico da Library, a NLU ampla, sugestões transversais genéricas e memória pessoal genérica estão desabilitados no runtime operacional atual**.

Leia [`docs/BUTLER_LIBRARY.md`](docs/BUTLER_LIBRARY.md) como desenho preservado/evolução futura, não como garantia de que todo catálogo está ligado ao webhook de produção.

## Runtime legado

A raiz `src/` contém a versão anterior:

```text
python-telegram-bot
+ polling
+ SQLite
```

Ela continua disponível como referência/fallback, mas uma correção feita somente ali não altera o Worker em produção.

Dependências também são diferentes:

- `requirements.txt` → runtime legado;
- `cloudflare/pyproject.toml` → Worker atual.

## Testes

Na pasta `cloudflare/`:

```bash
pytest -q
```

A suíte roda em CPython, enquanto a produção usa Pyodide. `cloudflare/tests/conftest.py` fornece stubs mínimos de `js`/`pyodide` apenas para permitir importar módulos em testes determinísticos; ele não simula integração real com Cloudflare/Telegram.

O GitHub Actions compila `cloudflare/src` e roda a suíte em alterações relevantes.

Testes novos devem priorizar:

- caminho de produção realmente alcançado pelo `entry.py`;
- variações de linguagem próximas;
- falsos positivos;
- isolamento entre dois usuários;
- cancelamento de estados guiados;
- idempotência de schedulers.

## Convenção de comentários

Comentários devem explicar **por que**, prioridade, invariantes ou risco. Não repetir a linha seguinte.

Todo módulo novo deve ter docstring dizendo:

- responsabilidade;
- quem o chama;
- tabelas/estado que altera;
- comportamento que não pode violar.

A regra detalhada está em `docs/MAINTAINER_GUIDE.md`.

## Direção de manutenção

A prioridade agora é reduzir complexidade sem quebrar comportamento:

```text
1. testes do dispatcher real
2. consolidar patches no módulo autoritativo
3. reduzir fontes duplicadas de menu/política
4. manter isolamento multiusuário
5. manter documentação sincronizada
6. só depois ampliar novas camadas
```

Antes de criar outro `*_fix.py`, pergunte se a mudança pode entrar diretamente no módulo que já é dono do domínio.

## Segurança e configuração

Tokens nunca devem entrar no repositório. O Worker usa secret do Telegram e aceita secret de webhook quando configurado.

O projeto ainda possui configuração pessoal do perfil proprietário versionada em código. Isso é compatível com o uso atual como bot pessoal, mas deve migrar para configuração/seed privado antes de uma distribuição mais ampla.

Materiais externos devem respeitar licenças e direitos autorais; prefira dados abertos, domínio público, documentos próprios e resumos/metadados produzidos para o projeto.
