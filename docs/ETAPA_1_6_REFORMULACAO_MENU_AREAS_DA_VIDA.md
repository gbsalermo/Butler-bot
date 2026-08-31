# Etapa 1.6 — Reformulação do menu por áreas da vida

**Status:** ⏳ planejada  
**Execução:** depois da conclusão da Etapa 1.5 e antes de considerar a Etapa 1 encerrada  
**Tipo:** revisão de UX/organização, sem alterar as regras de negócio dos domínios  
**Motivação:** o menu operacional cresceu junto com as funcionalidades e começou a ficar visualmente fragmentado e difícil de entender.

> Esta etapa NÃO substitui nem antecipa a 1.4/1.5. Ela entra como revisão final da experiência de navegação da Etapa 1 antes de avançar para a Etapa 2.

---

## Objetivo

Reorganizar os menus do Butler por **áreas da vida**, em vez de expor no mesmo nível uma coleção crescente de funções e CRUDs.

O usuário deve conseguir pensar:

```text
quero ver algo da faculdade
quero cuidar do cotidiano/casa
quero ver treino/saúde
quero organizar tarefas e compromissos
quero acessar lazer/interesses
```

sem precisar lembrar em qual submenu técnico cada recurso foi colocado.

A linguagem natural continua sendo o caminho principal sempre que a intenção estiver clara; o menu funciona como navegação segura, descoberta e fallback.

---

## Problema atual

O Butler já possui tarefas, compromissos, rotinas, metas, mercado, matérias, provas, presença, musculação, Ler/Ver Depois, RU, clima, Day-off e outros recursos.

Mesmo com uma única autoridade de menu (`operational_menu.py`), o crescimento funcional tende a produzir:

- muitos botões no mesmo nível;
- funções relacionadas separadas em menus diferentes;
- dificuldade para descobrir onde uma ação está;
- duplicação de botões de entrada;
- menus que refletem a implementação interna mais do que a vida do usuário;
- maior risco de o menu ficar ainda mais confuso com Projetos, Estudos, Cursos e Inbox nas etapas futuras.

A revisão deve ocorrer ANTES que essas expansões aumentem ainda mais o problema.

---

## Direção de UX

A estrutura final deve ser definida após inventário e protótipo, mas a organização deve partir de áreas humanas, não de módulos técnicos.

Exemplo inicial para estudo — **não tratar como layout fechado**:

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
│   └── futuros modos de estudo/cursos
│
├── 🏡 Casa & Cotidiano
│   ├── Itens faltando / mercado
│   ├── clima quando fizer sentido no contexto
│   └── futuras rotinas domésticas
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

Esse desenho é apenas um ponto de partida para avaliação. A etapa deve decidir quais áreas realmente reduzem atrito e quais funções precisam de atalho na tela inicial.

---

## Regras da reformulação

1. **Não quebrar linguagem natural.** `qual o almoço hoje?`, `o que tenho hoje?`, `acabou café`, etc. continuam funcionando sem navegar pelo menu.
2. **Não duplicar autoridades.** `operational_menu.py` continua sendo a fonte central de menus enquanto a arquitetura atual vigorar.
3. **Preservar ações globais.** `Voltar`, `Cancelar`, `Menu principal` e equivalentes devem ter comportamento consistente.
4. **Não expor implementação interna.** O usuário deve ver áreas e ações, não nomes técnicos de handlers, schemas ou módulos.
5. **Permissões afetam visibilidade.** Funções exclusivas do proprietário/admin não devem poluir menus de usuários comuns.
6. **Botão não substitui frase natural.** Menu é suporte e descoberta, não obrigatoriedade.
7. **Evitar profundidade excessiva.** Não trocar um menu largo por uma árvore de cinco níveis.
8. **Atalhos precisam ser deliberados.** `Hoje` e outras funções de uso muito frequente podem permanecer na primeira tela mesmo pertencendo a uma área.
9. **Day-off deve permanecer difícil de acionar por engano.** A posição e confirmação precisam continuar protegendo contra toque acidental.
10. **Cada mudança visual precisa de regressão de navegação.** Não basta o botão aparecer: voltar/cancelar/estado também precisam funcionar.

---

## Trabalho previsto

### 1. Inventário do menu atual

Mapear todos os botões e pontos de entrada realmente ativos:

- menu principal;
- Cotidiano;
- Adicionar;
- Acadêmico;
- Rotinas;
- Metas;
- Musculação;
- RU;
- Ler/Ver Depois;
- navegação global;
- fluxos exclusivos do proprietário.

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

Criar de 4 a 6 áreas principais no máximo.

Critério: o usuário deve prever onde uma função está sem conhecer a arquitetura do Butler.

### 3. Definição da tela inicial

Avaliar quais elementos merecem ficar na raiz por frequência.

Candidatos a atalho:

- `🗓️ Hoje`;
- adicionar algo rapidamente;
- áreas principais;
- Day-off em posição protegida.

Não preencher a raiz com um botão para cada módulo.

### 4. Protótipo textual antes do código

Antes de alterar `operational_menu.py`, documentar pelo menos duas propostas completas de teclado e comparar:

- quantidade de toques para tarefas comuns;
- clareza dos nomes;
- profundidade;
- redundância;
- comportamento para usuário comum × proprietário.

### 5. Migração sem quebra

Durante a troca:

- manter frases naturais;
- aceitar botões antigos quando possível por um período curto;
- não deixar estados guiados sem caminho de volta;
- atualizar `BASE_BUTTONS`/navegação global quando necessário;
- revisar mensagens que instruem caminhos antigos.

### 6. Revisão das mensagens de menu

A reformulação inclui os textos apresentados ao abrir cada área.

Evitar mensagens como listas de features. Preferir contextualizar a área de maneira curta e útil.

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
```

---

## O que NÃO faz parte desta etapa

- criar novas funcionalidades só para preencher áreas;
- reescrever toda a arquitetura do dispatcher;
- religar NLU ampla;
- criar app/web/Telegram Mini App;
- mover regras de negócio entre domínios sem necessidade;
- transformar cada área em um novo módulo técnico apenas por organização visual.

A mudança é principalmente de **arquitetura de informação e navegação**.

---

## Gate de saída

- [ ] inventário completo dos menus ativos;
- [ ] todas as funções classificadas por área da vida;
- [ ] no máximo 4–6 áreas principais, salvo justificativa forte;
- [ ] dois protótipos comparados antes da implementação;
- [ ] layout final validado pelo usuário;
- [ ] menu principal mais simples que o atual;
- [ ] ações frequentes continuam rápidas;
- [ ] usuário comum não vê ações exclusivas do proprietário;
- [ ] linguagem natural continua independente do menu;
- [ ] voltar/cancelar funcionam em todos os fluxos revisados;
- [ ] mensagens com caminhos antigos atualizadas;
- [ ] regressões de navegação verdes;
- [ ] documentação oficial atualizada com o novo mapa.

---

## Critério de sucesso

A reformulação será considerada bem-sucedida quando uma pessoa que não conhece o código do Butler conseguir localizar as funções pensando em **qual parte da vida quer organizar**, e não em qual módulo técnico precisa abrir.

O objetivo não é ter o menor número possível de botões. É ter uma estrutura previsível, limpa e que continue fazendo sentido quando o Butler ganhar mais recursos nas etapas seguintes.
