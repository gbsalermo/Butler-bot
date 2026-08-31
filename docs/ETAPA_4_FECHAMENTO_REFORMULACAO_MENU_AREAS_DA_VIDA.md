# Fechamento da Etapa 4 — Reformulação do menu por áreas da vida

**Status:** ⏳ planejada  
**Execução:** depois de concluir todo o escopo funcional da Etapa 4 e antes de iniciar a Etapa 5  
**Tipo:** revisão de UX/arquitetura de informação, sem alterar as regras de negócio dos domínios  
**Motivação:** o menu operacional cresceu junto com as funcionalidades e começou a ficar visualmente fragmentado e difícil de entender.

> Esta revisão não pertence mais à Etapa 1. Ela deve acontecer como **último trabalho da Etapa 4**, depois que Acadêmico, Auxiliares de Tempo/Modo Estudo e Cursos/Trilhas já estiverem implementados, e **antes da Etapa 5 — Caixa de entrada**.

---

## Por que no fim da Etapa 4

Reorganizar o menu agora faria o Butler passar por outra grande reorganização logo depois, quando entrarem as funcionalidades das Etapas 2, 3 e 4.

A ordem correta passa a ser:

```text
Etapa 1 — Linguagem natural + conversa real
→ Etapa 2 — Acadêmico completo + importação
→ Etapa 3 — Auxiliares de Tempo / Modo Estudo
→ Etapa 4 — Cursos e trilhas de estudo
→ REVISÃO FINAL DO MENU POR ÁREAS DA VIDA
→ Etapa 5 — Caixa de entrada
```

Assim a reformulação trabalha sobre um conjunto funcional mais maduro e pode preparar a navegação antes da segunda metade do roadmap, quando ainda entrarão Inbox, Projetos/Trabalho, priorização e memória seletiva.

---

## Objetivo

Reorganizar os menus do Butler por **áreas da vida**, em vez de expor no mesmo nível uma coleção crescente de funções e CRUDs.

O usuário deve conseguir pensar:

```text
quero ver algo da faculdade
quero estudar
quero cuidar do cotidiano/casa
quero ver treino/saúde
quero organizar tarefas e compromissos
quero acessar lazer/interesses
```

sem precisar lembrar em qual submenu técnico cada recurso foi colocado.

A linguagem natural continua independente da navegação. O menu funciona como descoberta, atalho e fallback seguro — não como caminho obrigatório.

---

## Direção de UX

A estrutura final será definida após inventário e protótipo. O exemplo abaixo é apenas ponto de partida:

```text
🏠 Início
├── 📅 Organização
│   ├── Hoje / agenda
│   ├── Tarefas
│   ├── Compromissos
│   ├── Rotinas
│   └── Metas
│
├── 🎓 Universidade & Estudos
│   ├── Matérias
│   ├── Provas
│   ├── Presença / faltas
│   ├── Restaurante Universitário
│   ├── Modo Estudo
│   └── Cursos / trilhas
│
├── 🏡 Casa & Cotidiano
│   ├── Itens faltando / mercado
│   ├── clima quando fizer sentido
│   └── rotinas domésticas
│
├── 🏋️ Saúde & Treino
│   ├── Musculação
│   ├── progresso
│   └── hábitos/metas relacionadas
│
├── 🎬 Interesses & Depois
│   └── Ler/Ver Depois
│
└── ⚙️ Butler
    ├── Como me chamar
    ├── configurações
    ├── Day-off
    └── opções administrativas quando aplicável
```

Esse desenho **não é definitivo**. A etapa deve comparar alternativas antes de alterar o runtime.

---

## Regras da reformulação

1. **Não quebrar linguagem natural.** Frases como `qual o almoço hoje?`, `o que tenho hoje?`, `acabou café` e comandos dos novos módulos continuam funcionando sem navegar pelo menu.
2. **Não duplicar autoridades.** A fonte central de menus deve continuar clara e única.
3. **Preservar ações globais.** `Voltar`, `Cancelar`, `Menu principal` e equivalentes precisam ter comportamento consistente.
4. **Organizar pela vida, não pela implementação.** O usuário não deve precisar conhecer handlers, schemas ou nomes técnicos.
5. **Permissões afetam visibilidade.** Funções exclusivas do proprietário/admin não devem aparecer para usuários comuns.
6. **Evitar profundidade excessiva.** Não trocar um menu largo por uma árvore de cinco níveis.
7. **Atalhos precisam ser deliberados.** Funções muito frequentes, como `Hoje`, podem ficar na primeira tela mesmo pertencendo a uma área.
8. **Day-off continua protegido contra toque acidental.**
9. **Cada mudança visual precisa de regressão de navegação.** Voltar, cancelar e estados guiados fazem parte do teste.
10. **Não criar funcionalidade nova só para completar uma categoria visual.**

