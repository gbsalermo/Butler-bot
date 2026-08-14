<p align="center">
  <img src="assets/butler.png" alt="Butler - mascote" width="420">
</p>

# Butler Bot

Assistente pessoal via Telegram para organização acadêmica, tarefas, compromissos, pendências, casa, metas, musculação, autocuidado e finanças pessoais.

O projeto roda inicialmente via **polling**, usa **SQLite** e possui duas formas de execução no mesmo código-base.

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

### Butler genérico

```bash
python -m src.main_generic
```

A versão genérica nasce limpa:

- **não** carrega a grade pessoal;
- **não** carrega o Protocol Mass;
- usa banco separado (`data/butler_generic.db` por padrão);
- registra o `chat_id` da pessoa no `/start`;
- pergunta como ela quer ser chamada;
- musculação começa sem rotina cadastrada;
- pode importar a própria grade por PDF textual ou arquivo `.txt`.

Crie `.env.generic` a partir de `.env.generic.example` e use o token de um bot Telegram separado.

## Onboarding e nome preferido

No primeiro `/start`, se ainda não houver apelido salvo, o Butler pergunta:

> Como você quer que eu te chame?

O valor fica persistido junto ao `chat_id`. Depois ele pode ser alterado em:

`🏠 Cotidiano → 👤 Como me chamar`

As respostas casuais e lembretes proativos passam a usar esse nome/apelido quando possível.

## Importação da grade por PDF/texto

Em:

`📚 Matérias → 📥 Importar grade por PDF/texto`

é possível enviar:

- **PDF com texto pesquisável/selecionável**;
- arquivo `.txt` contendo a grade.

O Butler procura códigos SIGAA como `35M45`, `24M23` e `3T23`, traduz para dias/horários completos e apresenta uma **prévia antes de gravar**.

Se uma matéria já existir, a importação atualiza os horários dela em vez de criar duplicata.

### O que não é aceito

Para manter o projeto simples e facilitar a futura hospedagem, o Butler **não executa OCR** e não aceita diretamente:

- foto da grade;
- screenshot;
- JPG/PNG/WebP;
- PDF que contém apenas uma imagem/scan.

Se a pessoa só possuir uma imagem, deve usar qualquer IA/ferramenta capaz de convertê-la para um **PDF com texto pesquisável** e então enviar esse PDF ao Butler.

O cadastro manual continua disponível em `⚙️ Gerenciar matérias` para quem preferir cadastrar matéria por matéria.

Essa decisão remove a dependência de Tesseract, Pillow e `pytesseract`. PDFs textuais são extraídos com `pypdf`.

## Horários SIGAA

O Butler usa blocos de **horas completas** como representação oficial. Exemplos:

- `M23` → `08:00–10:00`;
- `M45` → `10:00–12:00`;
- `T23` → `14:00–16:00`;
- `T2345` → `14:00–18:00`;
- `N12` → `18:00–20:00`.

Correções manuais do usuário continuam tendo prioridade sobre o código exibido pelo SIGAA.

## Menu principal

- 🌙 Day-off
- 🏋️ Musculação
- 📚 Matérias
- ✅ Tarefas
- 📅 Compromissos
- 📌 Pendências
- 🗓️ Hoje
- 🏠 Cotidiano

Dentro de **Cotidiano** ficam lista de mercado, metas, rotinas, finanças e configuração de como o Butler deve chamar o usuário.

## Funcionalidades principais

### Acadêmico

- grade persistente;
- gerenciamento de matérias: adicionar, remover, trancar e editar;
- tradução de códigos SIGAA;
- importação por PDF textual/`.txt`;
- lembrete automático antes das aulas.

### Tarefas, compromissos e pendências

- adicionar/listar/concluir/editar/remover;
- data, horário e observação;
- antecedência configurável;
- lembretes proativos;
- concluir ou adiar pelo próprio aviso.

### 🏋️ Musculação — Butler pessoal

O Butler pessoal possui o Protocol Mass completo de 12 semanas, com:

- `🚀 Começar os trabalhos` como início único do protocolo;
- treino do dia;
- faltas com motivo;
- exercícios substitutos oficiais;
- registro série por série de carga/repetições;
- histórico de carga;
- progresso semanal;
- opção temporária de reiniciar o protocolo durante os testes.

Na versão genérica, musculação começa vazia e usa o cadastro manual de rotina/exercícios.

### 🌙 Day-off

Silencia cobranças e lembretes até o usuário chamar o Butler novamente.

### 🕴️ Personality Engine

Respostas variam entre neutras, leves e sarcásticas, sempre preservando contexto importante. Em situações sensíveis/Day-off, o sarcasmo é desativado.

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
