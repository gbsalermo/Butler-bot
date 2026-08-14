<p align="center">
  <img src="assets/butler.png" alt="Butler - mascote" width="420">
</p>

# Butler Bot

**Butler** é um assistente pessoal via Telegram para organização diária. Ele reúne agenda acadêmica, tarefas, compromissos, lembretes, casa, musculação, metas, autocuidado e finanças simples, com uma personalidade provocativa baseada no comportamento realmente registrado.

A proposta não é ser apenas um menu de CRUD. O Butler deve estar presente: lembrar compromissos, mostrar o que vem pela frente, perceber adiamentos e faltas, acompanhar sequências, provocar quando existe histórico para isso e reduzir ao mínimo o esforço necessário para registrar algo.

O bot pode ser usado por **botões** ou por **texto natural**. A camada de linguagem natural atual é determinística e não depende de LLM/API externa.

---

## Estado atual

O rolling local está funcional e concentra as funcionalidades planejadas antes da primeira hospedagem.

- Python + `python-telegram-bot[job-queue]`;
- SQLite no ambiente local;
- polling no desenvolvimento;
- persistência de dados;
- scheduler para lembretes e resumos;
- Butler pessoal e versão genérica multiusuário;
- isolamento da versão genérica por `chat_id`;
- linguagem natural v1;
- personalidade contextual baseada em dados reais;
- próxima grande etapa: **Cloudflare + webhook Telegram + D1**.

Bot pessoal: **Butler** — `@ButlerSal_BOT`.

---

# Capacidades atuais

## ⚡ Menu principal

O menu foi desenhado para deixar as ações mais frequentes a poucos cliques:

- 🌙 **Day-off**
- ➕ **Adicionar**
- 🗓️ **Hoje**
- 🛒 **Item faltando**
- 📚 **Matérias**
- 🏠 **Cotidiano**
- 🏋️ **Musculação**

`➕ Adicionar` permite criar tarefa ou compromisso.

`🛒 Item faltando` abre diretamente:

- ➕ adicionar item;
- 📋 listar itens faltando.

Tarefas, compromissos, mercado, metas, rotinas, finanças e configurações também ficam disponíveis em **Cotidiano**.

---

## 🗣️ Linguagem natural

O Butler já consegue interpretar diversas frases comuns sem exigir navegação pelos botões.

### Compromissos

```text
Butler, amanhã tenho dentista às 15h
amanhã tenho dentista 15h
tenho dentista amanhã às 15:30
sexta tenho reunião 10h
dentista amanhã 15h
tenho prova segunda às 8h
```

Ele extrai título, data e horário e grava usando as mesmas regras do fluxo tradicional.

Se faltar informação, pergunta apenas o necessário. Exemplo:

```text
tenho dentista amanhã
```

→ pergunta somente o horário.

### Tarefas e lembretes

```text
amanhã preciso entregar o relatório às 18h
tenho que estudar física amanhã
preciso comprar um adaptador
anota uma tarefa: revisar álgebra
```

Pedidos explícitos de lembrete não fingem possuir horário:

```text
me lembra de entregar o relatório
```

→ o Butler pergunta quando deve lembrar.

### Compras domésticas / mercado

Compras domésticas simples são interpretadas como **itens faltando em casa**, e não como tarefas:

```text
preciso comprar café
preciso comprar arroz e feijão
falta sal, açúcar e café
bota café na lista de mercado
coloca detergente na lista de compras
```

Compras que claramente representam outra responsabilidade continuam como tarefa, por exemplo:

```text
preciso comprar um adaptador para o trabalho
```

Também entende:

```text
o que falta em casa?
mostra a lista de mercado
comprei o café
```

Ao informar que comprou algo, o item é marcado como comprado. Se houver mais de um alvo plausível, o Butler pede confirmação.

### Consultar agenda

```text
o que tenho amanhã?
o que tenho daqui a 3 dias?
o que tenho sexta?
como está minha agenda sexta?
o que tenho na próxima semana?
```

### Pendências

```text
quais tarefas estão atrasadas?
o que ficou pendente?
o que está atrasado?
```

### Concluir tarefa

```text
já fiz o relatório
terminei o trabalho
concluí revisar física
```

O Butler procura a tarefa pendente correspondente. Se existirem tarefas parecidas, pergunta qual antes de alterar qualquer registro.

### Avisar atraso

```text
vou me atrasar para o dentista
vou chegar atrasado na reunião
estou atrasado para a entrevista
```

O aviso **não altera automaticamente o horário do compromisso**. Ele é registrado como evento comportamental.

A provocação depende do histórico: a primeira ocorrência é tratada como caso isolado; reincidências permitem respostas como “não chega a ser exatamente uma novidade 👀”.

