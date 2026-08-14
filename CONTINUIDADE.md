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
- `src/protocol_mass_store.py` — estado, sessões, exercícios e séries em SQLite;
- `src/protocol_mass_handlers.py` — fluxo geral do Telegram;
- `src/protocol_mass_series.py` — acompanhamento série por série e histórico;
- `src/protocol_mass_navigation.py` — entrada pelo botão de musculação;
- `src/protocol_mass_ui.py` — menus diferentes antes/durante o protocolo;
- `src/main.py` — inicialização e registro do módulo.

### Semântica de início

`🚀 Começar os trabalhos` significa iniciar o protocolo inteiro de 12 semanas e deve aparecer somente antes do início.

Durante o protocolo ativo, o menu diário não oferece um novo início. O botão `🔄 Reiniciar os trabalhos` continua apenas como ferramenta temporária de teste e zera completamente o protocolo.

### Menu durante o protocolo

- `📅 Treino de hoje`
- `🏋️ Registrar séries`
- `🔁 Substituir exercício`
- `✅ Finalizar treino`
- `😕 Não consegui treinar hoje`
- `📈 Progresso Protocol Mass`
- `📊 Histórico de carga`
- `🔄 Reiniciar os trabalhos` — temporário para teste
- retorno ao cotidiano

### Regras do acompanhamento

- protocolo possui 12 semanas;
- cada semana possui treinos de segunda a sábado;
- domingo não entra na contagem;
- semana só avança após 6/6 treinos concluídos;
- reiniciar o processo do bot não perde o progresso;
- Semana 12 concluída encerra o protocolo.

### Registro série por série

Nova tabela: `protocol_mass_set_logs`.

Cada série guarda separadamente:

- semana;
- dia;
- exercício original;
- exercício efetivamente realizado quando houve substituição;
- número da série;
- carga;
- repetições;
- observação futura opcional.

Fluxo de `🏋️ Registrar séries`:

1. escolher o exercício do treino atual;
2. para prescrições simples (`3 x ...`, `4 x ...`) o Butler deduz automaticamente o número de séries;
3. para prescrições especiais/complexas (`1 + ...`, ciclos, cluster, bi-set etc.) o Butler mostra a prescrição original e pergunta quantas séries efetivamente serão registradas, evitando interpretar a técnica de forma errada;
4. para cada série pergunta carga;
5. depois pergunta repetições;
6. salva cada série imediatamente;
7. ao terminar, marca o exercício como registrado.

Se o fluxo for cancelado no meio, as séries já gravadas permanecem salvas.

### Histórico de carga

`📊 Histórico de carga` lista exercícios que já possuem séries registradas e mostra a evolução por semana/dia.

Exemplo conceitual:

- Semana 1 — Supino reto
  - 1ª série — 40 kg x 12
  - 2ª série — 40 kg x 10
  - 3ª série — 40 kg x 8
- Semana 2 — Supino reto
  - 1ª série — 42 kg x 10
  - 2ª série — 42 kg x 9
  - 3ª série — 42 kg x 8

O histórico preserva substituições, mostrando quando o exercício foi efetivamente realizado com outro movimento.

Nesta etapa a comparação é factual/visual entre registros. Cálculos automáticos de percentual de evolução, volume e tendências ficam para evolução futura, pois cargas podem ser registradas em formatos textuais diferentes (`kg`, `cada lado`, `peso corporal` etc.).

### Exercício substituído

`🔁 Substituir exercício` escolhe o exercício original e depois um substituto oficial da tabela fornecida. A substituição fica persistida e também é usada pelo registro série por série para identificar qual movimento foi efetivamente realizado.

Regras:

- usar somente a tabela oficial de substituições fornecida;
- tolerar pequenas diferenças de nomenclatura;
- nunca inventar substituto quando não houver correspondência confiável.

### Não consegui treinar hoje

`😕 Não consegui treinar hoje` registra uma falta daquele dia no protocolo.

- pode guardar motivo livre ou `Sem motivo específico`;
- o dia não conta como treino concluído;
- a semana não avança por esse registro;
- no progresso aparece como `➖`.

Legenda do progresso:

- `✅` treino concluído;
- `➖` falta;
- `⬜` treino ainda pendente.

### Fluxo de teste

`🧪 Exemplo de treino` existe antes do início e não altera o progresso real.

`🔄 Reiniciar os trabalhos` é temporário para desenvolvimento/teste e exige confirmação. Agora ele apaga também `protocol_mass_set_logs`, além de progresso, sessões, exercícios e substituições.

## Scheduler

Atualmente trata aulas, tarefas/compromissos/pendências, itens adiados, rotinas e Day-off. O Protocol Mass ainda não envia lembrete automático de horário de treino porque não foi definido um horário fixo para musculação.

## Finanças

Continua planejado, ainda sem persistência real. Direção: entradas/saídas, categorias, saldo mensal, histórico, detecção de excesso, economia e metas.

## Próximos passos sugeridos

1. validar manualmente o fluxo série por série no Telegram;
2. permitir corrigir/apagar uma série registrada por engano;
3. calcular evolução quando cargas puderem ser normalizadas numericamente;
4. calcular volume por exercício quando fizer sentido (`carga × repetições`);
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
