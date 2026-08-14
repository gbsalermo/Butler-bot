# Continuidade do desenvolvimento

## Estado atual

- Desenvolvimento concentrado na `main`.
- Stack: Python, `python-telegram-bot[job-queue]`, SQLite e `python-dotenv`.
- Execução local via polling.
- Nome do bot: `Butler`.
- Username atual: `@ButlerSal_BOT`.
- Prioridade continua sendo funcionalidade antes de suíte de testes.

## Filosofia do produto

O Butler deve parecer um assistente presente, não um formulário. Deve reduzir carga mental, lembrar antes que o usuário precise conferir, guardar pequenas informações persistentes, conversar de forma natural e respeitar períodos de descanso sem cobrança.

## Funcionalidades consolidadas

### 🌙 Day-off

- estado persistente;
- silencia o scheduler;
- permanece após reinício;
- retorno por frases como `Butler, preciso de você!` e `Chamar, Butler!`.

### 📚 Acadêmico

- grade inicial persistida;
- tradução de códigos SIGAA;
- adicionar/remover/trancar/editar matérias;
- matérias trancadas não geram lembretes;
- navegação possui retorno para o menu acadêmico/principal.

### ✅ Tarefas, 📅 compromissos e 📌 pendências

- adicionar/listar/concluir/editar/remover;
- data, horário, detalhes e antecedência configuráveis;
- lembretes proativos;
- concluir ou adiar no próprio aviso;
- botão `❌ Cancelar ação` durante fluxos de cadastro/edição.

### 🏠 Cotidiano

- lista persistente do que está faltando em casa;
- metas gerais e progresso;
- rotinas/autocuidado;
- musculação;
- visão `🗓️ Hoje` agregando agenda e rotina.

## 🏋️ Musculação — Protocol Mass

Implementado a partir das 12 planilhas semanais fornecidas e da tabela oficial de exercícios substitutos.

Arquivos:

- `src/protocol_mass_data.py` — dados das 12 semanas + substituições;
- `src/protocol_mass_store.py` — estado e cumprimento persistidos em SQLite;
- `src/protocol_mass_handlers.py` — fluxo do Telegram;
- `src/protocol_mass_navigation.py` — entrada pelo botão de musculação;
- `src/main.py` — inicialização e registro do módulo.

### Fluxo principal

Ao abrir `🏋️ Musculação`, o Butler direciona para o Protocol Mass.

Opções:

- `🚀 Começar os trabalhos`
- `📅 Treino de hoje`
- `✅ Finalizar treino`
- `📈 Progresso Protocol Mass`
- `🔁 Substitutos`
- retorno ao cotidiano

### Regras do acompanhamento

- protocolo possui 12 semanas;
- cada semana possui treinos de segunda a sábado;
- domingo não entra na contagem;
- `Começar os trabalhos` inicia o protocolo se ainda não começou ou retoma o estado salvo;
- o treino do dia é marcado como iniciado;
- `Finalizar treino` marca o dia como cumprido;
- cada semana exige 6/6 dias concluídos antes de avançar;
- ao completar os seis dias, o Butler avança automaticamente para a próxima semana;
- ao completar a Semana 12, o protocolo é marcado como concluído;
- progresso fica persistido mesmo com reinício do bot.

### Exibição do treino

O Butler mostra, quando disponíveis nas planilhas:

- exercício;
- prescrição de séries/repetições;
- velocidade C/E;
- intervalo;
- técnica.

Os dados foram extraídos das planilhas fornecidas. Se algum registro não puder ser localizado, o Butler deve informar a ausência em vez de inventar a ficha.

### Exercícios substitutos

O botão `🔁 Substitutos` mostra os exercícios do treino atual e pede qual precisa ser trocado.

Regras:

- usar somente a tabela de substituições fornecida com o Protocol Mass;
- busca tolera pequenas diferenças de grafia/nomenclatura entre as planilhas e a tabela;
- se não houver correspondência confiável, responder que não há substituto localizado, sem inventar um exercício.

### Cadastro manual anterior

As tabelas antigas `workout_days` e `workout_exercises` continuam existindo. Elas não foram apagadas porque podem servir posteriormente para fichas próprias, exercícios extras e evolução de carga fora do Protocol Mass.

## Scheduler

Atualmente trata aulas, tarefas/compromissos/pendências, itens adiados, rotinas e Day-off. O Protocol Mass ainda não envia lembrete automático de horário de treino porque não foi definido um horário fixo para musculação.

## Finanças

Continua planejado, ainda sem persistência real. Direção: entradas/saídas, categorias, saldo mensal, histórico, detecção de excesso, economia e metas.

## Próximos passos sugeridos

1. Protocol Mass: registrar carga e repetições realmente executadas em cada série/exercício;
2. Protocol Mass: histórico de evolução de carga entre semanas;
3. Protocol Mass: permitir marcar exercício individual como feito/substituído;
4. rotinas/metas: progresso por período real e streak;
5. resumo diário e semanal automático;
6. finanças persistentes;
7. integração com ônibus;
8. depois consolidar testes e preparar hospedagem 24/7.

## Regra de continuidade

Ao concluir nova etapa:

1. atualizar este arquivo com o estado real;
2. atualizar o README quando funcionalidades ou execução mudarem;
3. registrar decisões que afetem etapas futuras;
4. deixar explícito o próximo passo técnico.