### Academia

```text
hoje não vou treinar porque estou cansado
não consigo treinar hoje
não vai dar pra treinar hoje
não vou pra academia
```

No Butler pessoal, uma falta só é registrada se o protocolo já tiver sido iniciado por `🚀 Começar os trabalhos`.

### Finanças

```text
gastei 35 com lanche
paguei 20 de uber
gastei 80 no mercado
recebi 540 de bolsa
entrou 200 de trabalho
quanto gastei esse mês?
quanto sobrou?
como estão minhas finanças?
```

Categorias simples podem ser inferidas automaticamente; o que não for reconhecido vai para `Outros`.

### Datas e horários entendidos

Entre os formatos suportados estão:

- hoje;
- amanhã;
- depois de amanhã;
- sexta / próxima sexta;
- `20/08`;
- `20/08/2026`;
- daqui a 3 dias;
- `15h`;
- `15h30`;
- `15:30`;
- às 15h;
- por volta das 15h.

Datas passadas e horários já vencidos no dia atual são bloqueados.

### Princípio de segurança da linguagem natural

O Butler segue quatro regras:

1. agir diretamente quando intenção e alvo estão claros;
2. pedir confirmação curta quando há mais de uma interpretação plausível;
3. não inventar fatos que não foram registrados;
4. não prometer lembrete sem possuir informação suficiente para executá-lo.

---

## 🗓️ Hoje, agenda futura e histórico

A visão **Hoje** reúne em um único lugar:

- aulas do dia;
- horário e local das aulas;
- tarefas;
- compromissos;
- tarefas vencidas;
- treino na academia quando aplicável;
- quantidade de itens faltando em casa.

Também permite consultar:

- ⏭️ amanhã;
- 📆 outra data;
- 🗓️ próximos 7 dias;
- 📚 histórico.

Outra data aceita `DD/MM` ou `DD/MM/AAAA`.

### Histórico diário

Permite reconstruir o que está registrado para uma data, incluindo aulas previstas, tarefas, compromissos, rotinas e treino quando houver registro.

Aulas aparecem como **previstas**, pois o Butler não presume presença sem confirmação.

### Histórico de tarefas

Tarefas são separadas em:

- ⏳ pendentes;
- ✅ concluídas;
- 🚫 canceladas.

Remover uma tarefa agora significa arquivá-la como cancelada; novos registros não são apagados fisicamente do histórico.

### Pendência

Pendência **não é um terceiro tipo de item**. É simplesmente uma tarefa cujo prazo venceu e que continua sem conclusão.

---

## ✅ Tarefas e 📅 compromissos

Além da linguagem natural, existe captura rápida por botão.

Fluxo curto:

1. informar título;
2. escolher Hoje / Outro dia / Sem data;
3. informar horário quando necessário;
4. salvar.

Não há uma sequência desnecessária de observações e configurações para ações simples.

Lembretes podem ser concluídos ou adiados. O Butler registra quantas vezes uma tarefa foi adiada e usa esse dado na personalidade.

Exemplos de comportamento contextual:

> 👀 Segunda adiada. Estou começando a reconhecer um padrão, mas vou fingir que não.

> 😏 Feito. Demorou mais do que deveria, mas chegamos lá. Não vou estragar o momento.

---

## 📚 Acadêmico

O Butler possui gerenciamento completo da grade:

- listar matérias;
- adicionar;
- remover;
- trancar;
- editar;
- persistir horários e locais;
- lembrar aulas automaticamente;
- mostrar aula, horário e sala nos resumos/agenda.

### Importação de grade

Em:

`📚 Matérias → 📥 Importar grade por PDF/texto`

aceita:

- PDF com texto pesquisável/selecionável;
- arquivo `.txt`.

O Butler procura nomes, locais e códigos de horário do SIGAA e apresenta uma prévia antes de gravar.

**Não existe OCR/Tesseract no projeto.** Imagens e PDFs escaneados devem ser convertidos previamente para PDF com texto pesquisável ou `.txt`, ou a grade pode ser cadastrada manualmente.

### Tradução de horários SIGAA

Os blocos são tratados como horas completas:

- `M23` → `08:00–10:00`;
- `M45` → `10:00–12:00`;
- `T23` → `14:00–16:00`;
- `T2345` → `14:00–18:00`;
- `N12` → `18:00–20:00`.

Correções manuais do usuário têm prioridade sobre o código original.

---

## ☀️ Resumo automático da manhã

Por padrão, às **07:30**, o Butler envia um resumo contendo o que for relevante naquele dia:

- aulas;
- horário e local;
- tarefas;
- compromissos;
- treino na academia quando aplicável;
- itens faltando em casa;
- tarefas que ficaram pendentes do dia anterior.

