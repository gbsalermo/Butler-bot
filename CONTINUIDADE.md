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

Arquivos principais:

- `src/protocol_mass_data.py` — dados das 12 semanas + substituições;
- `src/protocol_mass_store.py` — estado, sessões e registros de exercícios em SQLite;
- `src/protocol_mass_handlers.py` — fluxo do Telegram;
- `src/protocol_mass_navigation.py` — entrada pelo botão de musculação;
- `src/main.py` — inicialização e registro do módulo.

### Menu atual

- `🚀 Começar os trabalhos`
- `📅 Treino de hoje`
- `📝 Registrar exercício`
- `🔁 Substituir exercício`
- `✅ Finalizar treino`
- `😕 Não consegui treinar hoje`
- `📈 Progresso Protocol Mass`
- `🧪 Exemplo de treino`
- `🔄 Reiniciar os trabalhos` — temporário enquanto o fluxo está sendo validado
- retorno à musculação/cotidiano

### Regras do acompanhamento

- protocolo possui 12 semanas;
- cada semana possui treinos de segunda a sábado;
- domingo não entra na contagem;
- `Começar os trabalhos` inicia ou retoma o estado salvo;
- semana só avança após 6/6 treinos concluídos;
- reiniciar o processo do bot não perde o progresso;
- Semana 12 concluída encerra o protocolo.

### Registro de exercício

Nova tabela: `protocol_mass_exercise_logs`.

`📝 Registrar exercício` permite escolher um exercício do treino atual e registrar um resultado livre, por exemplo:

- `40 kg — 10/9/8`
- `20 kg cada lado — 8/8/7`
- ou simplesmente `feito`.

O objetivo é começar a formar histórico real de carga/repetições sem tentar interpretar automaticamente prescrições complexas como cluster, bi-set, FST-7 ou MTUT.

### Exercício substituído

`🔁 Substituir exercício` agora faz duas etapas:

1. escolhe o exercício original do treino do dia;
2. escolhe qual substituto oficial será usado.

A escolha fica persistida no banco e aparece posteriormente em `📅 Treino de hoje` como exercício substituído.

Se depois for registrado resultado/carga para aquele exercício, a informação de substituição é preservada.

Regras:

- usar somente a tabela oficial de substituições fornecida;
- tolerar pequenas diferenças de nomenclatura;
- nunca inventar substituto quando não houver correspondência confiável.

### Não consegui treinar hoje

`😕 Não consegui treinar hoje` registra o dia como não realizado.

- pode guardar motivo livre ou `Sem motivo específico`;
- o dia NÃO conta como treino concluído;
- a semana NÃO avança por esse registro;
- no progresso aparece como `➖`;
- caso o usuário depois decida treinar naquele mesmo dia, `Começar os trabalhos` limpa o status de falta e permite seguir normalmente.

Legenda do progresso:

- `✅` treino concluído;
- `➖` treino não realizado;
- `⬜` treino ainda pendente.

### Fluxo de teste

`🧪 Exemplo de treino` exibe uma simulação baseada na Semana 1 / Segunda-feira sem alterar o banco real.

`🔄 Reiniciar os trabalhos` é uma opção temporária para desenvolvimento/teste e exige confirmação. Ela apaga:

- progresso das semanas;
- sessões concluídas/não realizadas;
- resultados de exercícios;
- substituições.

Depois volta para Semana 1 ainda não iniciada.

### Exibição do treino

O Butler mostra, quando disponíveis nas planilhas:

- exercício;
- prescrição de séries/repetições;
- velocidade C/E;
- intervalo;
- técnica;
- resultado registrado;
- substituição realizada.

Os dados-base vêm das planilhas fornecidas. Se algum registro não puder ser localizado, o Butler deve informar a ausência em vez de inventar a ficha.

### Cadastro manual anterior

As tabelas antigas `workout_days` e `workout_exercises` continuam existindo. Elas podem ser reaproveitadas posteriormente para fichas próprias, exercícios extras e treinos fora do Protocol Mass.

## Scheduler

Atualmente trata aulas, tarefas/compromissos/pendências, itens adiados, rotinas e Day-off. O Protocol Mass ainda não envia lembrete automático de horário de treino porque não foi definido um horário fixo para musculação.

## Finanças

Continua planejado, ainda sem persistência real. Direção: entradas/saídas, categorias, saldo mensal, histórico, detecção de excesso, economia e metas.

## Próximos passos sugeridos

1. validar manualmente o novo fluxo do Protocol Mass no Telegram;
2. após validação, substituir o campo livre de resultado por acompanhamento opcional série a série quando a prescrição permitir;
3. histórico de evolução de carga entre semanas e comparação do mesmo exercício;
4. permitir corrigir/apagar um registro de exercício feito por engano;
5. remover o botão temporário `🔄 Reiniciar os trabalhos` quando o módulo estiver estável;
6. rotinas/metas: progresso por período real e streak;
7. resumo diário e semanal automático;
8. finanças persistentes;
9. integração com ônibus;
10. depois consolidar testes e preparar hospedagem 24/7.

## Regra de continuidade

Ao concluir nova etapa:

1. atualizar este arquivo com o estado real;
2. atualizar o README quando funcionalidades ou execução mudarem;
3. registrar decisões que afetem etapas futuras;
4. deixar explícito o próximo passo técnico.
