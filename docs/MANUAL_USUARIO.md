# Butler — Manual do Usuário

**Data-base:** 01/09/2026

Butler é um assistente pessoal multiusuário no Telegram. Ele organiza tarefas, compromissos, rotinas, metas, universidade, estudo, cursos, musculação, itens faltando, cardápio do RU, clima e listas para depois.

O Butler tenta aceitar texto natural, mas mudanças importantes continuam sendo determinísticas. Quando uma ação é ambígua ou exige confirmação, o bot pergunta antes de gravar.

---

## 1. Menu principal atual

```text
➕ Adicionar      🗓️ Hoje
🛒 Item faltando  📚 Matérias
🏠 Cotidiano      🏋️ Musculação
📘 Cursos
📖 Manual
🌙 Day-off
```

Esse menu ainda será reorganizado por áreas da vida no fechamento da Etapa 4. As funções abaixo já estão disponíveis independentemente dessa futura reorganização.

`🌙 Day-off` fica sozinho na última linha para diminuir toque acidental.

---

## 2. Comandos de ajuda

Você pode usar:

```text
/manual
/ajuda
manual
📖 Manual
```

O manual só deve abrir quando a intenção de ajuda é explícita. Falar `Cotidiano`, `Matérias` ou `Musculação` como ação normal não deve ser sequestrado pela ajuda.

---

## 3. Cotidiano

Abra `🏠 Cotidiano` para acessar tarefas, compromissos, rotinas, metas, itens faltando, Ler/Ver Depois e RU.

### Tarefas

Use `✅ Tarefas` para ver as tarefas ativas. Quando o bot mostrar uma lista numerada, você pode responder pelo número exibido naquele momento.

Exemplos de linguagem natural:

```text
preciso entregar o relatório amanhã às 18h
me lembra de pagar a conta sexta às 10h
```

A posição `1`, `2`, etc. deve continuar apontando para a lista que você realmente viu durante aquele fluxo.

Ações como concluir, adiar ou remover pedem o alvo quando necessário. Ao adiar uma tarefa, depois de escolher a tarefa basta informar a nova data/horário; o Butler não deve pedir a tarefa novamente.

### Compromissos

Use `📅 Compromissos` para listar. Para criar, use `📅 Compromisso` ou uma frase clara, por exemplo:

```text
amanhã tenho dentista às 15h
reunião sexta às 9h
```

Compromissos pendentes continuam visíveis. Concluídos/cancelados deixam a tela operacional depois de uma janela curta, mas o histórico não é apagado.

### Rotinas

Abra `🧘 Rotinas` para listar, criar, marcar como feita, editar ou remover rotinas.

O Butler não deve considerar uma rotina feita apenas porque o horário passou. O registro depende do fluxo/ação correspondente.

### Metas

Abra `🎯 Metas` para criar e acompanhar metas de hábito, numéricas e de projeto.

Exemplos:

```text
quero criar uma meta de estudar inglês
quero perder 5 kg
quero terminar o projeto X
```

Ações disponíveis incluem registrar progresso, editar, concluir, remover e, quando aplicável, vincular uma rotina. Em listas filtradas, a numeração se refere ao conjunto mostrado na tela.

---

## 4. Itens faltando

Use:

```text
🛒 Item faltando
➕ Item faltando
🛒 O que está faltando?
```

Exemplos:

```text
acabou o café
está faltando açúcar
```

A lista é persistente e pessoal por usuário.

---

## 5. Ler/Ver Depois

A lista simples de coisas para consumir no futuro possui categorias como:

```text
📚 Livros
🎬 Filmes
🎓 Cursos
🗂️ Outras
```

Ela funciona como backlog simples.

**`🎓 Cursos` aqui não é o mesmo que `📘 Cursos` do menu principal.** Use Ler/Ver Depois quando você só quer guardar o nome de um curso para talvez fazer futuramente. Use `📘 Cursos` quando quer acompanhar módulos, conteúdos e progresso.

---

## 6. Restaurante Universitário

Abra `🍽️ RU` no Cotidiano.

Consultas disponíveis incluem:

```text
🍽️ Cardápio de hoje
📅 Cardápio da semana
🗃️ Cardápios anteriores
```

O cardápio é compartilhado para leitura entre usuários. A atualização/importação do arquivo fica restrita ao proprietário enquanto essa política estiver ativa.

