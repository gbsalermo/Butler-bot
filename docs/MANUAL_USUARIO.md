# Butler — Manual do Usuário

**Objetivo:** lembrar rapidamente o que o Butler sabe fazer e como pedir cada coisa no Telegram.

Este arquivo descreve o comportamento de produção do Butler. Em caso de dúvida, você também pode usar no próprio bot:

```text
/manual
/ajuda
ajuda
manual
```

---

# 1. Como falar com o Butler

Você não precisa decorar comandos para as funções principais. Frases naturais funcionam quando a intenção está clara.

Exemplos:

```text
me lembra amanhã às 15h de levar o documento
cria uma tarefa revisar cálculo amanhã às 20h
tenho dentista sexta às 14h
qual meu almoço hoje no RU?
qual meu treino hoje?
cronometra 20 minutos
```

Também existem botões para os fluxos mais comuns.

Se estiver no meio de uma ação e quiser sair:

```text
Cancelar ação
```

ou use o botão:

```text
❌ Cancelar ação
```

Para voltar:

```text
🏠 Menu principal
```

---

# 2. Tarefas

Use tarefas para coisas que precisam ser feitas e continuar pendentes até você concluir ou cancelar.

Exemplos:

```text
cria uma tarefa revisar cálculo amanhã às 20h
preciso pagar a conta amanhã
tenho que entregar o relatório sexta
```

Você pode consultar pelo menu:

```text
✅ Tarefas
```

ou perguntar naturalmente sobre sua agenda.

Depois de uma lista, referências curtas também podem funcionar:

```text
conclui a segunda
cancela a primeira
```

Depois de criar ou mencionar uma tarefa recente:

```text
muda ela pra sexta
adia isso 30 minutos
```

---

# 3. Compromissos

Use compromissos para eventos marcados, como dentista, reunião ou consulta.

Exemplos:

```text
tenho dentista amanhã às 15h
marca uma consulta sexta às 14h
cria um compromisso reunião terça às 10h
```

O Butler avisa compromissos comuns alguns minutos antes segundo a política atual.

Menu:

```text
📅 Compromissos
```

Referências curtas também podem ser usadas:

```text
muda ele pra 16h
cancela esse compromisso
```

---

# 4. Lembretes pessoais

Use lembrete quando você quer apenas ser avisado em uma data e horário, sem transformar aquilo numa tarefa permanente.

Exemplos:

```text
me lembra amanhã às 9h de levar o documento
me avisa sexta às 18h de entregar o relatório
não deixa eu esquecer amanhã às 8h de pegar a chave
```

Um lembrete pontual continua sendo apenas aviso.

---

# 5. Alertas rápidos e cronômetros

Use esta função para minutos ou poucas horas a partir de agora.

Ela não cria tarefa na agenda.

## Alerta rápido

```text
me lembra de desligar o ovo daqui a 5 minutos
me avisa daqui a 20 minutos de olhar o forno
tenho que ligar para João daqui a 10 minutos
me lembra daqui a 1 hora de tirar a roupa do varal
```

## Cronômetro

```text
cronometra 30 minutos
cronometra 45 segundos
inicia um timer de 10 minutos
começa um cronômetro de 1 hora
```

O Butler informa o número do timer quando necessário.

## Cancelar

Se houver apenas um:

```text
cancelar timer
para o cronômetro
```

Se houver vários:

```text
cancelar timer
```

O Butler lista os ativos. Depois use, por exemplo:

```text
cancelar timer #12
```

Limite atual de alerta rápido: de 1 segundo até 24 horas. Para datas posteriores, use um lembrete normal.

---

# 6. Modo Estudo

O Modo Estudo organiza ciclos de foco e pausa mantendo matéria, tópicos e histórico.

## Iniciar rapidamente

```text
modo estudo Cálculo I: limites, derivadas, integrais
```

Também pode usar:

```text
quero estudar Cálculo agora: limites, derivadas e integrais
começa o modo estudo Cálculo I: limites, derivadas
```

Se a matéria já existir no cadastro acadêmico e o nome for reconhecido com segurança, o Butler reaproveita o nome dela.

## Tempos padrão

```text
25 min foco
5 min pausa
15 min pausa longa
```

A pausa longa ocorre periodicamente durante os ciclos.

## Personalizar tempos

Formato:

```text
foco/pausa/pausa-longa
```

Exemplo:

```text
modo estudo 50/10/20 Cálculo I: limites, derivadas
```

Para testes curtos, o mínimo atual de foco é 5 minutos:

```text
modo estudo 5/1 Cálculo I: limites, derivadas
```

## Durante o estudo

```text
status estudo
não terminei
concluí o tópico
pular tópico
pausar estudo
retomar estudo
cancelar estudo
histórico de estudo
```

### Regra importante

**O tempo acabar não conclui o tópico.**

Se os 25 minutos terminarem, o Butler inicia a pausa, mas o tópico continua pendente.

O tópico só avança quando você disser explicitamente que concluiu ou pulou.

---

# 7. Agenda

No menu principal:

```text
🗓️ Hoje
```

O Butler reúne informações operacionais do dia conforme os módulos ativos.

Frases úteis:

