# Butler — Manual do Usuário

**Data-base:** 03/09/2026

Butler é um assistente pessoal multiusuário no Telegram. Ele organiza tarefas, compromissos, rotinas, metas, universidade, estudo, cursos, musculação, itens faltando, caixa de entrada, cardápio do RU, clima e listas para depois.

O Butler tenta aceitar texto natural, mas mudanças importantes continuam sendo determinísticas. Quando uma ação é ambígua ou exige confirmação, o bot pergunta antes de gravar.

---

## 1. Menu principal atual

O fechamento da Etapa 4 adotou uma raiz minimalista:

```text
➕ Adicionar          🗓️ Hoje
🎓 Faculdade          📋 Minha vida
🏋️ Treino             ⚙️ Mais
🌙 Day-off
```

`🌙 Day-off` continua sozinho na última linha para diminuir toque acidental.

A navegação é organizada por contexto, mas a linguagem natural continua independente dos menus. Você não precisa abrir uma área antes de dizer algo como `qual o almoço hoje?`, `acabou café` ou `tenho prova amanhã`.

Durante a transição, alguns botões antigos ainda são aceitos como aliases, como `🏠 Cotidiano`, `🏋️ Musculação`, `🏠 Menu principal` e `⬅️ Voltar ao cotidiano`.

---

## 2. Áreas da navegação

### 🎓 Faculdade

```text
📚 Matérias           🍽️ RU
🧠 Modo Estudo        📘 Cursos
⬅️ Início
```

`📘 Cursos` estruturados está em **standby** e, por enquanto, só aparece para o proprietário. Usuários comuns continuam usando Faculdade normalmente sem enxergar essa opção.

### 📋 Minha vida

```text
✅ Tarefas            📅 Compromissos
🧘 Rotinas            🎯 Metas
📥 Inbox
🛒 Casa               📌 Interesses
⬅️ Início
```

### 🛒 Casa

```text
🛒 O que está faltando?   ➕ Item faltando
⬅️ Minha vida
```

### 📌 Interesses

É a antiga lista `Ler/ver depois`, reorganizada dentro de Minha vida:

```text
➕ Adicionar à lista   📚 Livros
🎬 Filmes             🎓 Cursos
🗂️ Outras
✏️ Editar item        🗑️ Remover item
⬅️ Minha vida
```

`🎓 Cursos` nesta tela significa apenas curso salvo para fazer/ver depois. Não é o domínio estruturado `📘 Cursos`.

### 🏋️ Treino

Abre diretamente o menu de musculação já existente. Não existe um submenu intermediário vazio.

### ⚙️ Mais

```text
👤 Como me chamar      📖 Manual
⬅️ Início
```

---

## 3. Comandos de ajuda

Você pode usar:

```text
/manual
/ajuda
manual
📖 Manual
```

O manual só deve abrir quando a intenção de ajuda é explícita. Botões normais de navegação não devem ser sequestrados pela ajuda.

---

## 4. Tarefas, compromissos, rotinas e metas

Abra `📋 Minha vida` para essas funções.

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

Use `📅 Compromissos` para listar. Para criar, use `📅 Compromisso` no atalho `➕ Adicionar` ou uma frase clara, por exemplo:

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

## 4A. Caixa de entrada / captura rápida

Use a Inbox quando você quer **guardar algo agora e decidir depois o que aquilo é**.

Pelo menu:

```text
📋 Minha vida
→ 📥 Inbox
```

ou pelo atalho:

```text
➕ Adicionar
→ 📥 Capturar na Inbox
```

Também funciona por texto quando a intenção de Inbox é explícita:

```text
joga na inbox: revisar autenticação do SGL
anota estudar cálculo pra eu organizar depois
```

Capturar na Inbox **não cria tarefa nem compromisso automaticamente**.

Dentro dela você pode:

```text
➕ Capturar
📋 Pendentes
🗄️ Arquivados
```

Ao abrir um item pendente:

```text
🧭 Processar
🗄️ Arquivar
```

Processar permite escolher explicitamente:

```text
✅ Virar tarefa
📅 Virar compromisso
```

Quando um item vira tarefa ou compromisso, ele sai dos pendentes da Inbox e fica ligado ao objeto criado. O Butler protege essa conversão contra repetição para não gerar duas tarefas iguais por causa de retry do Telegram.

Arquivar não cria nada. Um item arquivado pode ser reaberto depois.