---

## 7. Matérias e universidade

Abra `📚 Matérias` para acessar o domínio acadêmico.

O Butler trabalha com matérias e seus horários, além de provas e presença/faltas conforme os fluxos disponíveis.

### Importar grade

O formato recomendado vem do painel do SIGAA contendo informações como:

```text
Componente Curricular | Local | Horário
```

São aceitos:

- PDF com texto pesquisável/selecionável;
- arquivo TXT.

O fluxo usa extração, validação, prévia e confirmação antes da persistência. PDF escaneado/imagem não é o formato oficial; o Butler não depende de OCR para essa importação.

### Presença

Aula prevista **não significa presença**. O Butler nunca deve presumir presença apenas porque uma aula ocorreu ou porque você disse que pretende ir.

Registros de ausência/presença seguem os fluxos explícitos existentes.

---

## 8. Alertas rápidos e cronômetros

O Butler possui auxiliares temporais persistentes para pedidos como:

```text
cronometra 20 minutos
me avisa daqui a 10 minutos
```

Esses alertas rápidos não viram tarefas em `daily_items`.

O runtime usa Cron + Durable Objects para reduzir dependência de um único relógio. Isso é detalhe interno; para você, o importante é que o alerta é um recurso temporal separado da lista de tarefas.

---

## 9. Modo Estudo

O Modo Estudo trabalha com sessões e tópicos.

Exemplo conceitual:

```text
Matéria: Cálculo
Tópicos:
1. Limites
2. Derivadas
3. Integrais
```

Regra central:

**o fim do tempo de foco não conclui o tópico.**

Concluir ou pular um tópico precisa ser explícito. Pausar, reiniciar, encerrar um foco ou entrar em Day-off não deve inventar progresso.

---

## 10. Cursos estruturados

Abra:

```text
📘 Cursos
```

O menu atual oferece:

```text
📚 Meus cursos
➕ Novo curso
📥 Importar curso
🗄️ Cursos arquivados
```

Um curso estruturado pode conter:

```text
Curso
├── Módulos
│   └── Conteúdos
│       ├── Materiais
│       └── Atividades
└── Histórico/progresso
```

### Criar curso

Ao usar `➕ Novo curso`, o Butler pergunta:

1. nome;
2. modo `Autogerido` ou `Ao vivo`;
3. descrição opcional.

Você pode depois criar/renomear módulos, criar/editar conteúdos e arquivar/reativar o curso.

Curso arquivado preserva estrutura e histórico.

### Autogerido x Ao vivo

**Autogerido:** `Continuar curso` segue a ordem dos módulos/conteúdos persistidos.

**Ao vivo:** o próximo conteúdo respeita o calendário (`scheduled_at`) registrado. Uma aula perdida não desloca automaticamente o curso inteiro.

### Progresso

Na tela do curso existem ações como:

```text
▶️ Continuar curso
📊 Progresso
🏁 Concluir curso
```

Na tela de conteúdo:

```text
✅ Concluir conteúdo
⏭️ Pular conteúdo
↩️ Voltar para pendente
```

Regras importantes:

- abrir um conteúdo não o conclui;
- `▶️ Continuar curso` apenas abre o próximo pendente;
- passar tempo estudando não conclui conteúdo;
- `skipped` conta como resolvido, mas não como concluído/aprendido;
- resolver o último conteúdo não conclui o curso automaticamente;
- concluir o curso exige ação explícita e confirmação.

### Estudar um conteúdo no Modo Estudo

Quando um conteúdo está pendente em curso ativo, pode aparecer:

```text
🧠 Estudar no Modo Estudo
```

Isso cria uma sessão de estudo ligada ao conteúdo. Porém:

**terminar o foco, o tópico ou a sessão não marca o conteúdo do curso como concluído.**

Depois de estudar, marque `✅ Concluir conteúdo` somente se a conclusão realmente aconteceu.

Se já houver uma sessão de estudo ativa/pausada, o Butler não substitui essa sessão silenciosamente.

### Importar curso

Use:

```text
📥 Importar curso
```

Você pode enviar:

- `.txt`;
- PDF com texto pesquisável;
- texto colado diretamente.

Formato explícito:

