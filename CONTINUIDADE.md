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

## 🕴️ Personality Engine v1

Implementado como camada separada da regra de negócio.

Arquivos:

- `src/personality.py` — tons, famílias de respostas e traços recorrentes;
- `src/context_engine.py` — contexto factual do cotidiano;
- `src/casual_handlers.py` — pequenas conversas naturais;
- `src/scheduler.py` — lembretes proativos agora usam a personalidade.

### Personalidade desejada

Butler é competente, informal, levemente cansado e cínico, mas genuinamente útil. Chama o usuário de `chefe` e pode provocar sem transformar toda mensagem em piada.

Tons disponíveis:

- `NEUTRO` — direto;
- `LEVE` — informal;
- `SARCASTICO` — provocação curta;
- `CUIDADOSO` — sem sarcasmo.

O sarcasmo não deve ser constante. O motor alterna respostas leves e sarcásticas para o personagem não ficar cansativo.

### Limites

- Day-off e situações sensíveis devem usar comportamento cuidadoso, sem cobrança;
- sarcasmo nunca deve humilhar ou atacar o usuário;
- o Butler provoca a situação/comportamento, não a pessoa;
- informação importante deve continuar clara mesmo quando houver piada;
- não usar LLM para mensagens rotineiras nesta etapa.

### Contexto real

`context_engine.py` já observa dados reais como:

- quantidade total de pendências;
- itens previstos para hoje;
- itens atrasados.

Assim um cumprimento pode receber comentários contextuais, por exemplo:

- muitas pendências: `Colecionar era para ser hobby, chefe.`;
- atrasos: comentário sobre itens que já passaram da data;
- nenhuma pendência: `Estranho. Silencioso demais por aqui.`

Isso é o início da memória comportamental. Não inventar fatos que não estejam no banco.

### Traços recorrentes

Butler possui pequenas características que podem reaparecer ocasionalmente. A primeira implementada é uma antipatia gratuita por terça-feira:

`Terça-feira. Você sabe o que penso sobre isso.`

Esses traços devem ser usados com moderação para criar continuidade de personagem.

### Eventos já humanizados

- lembrete de aula;
- tarefa/compromisso/pendência;
- rotina/autocuidado;
- cumprimentos simples (`oi`, `bom dia`, `fala Butler` etc.);
- agradecimentos.

Próxima evolução da personalidade:

1. usar histórico de adiamentos e atrasos para provocações factuais;
2. usar streaks de metas/rotinas para reconhecer constância;
3. comparar evolução de musculação e comentar progresso real;
4. futuramente permitir linguagem natural controlar ações do Butler;
5. somente depois avaliar LLM opcional para conversa livre.

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

Tabela: `protocol_mass_set_logs`.

Cada série guarda separadamente semana, dia, exercício original, exercício efetivamente realizado quando houve substituição, número da série, carga e repetições.

Para prescrições simples o Butler deduz o número de séries. Para prescrições especiais/complexas ele mostra a prescrição original e pergunta quantas séries serão registradas, evitando interpretar técnica avançada de forma errada.

### Histórico de carga

`📊 Histórico de carga` lista exercícios que já possuem séries registradas e mostra a evolução por semana/dia. A comparação atual é factual/visual. Percentual de evolução e volume ficam para depois da normalização das cargas.

### Exercício substituído

`🔁 Substituir exercício` usa somente os substitutos da tabela fornecida e preserva o movimento realmente executado nos registros de séries.

### Não consegui treinar hoje

`😕 Não consegui treinar hoje` registra falta com motivo opcional. O dia não conta como treino concluído e aparece como `➖` no progresso.

### Fluxo de teste

`🧪 Exemplo de treino` existe antes do início e não altera o progresso real. `🔄 Reiniciar os trabalhos` é temporário e apaga também séries/cargas/repetições.

## Scheduler

Atualmente trata aulas, tarefas/compromissos/pendências, itens adiados, rotinas e Day-off. Os lembretes agora passam pelo Personality Engine. O Protocol Mass ainda não envia lembrete automático porque não foi definido horário fixo para musculação.

## Finanças

Continua planejado, ainda sem persistência real. Direção: entradas/saídas, categorias, saldo mensal, histórico, detecção de excesso, economia e metas.

## Próximos passos sugeridos

1. validar manualmente o Personality Engine e o fluxo série por série no Telegram;
2. expandir contexto comportamental com adiamentos, streaks e progresso real;
3. permitir corrigir/apagar uma série registrada por engano;
4. normalizar cargas e calcular evolução/volume quando seguro;
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