A palavra `anota` sozinha não força uma captura na Inbox; isso evita sequestrar pedidos normais de tarefa, lembrete e outros domínios.

---

## 5. Casa e itens faltando

Abra `📋 Minha vida → 🛒 Casa` ou use o atalho `➕ Adicionar → ➕ Item faltando`.

Exemplos:

```text
acabou o café
está faltando açúcar
o que está faltando?
```

A lista é persistente e pessoal por usuário.

---

## 6. Interesses / Ler-Ver Depois

Abra `📋 Minha vida → 📌 Interesses`.

A lista simples de coisas para consumir no futuro possui categorias como:

```text
📚 Livros
🎬 Filmes
🎓 Cursos
🗂️ Outras
```

Ela funciona como backlog simples.

**`🎓 Cursos` aqui não é o mesmo que `📘 Cursos` estruturado.** Use Interesses quando você só quer guardar o nome de um curso para talvez fazer futuramente.

---

## 7. Restaurante Universitário

Abra `🎓 Faculdade → 🍽️ RU`.

Consultas disponíveis incluem:

```text
🍽️ Cardápio de hoje
📅 Cardápio da semana
🗃️ Cardápios anteriores
```

O cardápio é compartilhado para leitura entre usuários. A atualização/importação do arquivo fica restrita ao proprietário enquanto essa política estiver ativa.

---

## 8. Matérias, provas e presença

Abra `🎓 Faculdade → 📚 Matérias` para acessar o domínio acadêmico.

O menu reúne matérias, provas, faltas/presença e importação da grade. Entre as ações de prova estão adicionar, listar, editar e cancelar. A edição permite alterar nome, matéria, data e horário.

### Importar grade

O formato recomendado vem do painel do SIGAA contendo informações como:

```text
Componente Curricular | Local | Horário
```

São aceitos:

- PDF com texto pesquisável/selecionável;
- arquivo TXT.

O fluxo usa extração, validação, prévia e confirmação antes da persistência. PDF escaneado/imagem não é o formato oficial; o Butler não depende de OCR para essa importação.

### Provas e lembretes

As provas possuem lembretes de antecedência em 7, 3 e 1 dia, além do dia da prova e da última hora quando existe horário. O mecanismo pode recuperar o aviso mais tarde no mesmo dia caso uma execução pontual seja perdida, sem duplicar notificações já registradas.

### Presença

Aula prevista **não significa presença**. O Butler nunca deve presumir presença apenas porque uma aula ocorreu ou porque você disse que pretende ir.

Registros de ausência/presença seguem os fluxos explícitos existentes.

---

## 9. Alertas rápidos e cronômetros

O Butler possui auxiliares temporais persistentes para pedidos como:

```text
cronometra 20 minutos
me avisa daqui a 10 minutos
```

Esses alertas rápidos não viram tarefas em `daily_items`.

O runtime usa Cron + Durable Objects para reduzir dependência de um único relógio. Isso é detalhe interno; para você, o importante é que o alerta é um recurso temporal separado da lista de tarefas.

---

## 10. Modo Estudo

Abra `🎓 Faculdade → 🧠 Modo Estudo` para ver uma ajuda curta, consultar status/histórico ou use linguagem natural diretamente.

Exemplo:

```text
quero estudar Física agora: ondas, exercícios
```

O Modo Estudo trabalha com sessões e tópicos.

Regra central:

**o fim do tempo de foco não conclui o tópico.**

Concluir ou pular um tópico precisa ser explícito. Pausar, reiniciar, encerrar um foco ou entrar em Day-off não deve inventar progresso.

---

## 11. Cursos estruturados — standby

O domínio `📘 Cursos` continua implementado, porém está em **standby** enquanto passa por nova estabilização. Por isso, o botão fica oculto para usuários comuns e permanece visível apenas para o proprietário em `🎓 Faculdade`.

Quando habilitado para o proprietário, o menu oferece:

```text
📚 Meus cursos
➕ Novo curso
📥 Importar curso
🗄️ Cursos arquivados
```

Um curso estruturado pode conter módulos, conteúdos, materiais, atividades e histórico/progresso.

Regras importantes continuam valendo:

- abrir um conteúdo não o conclui;
- `▶️ Continuar curso` apenas abre o próximo pendente;
- passar tempo estudando não conclui conteúdo;
- `skipped` conta como resolvido, mas não como concluído/aprendido;
- resolver o último conteúdo não conclui o curso automaticamente;
- concluir o curso exige ação explícita e confirmação;
- terminar uma sessão do Modo Estudo não marca o conteúdo do curso como concluído.