Exemplo de formato:

```text
☀️ Resumo da manhã

🎓 10:00 — Física II (PAV III, Sala 07)
📅 15:00 — Dentista
✅ 18:00 — Terminar relatório
🏋️ Treino na academia previsto hoje.

🛒 Faltando em casa: café, açúcar

Nada demais. Só a administração básica de uma pequena empresa chamada sua vida. 😌
```

Não existe fechamento automático noturno, pois o dia pode continuar até tarde.

---

## 📊 Fechamento semanal

Por padrão, domingo às **20:00**, o Butler apresenta um fechamento simples dos últimos dias, usando os registros disponíveis para mostrar o que foi cumprido, o que ficou aberto e sinais de evolução.

Os horários dos resumos são configuráveis por `.env`.

---

## 🕴️ Personalidade baseada em comportamento real

O Butler não deve provocar apenas por sorteio. A personalidade contextual utiliza dados registrados, como:

- número de adiamentos de uma tarefa;
- conclusão no prazo ou em atraso;
- tarefas pendentes;
- sequência de metas/rotinas;
- faltas na academia;
- evolução de carga quando comparável;
- avisos recorrentes de atraso.

A primeira ocorrência não é tratada como padrão. O sarcasmo ganha contexto conforme o histórico cresce.

Exemplos:

> 🌱 Terceira vez. A tarefa claramente criou raízes. Eu volto de novo.

> 🔥 10 dias seguidos. Isso já deixou de ser acidente estatístico. Continue.

> 👀 Segunda falta no protocolo. Ainda administrável. Só não vamos transformar exceção em calendário.

Em Day-off e contextos sensíveis, a cobrança é reduzida.

---

## 🔥 Metas e sequências

Em `🎯 Metas → 🔥 Sequências`, o Butler acompanha de forma leve, semelhante à ideia de streak de aplicativos como Duolingo:

- 🇬🇧 Inglês;
- 💻 Programação;
- 💧 Água;
- 🥗 Alimentação;
- 🏋️ Musculação.

Exibe:

- sequência atual;
- melhor sequência;
- total de dias registrados;
- visual dos últimos 7 dias.

No Butler pessoal, musculação usa diretamente treinos realmente concluídos, evitando exigir registro duplicado.

---

## 🏋️ Musculação

### Butler pessoal

Existe um protocolo interno de 12 semanas com:

- `🚀 Começar os trabalhos` para iniciar oficialmente;
- acompanhamento do dia e da semana;
- exercícios previstos;
- exercícios substitutos;
- registro série por série;
- carga e repetições realizadas;
- histórico de evolução de carga;
- faltas com motivo;
- progresso semanal;
- opção temporária de reiniciar durante testes.

Para o usuário, a linguagem do Butler usa apenas **“treino na academia”**; o nome interno do protocolo não precisa aparecer nas mensagens comuns.

Antes de `🚀 Começar os trabalhos`, o treino não aparece nos resumos e uma frase como “hoje não vou treinar” não gera falta no protocolo.

### Butler genérico

Não recebe a rotina pessoal. Musculação começa vazia e pode ser cadastrada pelo próprio usuário com dia, exercícios, carga, séries e repetições.

---

## 🛒 Casa / itens faltando

A lista de feira é persistente e pensada como uma memória da casa, não como uma lista descartável criada a cada ida ao mercado.

É possível adicionar rapidamente:

```text
sal
sal, açúcar, café
falta sal, açúcar, café
café | 2 pacotes
```

Quantidade é opcional.

Depois basta perguntar:

```text
o que falta em casa?
```

ou usar o atalho do menu.

---

## 💰 Finanças simples

O módulo financeiro foi mantido propositalmente pequeno.

### Funcionalidades

- ➕ entrada;
- ➖ saída/gasto;
- categorias;
- descrição opcional;
- relatório mensal;
- saldo baseado no que foi registrado;
- comparação com mês anterior;
- alertas simples de excesso.

Categorias iniciais:

- Alimentação;
- Transporte;
- Lazer;
- Compras;
- Renda;
- Outros.

Existem limites predefinidos simples para algumas categorias. Eles servem apenas como alerta inicial, não como sistema completo de orçamento.

O Butler também deixa claro quando os dados são insuficientes. Ele não tenta produzir uma análise financeira confiável se o usuário não registrar entradas e saídas.

Não fazem parte desta versão:

- cartões;
- parcelas;
- investimentos;
- múltiplas contas bancárias;
- orçamento financeiro complexo.

---

## 🌙 Day-off

Day-off representa um dia em que o usuário não quer cobranças ou não está disponível para a rotina normal.

