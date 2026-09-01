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

Menu:

```text
📅 Compromissos
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

---

# 5. Alertas rápidos e cronômetros

Use para minutos ou poucas horas a partir de agora. Eles não criam tarefa na agenda.

## Alerta rápido

```text
me lembra de desligar o ovo daqui a 5 minutos
me avisa daqui a 20 minutos de olhar o forno
tenho que ligar para João daqui a 10 minutos
```

## Cronômetro

```text
cronometra 30 minutos
cronometra 45 segundos
inicia um timer de 10 minutos
```

## Cancelar

```text
cancelar timer
cancelar timer #12
```

Limite atual de alerta rápido: de 1 segundo até 24 horas. Para datas posteriores, use um lembrete normal.

Responder ao aviso com `valeu`, `desliguei`, `feito`, `já foi` e semelhantes é opcional. Quando o contexto ainda estiver recente, o Butler pode apenas reconhecer e encerrar naturalmente.

---

# 6. Modo Estudo

O Modo Estudo organiza ciclos de foco e pausa mantendo matéria, tópicos e histórico.

## Iniciar

```text
modo estudo Cálculo I: limites, derivadas, integrais
quero estudar Cálculo agora: limites, derivadas e integrais
```

## Tempos padrão

```text
25 min foco
5 min pausa
15 min pausa longa
```

Personalização:

```text
modo estudo 50/10/20 Cálculo I: limites, derivadas
```

Durante:

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

**O tempo acabar não conclui o tópico.** O tópico só avança quando você disser explicitamente que concluiu ou pulou.

---

# 7. Agenda

No menu principal:

```text
🗓️ Hoje
```

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

O Butler não usa OCR em produção para grade acadêmica. Antes de salvar uma importação, ele mostra uma prévia.

## Presença e faltas

O Butler não presume presença só porque a aula aconteceu.

---

# 9. Provas

Exemplos naturais:

```text
tenho prova de cálculo sexta
marca prova de física dia 15
```

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

O cardápio semanal é compartilhado; a atualização/importação fica restrita ao proprietário.

---

# 11. Rotinas

Menu:

```text
🏠 Cotidiano
→ 🧘 Rotinas
```

Você pode criar, listar, marcar realizada, editar horários/checkpoints e remover rotina.

Rotina é recorrente; tarefa é pontual.

---

# 12. Metas

Menu:

```text
🏠 Cotidiano
→ 🎯 Metas
```

O Butler suporta metas com progresso e integração com rotinas quando aplicável.

---

# 13. Lista de mercado / itens faltando

É uma lista persistente do que está faltando em casa.

Exemplos:

```text
acabou café
tô sem detergente
adiciona arroz na lista
o que está faltando?
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

**`🎓 Cursos` aqui não é o mesmo que `📘 Cursos` do menu principal.** Use Ler/Ver Depois quando você só quer guardar um curso para talvez fazer no futuro.

---

# 16. Cursos e trilhas estruturados

Menu principal:

```text
📘 Cursos
```

Use esta área quando você realmente está fazendo/acompanhando um curso e quer organizar a estrutura dele.

Menu:

```text
📘 Cursos
├── 📚 Meus cursos
├── ➕ Novo curso
└── 🗄️ Cursos arquivados
```

## Criar um curso

Ao escolher `➕ Novo curso`, o Butler pergunta:

1. nome;
2. tipo;
3. descrição opcional.

Tipos:

```text
🧭 Autogerido
→ você segue a ordem dos módulos/conteúdos no seu ritmo

📡 Ao vivo
→ conteúdos podem ter data e horário fixos
```

## Estrutura

Um curso pode ter:

```text
Curso
→ Módulos
   → Conteúdos
```

Os conteúdos podem ser:

```text
🎥 Aula
📖 Leitura
🧪 Exercício
🛠️ Projeto
🔁 Revisão
📎 Outro
```

Você pode criar/abrir módulos, renomear módulos, criar conteúdos e editar nome, tipo e data/horário dos conteúdos.

## Editar e arquivar

Na tela do curso é possível editar nome, descrição e tipo.

`🗄️ Arquivar curso` tira o curso da lista principal, mas **não apaga sua estrutura ou histórico**. Em `🗄️ Cursos arquivados`, ele pode ser reativado depois.

## Progresso nesta versão

A tela já mostra conteúdos concluídos, pulados e pendentes, mas **a Etapa atual de Cursos ainda não expõe os botões de concluir/pular/continuar**. Isso será adicionado na próxima evolução do módulo.

Navegar, abrir ou editar uma aula nunca marca progresso automaticamente.

---

# 17. Clima

Você pode perguntar:

```text
como está o tempo hoje?
vai chover amanhã?
qual a previsão de hoje?
```

O clima usa Open-Meteo.

---

# 18. Day-off

Botão:

```text
🌙 Day-off
```

O Day-off vale para o dia local em que foi ativado. Alertas rápidos/cronômetros explicitamente iniciados continuam funcionando, assim como uma sessão de estudo já iniciada.

---

# 19. Referências e correções rápidas

O Butler mantém contexto curto para frases como:

```text
muda ela pra sexta
cancela esse
conclui a segunda
```

Também entende correções recentes como:

```text
não, 16h
quinta não, sexta
na verdade é dia 16
```

Uma mudança explícita de assunto não deve ser contaminada por contexto antigo.

---

# 20. Quando usar cada tipo

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

Quero guardar um curso para talvez fazer depois
→ 🎓 Cursos em Ler/Ver Depois

Quero acompanhar um curso que estou fazendo
→ 📘 Cursos estruturados
```

---

# 21. Ajuda rápida no Telegram

Digite:

```text
/manual
```

ou:

```text
/ajuda
```

O manual interno mostra categorias e exemplos curtos sem precisar abrir este arquivo no GitHub.