### Importar curso

O importador aceita `.txt`, PDF com texto pesquisável ou texto colado diretamente. O formato é explícito:

```text
CURSO: Java + Spring
TIPO: AUTOGERIDO
DESCRICAO: Trilha backend
[MÓDULO] Fundamentos
[CONTEÚDO] REST Controllers | aula
[MATERIAL] Slides | link | https://exemplo.com
[ATIVIDADE] Exercícios | implementar GET /health
```

Antes de salvar, sempre mostra uma prévia. Nada é persistido até a confirmação explícita. PDF sem texto pesquisável é recusado; OCR não faz parte deste fluxo.

---

## 12. Treino

Abra `🏋️ Treino` na tela inicial. O botão entra direto nos fluxos de musculação.

O Butler registra carga/repetições apenas quando esses dados foram informados. Ausência de treino não cria séries fictícias. Substituição de exercício deve preservar rastreabilidade do original.

Perfis pessoais/protocolos específicos não devem ser aplicados automaticamente a outro usuário.

---

## 13. Hoje, agenda e clima

`🗓️ Hoje` continua na raiz porque é uma consulta frequente. Ele combina informações operacionais do dia conforme disponibilidade, como agenda/pendências e previsão do tempo.

O Butler usa Open-Meteo para dados objetivos. Comentários mais humanos sobre o clima podem ser acrescentados, mas temperatura, chuva, vento e probabilidades não podem ser inventados.

Se o serviço meteorológico falhar, a agenda não deve desaparecer por causa disso.

---

## 14. Adicionar rápido

`➕ Adicionar` também continua na raiz. Ele oferece atalhos para:

```text
✅ Tarefa              📅 Compromisso
🧘 Rotinas             🎯 Metas
📥 Capturar na Inbox
➕ Item faltando
⬅️ Início
```

O objetivo é permitir captura rápida sem obrigar o usuário a entrar primeiro em uma área.

---

## 15. Day-off

`🌙 Day-off` serve para sinalizar um dia em que determinadas cobranças/notificações devem respeitar a política de descanso.

Ele não deve apagar histórico nem concluir automaticamente tarefas, rotinas, tópicos ou conteúdos.

O botão fica isolado na última linha do menu para diminuir acionamento acidental.

---

## 16. Linguagem natural e contexto curto

Exemplos de frases que o Butler pode entender conforme o domínio:

```text
me lembra de entregar o relatório amanhã às 18h
amanhã tenho dentista às 15h
acabou o café
segunda não vou pra Sistemas Digitais
hoje não vou conseguir treinar
cria uma rotina de estudar inglês
joga na inbox: revisar autenticação do SGL
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

## 17. Cancelar e voltar

`⬅️ Início` sempre retorna à raiz. Dentro das áreas, os botões de volta retornam ao contexto imediatamente anterior, por exemplo `⬅️ Faculdade` ou `⬅️ Minha vida`.

Fluxos guiados continuam oferecendo `❌ Cancelar ação` e/ou `Voltar` quando fizer sentido. Cancelar limpa o estado temporário daquele fluxo para não capturar a próxima conversa por engano.

---

## 18. Administração

Algumas ações são exclusivas do proprietário, como diagnósticos, manutenção de conteúdo compartilhado e o acesso temporário a `📘 Cursos` enquanto o recurso está em standby.

Exemplos administrativos podem incluir:

```text
/status runtime
/status usuarios
/aviso ...
```

Ações exclusivas não devem ficar disponíveis operacionalmente para usuários comuns.

---

## 19. Privacidade operacional

Dados pessoais são isolados por usuário no banco. Um usuário não deve conseguir listar ou alterar tarefas, metas, cursos, estudos, Inbox ou outros registros de outra conta.

Os registros de erro de runtime guardam metadados técnicos, não o texto completo da conversa.

---

## 20. Limites atuais

- Broad NLU/Library genérica não governa o webhook de produção;
- IA/Groq está planejada somente para depois do roadmap principal e do gate de estabilidade;
- importações oficiais de acadêmico/cursos não dependem de OCR;
- `📘 Cursos` estruturados permanece em standby e owner-only até nova estabilização;
- recursos futuros de Projetos/Memória seletiva ainda não devem ser tratados como prontos.

Para o estado técnico exato consulte `docs/STATUS_ATUAL.md`.