---

## Trabalho previsto

### 1. Inventário completo dos menus

Mapear todos os botões e pontos de entrada realmente ativos ao final da Etapa 4, incluindo funcionalidades que ainda não existem hoje e serão criadas nas Etapas 2–4.

Para cada item registrar:

```text
função
frequência provável
área da vida
atalho necessário?
entrada por linguagem natural?
permissão
submenu atual
```

### 2. Agrupamento por áreas da vida

Criar preferencialmente de 4 a 6 áreas principais.

Critério: uma pessoa deve conseguir prever onde uma função está sem conhecer a arquitetura do Butler.

### 3. Definição da tela inicial

Reavaliar quais ações merecem continuar na raiz por frequência.

Candidatos:

- `🗓️ Hoje`;
- captura/adição rápida;
- acesso às áreas principais;
- Day-off em posição protegida.

### 4. Protótipos antes do código

Antes de alterar o menu real, documentar **pelo menos duas propostas completas** e comparar:

- quantidade de toques para ações frequentes;
- clareza dos nomes;
- profundidade;
- redundância;
- usuário comum × proprietário;
- impacto em Acadêmico, Modo Estudo e Cursos.

O layout final deve ser validado antes da implementação.

### 5. Migração sem quebra

Durante a troca:

- manter frases naturais;
- aceitar botões antigos quando possível durante transição curta;
- não deixar estados guiados sem caminho de volta;
- revisar `BASE_BUTTONS` e navegação global;
- atualizar mensagens que instruem caminhos antigos.

### 6. Revisão dos textos de navegação

Cada área deve ter uma mensagem curta e contextual. Evitar transformar a abertura de submenu em lista de funcionalidades.

### 7. Testes de navegação

Cobrir pelo menos:

```text
/start → área → ação → cancelar → área
/start → área → subárea → voltar → área
menu principal → Hoje
usuário comum não vê ações admin
proprietário vê ações permitidas
botão antigo não causa erro crítico
estado guiado continua recuperável
linguagem natural funciona sem abrir área
```

---

## O que NÃO faz parte desta revisão

- criar novas funcionalidades só para preencher áreas;
- reescrever todo o dispatcher;
- religar NLU ampla;
- criar app/web/Telegram Mini App;
- mover regras de negócio entre domínios sem necessidade;
- transformar cada área da vida em um novo módulo técnico apenas por organização visual.

A mudança é principalmente de **arquitetura de informação e navegação**.

---

## Gate para iniciar a Etapa 5

A **Etapa 5 não começa antes desta revisão ser concluída e validada**.

- [ ] Etapa 4 funcionalmente concluída;
- [ ] inventário completo dos menus ativos;
- [ ] funções classificadas por área da vida;
- [ ] dois protótipos comparados;
- [ ] layout final validado;
- [ ] menu principal mais previsível e menos fragmentado;
- [ ] ações frequentes continuam rápidas;
- [ ] usuário comum não vê ações exclusivas do proprietário;
- [ ] linguagem natural continua independente do menu;
- [ ] voltar/cancelar funcionam nos fluxos revisados;
- [ ] caminhos antigos nas mensagens foram atualizados;
- [ ] regressões de navegação verdes;
- [ ] documentação oficial atualizada com o mapa final.

---

## Critério de sucesso

A reformulação será bem-sucedida quando uma pessoa conseguir localizar as funções pensando em **qual parte da vida quer organizar**, e não em qual módulo técnico precisa abrir.

O objetivo não é simplesmente reduzir o número de botões. É chegar ao final da Etapa 4 com uma estrutura limpa e previsível o suficiente para receber Inbox, Projetos, priorização e memória nas etapas seguintes sem voltar a virar um menu bagunçado.