```text
CURSO: Java + Spring
TIPO: AUTOGERIDO
DESCRICAO: Trilha backend
[MÓDULO] Fundamentos
[CONTEÚDO] REST Controllers | aula
[MATERIAL] Slides | link | https://exemplo.com
[ATIVIDADE] Exercícios | implementar GET /health
```

Para curso ao vivo:

```text
TIPO: AO VIVO
[CONTEÚDO] Aula síncrona | aula | 15/09/2026 19:30
```

O Butler **não tenta adivinhar linhas ambíguas**. Se não conseguir associar uma linha com segurança, pede correção.

Antes de salvar, sempre mostra uma prévia. Nada é persistido até você escolher:

```text
✅ Confirmar importação
```

PDF sem texto pesquisável é recusado; OCR não faz parte deste fluxo.

Todos os conteúdos e atividades importados começam pendentes. O arquivo não pode inventar que algo já foi aprendido/concluído.

---

## 11. Musculação

Abra `🏋️ Musculação` para os fluxos de treino.

O Butler registra carga/repetições apenas quando esses dados foram informados. Ausência de treino não cria séries fictícias. Substituição de exercício deve preservar rastreabilidade do original.

Perfis pessoais/protocolos específicos não devem ser aplicados automaticamente a outro usuário.

---

## 12. Hoje, agenda e clima

`🗓️ Hoje` combina informações operacionais do dia conforme disponibilidade, como agenda/pendências e previsão do tempo.

O Butler usa Open-Meteo para dados objetivos. Comentários mais humanos sobre o clima podem ser acrescentados, mas temperatura, chuva, vento e probabilidades não podem ser inventados.

Se o serviço meteorológico falhar, a agenda não deve desaparecer por causa disso.

---

## 13. Day-off

`🌙 Day-off` serve para sinalizar um dia em que determinadas cobranças/notificações devem respeitar a política de descanso.

Ele não deve apagar histórico nem concluir automaticamente tarefas, rotinas, tópicos ou conteúdos.

O botão fica isolado na última linha do menu para diminuir acionamento acidental.

---

## 14. Linguagem natural e contexto curto

Exemplos de frases que o Butler pode entender conforme o domínio:

```text
me lembra de entregar o relatório amanhã às 18h
amanhã tenho dentista às 15h
acabou o café
segunda não vou pra Sistemas Digitais
hoje não vou conseguir treinar
cria uma rotina de estudar inglês
```

O contexto curto permite referências recentes como:

```text
essa
a segunda
a anterior
```

quando existe um alvo seguro.

Correções como:

```text
não, 16h
quinta não, sexta
```

podem atualizar o item recém-criado sem duplicá-lo quando o contexto é claro.

Regra permanente:

**entender o texto não significa autorização automática para gravar qualquer coisa.**

---

## 15. Cancelar e voltar

Fluxos guiados devem oferecer `Cancelar` e/ou `Voltar` quando fizer sentido.

Se estiver em uma criação/importação e desistir, use o botão de cancelamento exibido ou `/cancelar` quando o fluxo aceitar esse comando.

O Butler deve limpar o estado temporário em cancelamentos válidos para não capturar a próxima conversa por engano.

---

## 16. Administração

Algumas ações são exclusivas do proprietário, como diagnósticos e manutenção de conteúdo compartilhado.

Exemplos administrativos podem incluir:

```text
/status runtime
/status usuarios
/aviso ...
```

Ações exclusivas não devem ficar disponíveis operacionalmente para usuários comuns.

---

## 17. Privacidade operacional

Dados pessoais são isolados por usuário no banco. Um usuário não deve conseguir listar ou alterar tarefas, metas, cursos, estudos ou outros registros de outra conta.

Os registros de erro de runtime guardam metadados técnicos, não o texto completo da conversa.

---

## 18. Limites atuais

- Broad NLU/Library genérica não governa o webhook de produção;
- IA/Groq está planejada somente para depois do roadmap principal e do gate de estabilidade;
- importações oficiais de acadêmico/cursos não dependem de OCR;
- o menu ainda será reorganizado por áreas da vida antes da Etapa 5;
- recursos futuros de Inbox/Projetos/Memória seletiva ainda não devem ser tratados como prontos.

Para o estado técnico exato consulte `docs/STATUS_ATUAL.md`.