```text
o que tenho hoje?
o que tenho amanhã?
minha agenda de hoje
qual a próxima coisa?
o que faço agora?
```

---

# 8. Matérias e faculdade

Menu:

```text
📚 Matérias
```

Você pode cadastrar, visualizar e gerenciar matérias e horários.

## Importar grade no primeiro acesso

Fonte recomendada no SIGAA:

```text
Componente Curricular | Local | Horário
```

Formatos aceitos:

- PDF com texto pesquisável/selecionável;
- TXT.

O Butler não usa OCR em produção para grade acadêmica.

Antes de salvar uma importação, ele mostra uma prévia. Se houver trecho ambíguo, nada é persistido até revisão.

## Presença e faltas

O Butler não presume presença só porque a aula aconteceu.

Você pode acompanhar faltas pelo módulo acadêmico e responder aos avisos de aula quando eles forem enviados.

---

# 9. Provas

Exemplos naturais:

```text
tenho prova de cálculo sexta
marca prova de física dia 15
```

Provas possuem tratamento acadêmico próprio e lembretes específicos.

---

# 10. Restaurante Universitário — RU

Menu:

```text
🏠 Cotidiano
→ 🍽️ RU
```

Consultas úteis:

```text
qual o almoço hoje?
qual o café amanhã?
cardápio de hoje
cardápio da semana
```

O cardápio semanal é compartilhado para os usuários do Butler.

A atualização/importação do cardápio fica restrita ao proprietário.

---

# 11. Rotinas

Menu:

```text
🏠 Cotidiano
→ 🧘 Rotinas
```

Você pode:

- criar rotina;
- listar rotinas;
- marcar rotina realizada;
- editar horários/checkpoints;
- remover rotina.

Rotina é recorrente. Tarefa é uma obrigação pontual. Não use uma no lugar da outra se quiser histórico coerente.

---

# 12. Metas

Menu:

```text
🏠 Cotidiano
→ 🎯 Metas
```

O Butler suporta metas com progresso e integração com rotinas quando aplicável.

Ações disponíveis pelo menu incluem criação, listagem, registro de progresso, edição, conclusão e remoção.

---

# 13. Lista de mercado / itens faltando

O objetivo não é montar uma compra única. É manter uma lista persistente do que está faltando em casa.

Exemplos:

```text
acabou café
tô sem detergente
adiciona arroz na lista
```

Para consultar:

```text
o que está faltando?
```

ou use:

```text
🛒 O que está faltando?
```

---

# 14. Musculação

Menu:

```text
🏋️ Musculação
```

Funções principais:

```text
📅 Treino de hoje
🚀 Começar os trabalhos
📝 Registrar série
🔁 Substituir exercício
✅ Finalizar treino
😕 Não consegui treinar hoje
📈 Progresso
```

O Butler registra apenas o que você informar. Ele não inventa carga, repetição ou conclusão.

Também mantém referências de cargas e exercícios substitutos quando disponíveis no protocolo configurado.

---

# 15. Ler / Ver Depois

Menu:

```text
🏠 Cotidiano
→ 📌 Ler/ver depois
```

Categorias atuais:

```text
📚 Livros
🎬 Filmes
🎓 Cursos
🗂️ Outras
```

Essa lista serve como backlog simples.

**A categoria Cursos aqui não é o módulo completo de Cursos e Trilhas**, que pertence à evolução posterior do Butler.

---

# 16. Clima

Você pode perguntar naturalmente:

```text
como está o tempo hoje?
vai chover amanhã?
qual a previsão de hoje?
```

O clima usa Open-Meteo e pode ser combinado com a agenda/resumo diário.

---

# 17. Day-off

Use quando quiser suspender o comportamento normal do Butler naquele dia.

Botão:

```text
🌙 Day-off
```

O Day-off vale para o dia local em que foi ativado e não transforma automaticamente finais de semana em folga.

Alertas rápidos/cronômetros explicitamente iniciados continuam funcionando, assim como uma sessão de estudo já iniciada.

Para voltar ao comportamento normal, use os fluxos de reativação disponíveis no Butler.

---

# 18. Referências e correções rápidas

O Butler mantém contexto curto para frases como:

```text
muda ela pra sexta
cancela esse
conclui a segunda
```

Também entende correções recentes em vários fluxos:

```text
não, 16h
quinta não, sexta
na verdade é dia 16
```

O contexto é curto e isolado por usuário. Uma nova ação explícita em outro assunto não deve ser contaminada por contexto antigo.

---

# 19. Quando usar cada tipo

```text
Tenho algo para fazer e quero manter pendente
→ Tarefa

Tenho evento marcado
→ Compromisso

Quero só um aviso numa data/hora
→ Lembrete

Quero aviso daqui a alguns minutos/horas
→ Alerta rápido

Quero contar uma duração
→ Cronômetro

Quero estudar com foco/pausa e acompanhar tópicos
→ Modo Estudo

Quero hábito recorrente
→ Rotina

Quero acompanhar objetivo/progresso
→ Meta
```

---

# 20. Ajuda rápida no Telegram

A forma mais simples de lembrar como usar é digitar:

```text
/manual
```

ou:

```text
/ajuda
```

O manual interno mostra as categorias principais e exemplos curtos sem precisar abrir este arquivo no GitHub.