Enquanto ativo, o Butler silencia lembretes/cobranças previstos para esse contexto e reduz o sarcasmo.

A reativação pode ser feita chamando novamente o Butler.

Na versão multiusuário, Day-off é isolado por `chat_id`: um usuário não silencia o bot dos outros.

---

# Butler pessoal x Butler genérico

## Butler pessoal

Executado por:

```bash
python -m src.main
```

Mantém:

- grade acadêmica inicial;
- correções pessoais de horário;
- protocolo de academia de 12 semanas;
- histórico pessoal;
- banco local `data/butler.db`.

### Grade pessoal inicial

| Matéria | Dia | Horário | Local |
|---|---|---|---|
| Álgebra Linear I | Terça e quinta | 10:00–12:00 | PAV III, Sala 10 |
| Física II | Segunda e quarta | 10:00–12:00 | PAV III, Sala 07 |
| Laboratório de Sistemas Digitais I | Segunda | 14:00–16:00 | PAV Eng., Sala D6 |
| Princípios de Eletrônica Analógica | Terça e quinta | 08:00–10:00 | PAV I, Sala 104 |
| Sistemas Digitais I | Segunda | 08:00–10:00 | PAV I, Sala 11 |
| Sistemas Digitais I | Quarta | 08:00–10:00 | PAV I, Sala 114 |

## Butler genérico / multiusuário

Executado por:

```bash
python -m src.main_generic
```

A versão genérica:

- nasce sem grade pessoal;
- nasce sem o protocolo pessoal de musculação;
- pergunta no `/start` como o usuário quer ser chamado;
- aceita importação da própria grade;
- permite cadastrar a própria musculação;
- identifica cada conversa pelo `chat_id`;
- mantém dados de usuários diferentes isolados.

No rolling local, cada chat usa um SQLite próprio em `data/butler_generic_users/` e existe um pequeno registro central dos chats conhecidos.

Essa implementação é adequada ao desenvolvimento e ao volume pequeno esperado. Na hospedagem, a regra de domínio permanece: **cada dado pertence ao usuário/chat correto**.

---

# Arquitetura funcional

Os principais módulos incluem:

- `database.py` — grade/usuários;
- `daily_store.py` — tarefas e compromissos;
- `home_store.py` — casa, metas, rotinas e musculação genérica;
- `protocol_mass_store.py` — protocolo pessoal de academia;
- `finance_store.py` — finanças;
- `assistant_state.py` — estado do assistente/Day-off;
- `scheduler.py` — lembretes e resumos locais;
- `summary_engine.py` — construção dos resumos;
- `behavior_engine.py` — comportamento contextual;
- `personality.py` — tom/persona;
- `natural_language.py` — interpretação determinística de texto;
- `natural_handlers.py` — execução das intenções naturais;
- `natural_store.py` — eventos comportamentais auxiliares;
- `user_scope.py` — isolamento multiusuário no rolling local.

A linguagem natural **não cria uma segunda regra de negócio**: ela traduz a fala e chama os mesmos stores utilizados pelos botões.

---

# Execução local

## Butler pessoal

```bash
git pull origin main
pip install -r requirements.txt
python -m src.main
```

## Butler genérico

Windows:

```bash
copy .env.generic.example .env.generic
# configure TELEGRAM_BOT_TOKEN
python -m src.main_generic
```

Linux/macOS:

```bash
cp .env.generic.example .env.generic
# configure TELEGRAM_BOT_TOKEN
python -m src.main_generic
```

---

# Smoke test da linguagem natural

Existe um teste rápido para as intenções críticas:

```bash
python scripts/nlu_smoke.py
```

Resultado esperado:

```text
NLU smoke OK
```

Ele cobre exemplos de compromisso, tarefa, agenda, mercado, treino, atraso, finanças e bloqueio temporal.

---

# Próxima etapa: produção no Cloudflare

O rolling local usa recursos que não devem ser simplesmente copiados para produção. A próxima etapa técnica será adaptar a infraestrutura mantendo as regras já consolidadas.

Plano:

1. trocar polling do Telegram por webhook;
2. migrar persistência SQLite para Cloudflare D1 ou camada persistente equivalente;
3. preservar isolamento por `chat_id`;
4. substituir/adaptar JobQueue para mecanismo de agendamento compatível com Cloudflare;
5. migrar secrets/configurações de `.env` para o ambiente de produção;
6. testar lembretes, resumo matinal e fechamento semanal;
7. validar Butler pessoal;
8. validar pelo menos dois `chat_id` distintos no modo genérico;
9. só então considerar o rolling local encerrado.

A prioridade da migração é **não alterar o comportamento funcional já validado**. Primeiro levamos o Butler atual para produção; novas funcionalidades ficam para depois do deploy estável.
