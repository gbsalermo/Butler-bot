# Etapa 5.5 — ⚡ Usabilidade Operacional

**Status:** ▶️ em andamento  
**Posição:** depois da Etapa 5 — Caixa de entrada e antes da Etapa 6 — Projetos e trabalho  
**Objetivo:** transformar os recursos já existentes em fluxos rápidos, naturais e confortáveis para uso diário antes de ampliar o produto com novos domínios.

---

## Por que esta subetapa existe

O Butler já possui bastante funcionalidade, mas o uso real ainda expõe atrito operacional:

- criação e manutenção de rotinas ainda depende demais de fluxos guiados;
- editar dados simples pode exigir navegar por várias telas;
- tarefas e outros itens são resolvidos um por vez mesmo quando o pedido é claramente em lote;
- confirmações simples frequentemente devolvem texto demais;
- alguns fluxos encerram a ação e obrigam o usuário a entrar novamente no mesmo domínio para continuar trabalhando.

O gate desta subetapa passa a medir não apenas **“a funcionalidade existe?”**, mas também **“é confortável usar isso todos os dias?”**.

A Etapa 6 fica bloqueada até o fechamento deste gate.

---

# 5.5.1 — Rotinas múltiplas e criação contínua ▶️

Objetivo:

- permitir várias rotinas ativas para o mesmo usuário sem sobrescrever nem bloquear umas às outras;
- permitir criação consecutiva sem exigir retorno ao menu principal;
- reconhecer pedidos naturais de continuação como `cria outra rotina...`, `adiciona mais uma rotina...` e equivalentes;
- manter lembretes, conclusão e edição isolados por `routine_id`;
- preservar histórico individual de cada rotina.

Gate:

- [ ] criar pelo menos 3 rotinas distintas em sequência;
- [ ] listar todas as rotinas ativas;
- [ ] editar uma sem alterar as demais;
- [ ] concluir uma sem concluir as demais;
- [ ] scheduler processar cada rotina independentemente;
- [x] parser reconhecer `outra rotina` / `mais uma rotina` como continuação válida;
- [ ] regressão integrada do fluxo completo.

Primeiro incremento iniciado nesta subetapa:

```text
cria uma rotina de Estudar inglês...
cria outra rotina de Academia...
adiciona mais uma rotina Curso DIO...
```

Todos os pedidos acima devem entrar no mesmo fast path conservador de criação de rotinas.

---

# 5.5.2 — Edição direta

Objetivo: permitir alterações simples sem obrigar o usuário a atravessar wizards quando o alvo e a mudança já estão claros.

Exemplos desejados:

```text
muda a rotina de inglês para 19h
coloca academia terça e quinta às 18h
renomeia a rotina Academia para Treino
adia a tarefa de Física para amanhã
```

Gate:

- [ ] edição direta de rotina;
- [ ] edição direta de tarefa/compromisso quando segura;
- [ ] confirmação somente quando houver ambiguidade real;
- [ ] ação direta não reutiliza contexto velho incorretamente;
- [ ] regressões de falso positivo.

---

# 5.5.3 — Ações em lote

Objetivo: executar vários alvos claramente indicados em uma única operação.

Exemplos desejados:

```text
conclui 1, 3 e 5
marca inglês e academia como feitos
cancela as tarefas 2 e 4
adia essas três para amanhã
```

Gate:

- [ ] conclusão em lote de tarefas;
- [ ] cancelamento/adiamento em lote quando seguro;
- [ ] múltiplas rotinas concluídas explicitamente;
- [ ] prévia/confirmação para lote ambíguo ou destrutivo;
- [ ] operação parcial não deixa estado incoerente;
- [ ] isolamento multiusuário.

---

# 5.5.4 — Respostas curtas e orientadas à ação

Princípio:

```text
ação simples → resposta simples
problema/ambiguidade → explicação suficiente
ajuda solicitada → explicação detalhada
```

Exemplo:

```text
Usuário: concluí a tarefa 2
Butler: ✅ Estudar Física concluída.
```

Evitar comentários adicionais, piadas e explicações quando não acrescentarem valor operacional.

Gate:

- [ ] confirmações comuns cabem preferencialmente em uma linha;
- [ ] erros dizem o que faltou e como corrigir;
- [ ] listas evitam rodapés repetitivos quando o contexto já está claro;
- [ ] personalidade permanece opcional e não atrapalha a ação.

---

# 5.5.5 — Fluxos contínuos

Objetivo: depois de uma ação dentro de um domínio, manter o usuário próximo do próximo passo provável.

Exemplo desejado:

```text
Tarefas
→ concluir 2
→ lista atualizada
→ concluir 4
```

em vez de obrigar:

```text
Tarefas
→ Concluir
→ escolher
→ confirmação
→ voltar
→ Tarefas
→ Concluir
→ escolher
```

Gate:

- [ ] listas importantes podem ser atualizadas depois da mutação;
- [ ] estado não prende o usuário em wizard antigo;
- [ ] Voltar/Cancelar continuam consistentes;
- [ ] atalhos naturais continuam independentes do menu.

---

# 5.5.6 — Gate de UX real

Antes de liberar a Etapa 6, executar uma bateria mínima de 20 cenários de uso cotidiano cobrindo:

- tarefas;
- compromissos;
- rotinas;
- metas;
- agenda;
- Inbox;
- faculdade;
- Modo Estudo;
- compras;
- navegação/retorno.

Critério qualitativo adicional:

> uma operação comum não deve exigir passos extras quando o Butler já possui informação suficiente para executá-la com segurança.

Gate final:

- [ ] 20 cenários documentados;
- [ ] todos passam em regressão determinística quando automatizáveis;
- [ ] nenhuma ação crítica depende de inferência ampla;
- [ ] nenhuma regressão de isolamento multiusuário;
- [ ] respostas operacionais revisadas para concisão;
- [ ] documentação e `STATUS_ATUAL.md` sincronizados;
- [ ] CI verde;
- [ ] deploy validado separadamente.

---

## Ordem oficial dentro da subetapa

```text
5.5.1 Rotinas múltiplas
→ 5.5.2 Edição direta
→ 5.5.3 Ações em lote
→ 5.5.4 Respostas curtas
→ 5.5.5 Fluxos contínuos
→ 5.5.6 Gate de UX real
→ Etapa 6 Projetos e trabalho
```

Não iniciar a Etapa 6 antes do fechamento da 5.5.6.
