<p align="center">
  <img src="assets/butler.png" alt="Butler - mascote" width="420">
</p>

# Butler Bot

Assistente pessoal via Telegram para organização acadêmica, tarefas, compromissos, casa, metas, musculação, autocuidado e finanças pessoais.

O projeto roda inicialmente via **polling**, usa **SQLite** no rolling local e possui duas formas de execução no mesmo código-base.

## Versões

### Butler pessoal

```bash
python -m src.main
```

Mantém os dados pessoais já existentes no projeto:

- grade acadêmica inicial;
- correção manual do Laboratório de Sistemas Digitais I;
- Protocol Mass de 12 semanas;
- histórico do usuário no banco `data/butler.db`.

### Butler genérico / multiusuário

```bash
python -m src.main_generic
```

A versão genérica nasce limpa e é personalizada por `chat_id`:

- não carrega a grade pessoal;
- não carrega o Protocol Mass;
- registra automaticamente cada chat que interage com o bot;
- cada `chat_id` possui dados isolados no rolling local;
- `/start` pergunta como a pessoa quer ser chamada;
- musculação começa sem rotina cadastrada;
- pode importar a própria grade por PDF textual ou `.txt`.

No rolling local, o isolamento usa um pequeno registro central e um SQLite por chat em `data/butler_generic_users/`. Isso é propositalmente simples para o volume esperado de poucos usuários.

### Regra de isolamento

O `chat_id` define o contexto do Butler. Antes de qualquer mensagem ou callback, `src/user_scope.py` seleciona o armazenamento correspondente ao chat atual.

Isso isola por usuário/chat:

- matérias e horários;
- tarefas e compromissos;
- itens faltando em casa;
- metas e progresso;
- rotinas e logs;
- musculação manual da versão genérica;
- Day-off;
- nome preferido;
- lembretes do scheduler.

O scheduler percorre os chats registrados individualmente e envia cada lembrete somente ao chat dono daquele armazenamento.

> O Protocol Mass permanece exclusivo do Butler pessoal nesta etapa.

### Hospedagem Cloudflare

A separação por `chat_id` é uma regra de domínio e deve ser preservada na hospedagem. O SQLite por arquivo é apenas a implementação do rolling local. Na etapa de Cloudflare, a persistência será adaptada para D1/armazenamento persistente da plataforma sem alterar a lógica de identidade do Butler.

## Menu principal — acesso rápido

O menu inicial prioriza ações de poucos segundos:

- 🌙 Day-off
- ➕ Adicionar
- 🗓️ Hoje
- 🛒 Item faltando
- 📚 Matérias
- 🏠 Cotidiano
- 🏋️ Musculação

`➕ Adicionar` deixa escolher entre **Nova tarefa** e **Novo compromisso**.

Dentro de **Cotidiano** ficam Tarefas, Compromissos, lista de mercado, metas, rotinas, finanças e configuração de como o Butler deve chamar o usuário.

### Pendências

Pendência não é mais um tipo criado pelo usuário. Uma **tarefa vencida e ainda não concluída** passa automaticamente a aparecer como pendência na visão `🗓️ Hoje`.

## Captura rápida

### Tarefas e compromissos

Fluxo padrão:

1. título;
2. Hoje / Outro dia / Sem data;
3. horário quando houver data;
4. salvar.

O fluxo rápido não pergunta observação nem antecedência. O lembrete fica para a hora marcada. Datas passadas e horários já vencidos no dia atual são rejeitados.

### Item faltando

Exemplos aceitos:

```text
sal
sal, açúcar, café
falta sal, açúcar, café
café | 2 pacotes
```

Quantidade é opcional.

## Onboarding e nome preferido

No primeiro `/start`, se ainda não houver apelido salvo, o Butler pergunta como o usuário quer ser chamado. Depois isso pode ser alterado em:

`🏠 Cotidiano → 👤 Como me chamar`

## Importação da grade por PDF/texto

Em:

`📚 Matérias → 📥 Importar grade por PDF/texto`

é possível enviar:

- PDF com texto pesquisável/selecionável;
- arquivo `.txt` contendo a grade.

O Butler procura códigos SIGAA como `35M45`, `24M23` e `3T23`, traduz para dias/horários completos e apresenta uma prévia antes de gravar.

Não há OCR. Foto, screenshot ou PDF escaneado sem texto devem ser convertidos antes para PDF com texto pesquisável por qualquer IA/ferramenta, ou cadastrados manualmente.

## Horários SIGAA

O Butler usa blocos de horas completas:

- `M23` → `08:00–10:00`;
- `M45` → `10:00–12:00`;
- `T23` → `14:00–16:00`;
- `T2345` → `14:00–18:00`;
- `N12` → `18:00–20:00`.

Correções manuais do usuário têm prioridade sobre o código exibido pelo SIGAA.

## Funcionalidades principais

### Acadêmico

- grade persistente;
- gerenciamento de matérias: adicionar, remover, trancar e editar;
- tradução de códigos SIGAA;
- importação por PDF textual/`.txt`;
- lembrete automático antes das aulas.

### Tarefas e compromissos

- criação rápida;
- listar/concluir/editar/remover;
- data e horário opcionais;
- lembretes proativos;
- concluir ou adiar pelo próprio aviso;
- tarefas vencidas aparecem automaticamente como pendências.

### 🗓️ Hoje

Reúne aulas, tarefas e compromissos do dia, tarefas vencidas, treino cadastrado e quantidade de itens faltando em casa.

### 🏋️ Musculação — Butler pessoal

O Butler pessoal possui o Protocol Mass completo de 12 semanas, com:

- início único por `🚀 Começar os trabalhos`;
- treino do dia;
- faltas com motivo;
- exercícios substitutos oficiais;
- registro série por série de carga/repetições;
- histórico de carga;
- progresso semanal;
- opção temporária de reiniciar o protocolo durante os testes.

Na versão genérica, musculação começa vazia e usa o cadastro manual.

### 🌙 Day-off

Silencia cobranças e lembretes até o usuário chamar o Butler novamente. Na versão genérica, o Day-off é isolado por `chat_id` e não afeta outros usuários.

### 🕴️ Personality Engine

Respostas variam entre neutras, leves e sarcásticas. Em situações sensíveis/Day-off, o sarcasmo é desativado.

## Grade pessoal inicial

| Matéria | Dia | Horário | Local |
|---|---|---|---|
| Álgebra Linear I | Terça e quinta | 10:00–12:00 | PAV III, Sala 10 |
| Física II | Segunda e quarta | 10:00–12:00 | PAV III, Sala 07 |
| Laboratório de Sistemas Digitais I | Segunda | 14:00–16:00 | PAV Eng., Sala D6 |
| Princípios de Eletrônica Analógica | Terça e quinta | 08:00–10:00 | PAV I, Sala 104 |
| Sistemas Digitais I | Segunda | 08:00–10:00 | PAV I, Sala 11 |
| Sistemas Digitais I | Quarta | 08:00–10:00 | PAV I, Sala 114 |

## Executar o Butler pessoal

```bash
git pull origin main
pip install -r requirements.txt
python -m src.main
```

## Executar o Butler genérico

```bash
copy .env.generic.example .env.generic
# configure TELEGRAM_BOT_TOKEN
python -m src.main_generic
```

No Linux/macOS, use `cp` no lugar de `copy`.

O estado detalhado do desenvolvimento fica em `CONTINUIDADE.md`.
