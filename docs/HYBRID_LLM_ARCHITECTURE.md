# Butler Hybrid Intelligence

## Objetivo

Usar LLM somente como camada de linguagem, personalidade, memória e sugestão de ações. O Butler Core determinístico continua sendo a autoridade sobre dados, regras e operações.

## Fluxo

```text
mensagem
  -> fast path determinístico
  -> LLM (somente OWNER_CHAT_ID nesta fase)
  -> resposta estruturada
  -> Core valida
  -> se houver escrita, cria proposta pendente
  -> usuário confirma
  -> Core executa
  -> fallback para NLU conversacional atual se LLM falhar
```

## Fast path

Continuam determinísticos e com prioridade:

- navegação;
- tarefas/compromissos claros;
- provas e matérias;
- presença;
- referências naturais já reconhecidas;
- runtime state;
- mercado explícito;
- validações de datas/horários;
- demais regras funcionais do bot.

A LLM recebe apenas mensagens que não foram resolvidas por essas camadas.

## Provider

Primeiro provider: Cloudflare Workers AI por binding `AI`.

A integração fica atrás de `LLMProvider`, permitindo troca futura sem alterar o restante do Butler.

Modelo inicial do laboratório:

`@cf/google/gemma-4-26b-a4b-it`

Se o binding estiver ausente, o provider falhar ou a resposta vier inválida, o handler retorna `False` e a NLU atual assume.

## Contrato da LLM

A LLM deve devolver JSON com:

- `reply`: resposta natural;
- `topic`: tema;
- `tone`: tom;
- `action`: ação sugerida ou `null`;
- `memory_candidates`: fatos que podem ser úteis depois.

A LLM nunca recebe função que escreve diretamente no D1.

## Ações inicialmente permitidas

Somente propostas:

- `grocery_add`;
- `task_create`;
- `routine_create`.

O Core valida payload, armazena uma proposta pendente e exige confirmação textual (`pode`) antes de executar.

Ações desconhecidas ou payload inválido são rejeitados.

## Memória

Nesta primeira fase, a memória usa a tabela existente `natural_events`.

Tipos:

- `stable`: fatos duradouros explicitamente informados;
- `episodic`: acontecimentos relevantes;
- `behavioral`: preferências ou padrões úteis.

A LLM apenas sugere candidatos. O Core aplica limites de tamanho, tipo e confiança antes de persistir.

Os últimos turnos LLM também são registrados para continuidade curta da conversa.

## ContextBuilder

A LLM não recebe o banco inteiro. O snapshot inicial inclui somente sinais resumidos:

- horário local;
- tarefas concluídas nos últimos 7 dias;
- pendências;
- próximo item;
- quantidade de itens faltando;
- resumo financeiro de 30 dias;
- treinos concluídos nos últimos 7 dias;
- memórias relevantes recentes;
- últimos turnos conversacionais da LLM.

Essa camada deve ficar mais seletiva no futuro, recuperando contexto por tema.

## Segurança e autoridade

Regras obrigatórias:

1. LLM nunca escreve diretamente no banco;
2. LLM nunca apaga dados;
3. Core valida toda ação;
4. escrita requer confirmação do usuário;
5. falha da LLM não derruba o bot;
6. dados numéricos/factuais devem vir do Core, não ser inventados;
7. laboratório restrito ao `OWNER_CHAT_ID`;
8. outros usuários continuam no comportamento determinístico atual.

## Evolução futura

Possíveis próximas fases:

- recuperação de memória por relevância semântica;
- ferramentas de leitura em duas etapas (agenda/finanças/provas -> LLM apresenta o resultado);
- mais ações propostas com validadores específicos;
- provider alternativo (OpenRouter, Gemini, Ollama etc.);
- controle de custo/tokens por conversa;
- comando de debug de contexto;
- avaliação de respostas e feedback de personalidade.

Fine-tuning não é prioridade. A evolução deve vir primeiro de memória externa, contexto e regras de personalidade.
