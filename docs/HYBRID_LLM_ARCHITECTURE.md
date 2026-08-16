# Butler Hybrid Intelligence

## Objetivo

Usar LLM somente como camada de linguagem, personalidade, memória e sugestão de ações. O Butler Core determinístico continua sendo a autoridade sobre dados, regras e operações.

## Fluxo

```text
mensagem
  -> fast path determinístico
  -> Memory Store recupera apenas fatos relevantes já persistidos
  -> LLM (somente OWNER_CHAT_ID nesta fase)
  -> resposta estruturada + novos candidatos de memória
  -> Core valida/deduplica memória
  -> se houver escrita, cria proposta pendente
  -> usuário confirma
  -> Core executa
  -> fallback para NLU conversacional atual se LLM falhar
```

## Fast path

Continuam determinísticos e com prioridade: navegação, tarefas/compromissos claros, provas/matérias, presença, referências naturais, runtime state, mercado explícito, datas/horários e demais regras funcionais.

A LLM recebe apenas mensagens não resolvidas por essas camadas.

## Provider

Primeiro provider: Cloudflare Workers AI por binding `AI`, atrás de `LLMProvider` para permitir troca futura. Modelo inicial: `@cf/google/gemma-4-26b-a4b-it`.

Se binding/provider/resposta falhar, o handler retorna `False` e a NLU atual assume.

## Contrato da LLM

JSON com `reply`, `topic`, `tone`, `action` e `memory_candidates`. A LLM nunca recebe função que escreve diretamente no D1.

## Ações inicialmente permitidas

Somente propostas: `grocery_add`, `task_create`, `routine_create`. O Core valida, persiste proposta pendente e exige confirmação textual antes de executar.

## Butler Memory Store

A memória persistente funciona como um cache semântico de contexto: fatos já compreendidos não precisam ser redescobertos a cada conversa.

Tipos:

- `stable`: fatos duradouros explicitamente informados;
- `episodic`: acontecimentos relevantes;
- `behavioral`: preferências/padrões úteis.

Cada memória pode guardar `subject`, `tags`, `importance` e `confidence`. O Core impõe limiares de confiança, tamanho e tipo. Fatos normalizados iguais são deduplicados; quando reaparecem, podem reforçar/atualizar a memória em vez de criar cópia.

### Recuperação

O `butler_memory.py` pesquisa uma janela maior de memórias persistidas, ranqueia por termos da mensagem, tags, tipo e importância e envia à LLM somente um pequeno conjunto relevante.

Exemplo: uma mensagem sobre `Tobias` deve recuperar `Tobias é o gato do usuário`, sem carregar episódios de Física, treino ou finanças.

Nesta fase a recuperação é lexical e determinística, sem vector database e sem nova chamada de LLM para pesquisar memória.

### Conversa recente

Somente até 4 turnos LLM são enviados para continuidade imediata (pronomes, brincadeiras e mudança de assunto). Conversas antigas devem sobreviver através de memórias resumidas, não pelo reenvio indefinido do chat completo.

### O que não vira memória estável

Dados vivos não são cacheados como verdade permanente: agenda atual, saldo/gastos atuais, tarefas pendentes, progresso de treino e outros estados mutáveis continuam vindo do Core.

## ContextBuilder

O payload enviado à LLM é compacto:

- mensagem atual;
- horário local;
- sinais resumidos de tarefas/agenda/finanças/treino;
- até 6 memórias relevantes;
- até 4 turnos recentes.

O objetivo é reduzir tokens, evitar repetição e manter a identidade/história independente do modelo usado.

## Segurança e autoridade

1. LLM nunca escreve diretamente no banco;
2. LLM nunca apaga dados;
3. Core valida toda ação;
4. escrita requer confirmação;
5. falha da LLM não derruba o bot;
6. fatos numéricos vêm do Core;
7. laboratório restrito ao `OWNER_CHAT_ID`;
8. outros usuários continuam determinísticos;
9. memória sugerida pela LLM só é persistida após validação do Core.

## Evolução futura

- ferramentas de leitura em duas etapas;
- provider chain/fallback externo;
- mais ações propostas com validadores;
- métricas de consumo;
- `/debug_llm`/contexto;
- eventual recuperação vetorial somente se a base de memória crescer a ponto de justificar.

Fine-tuning não é prioridade. A identidade e história pertencem ao Butler Memory Store, não aos pesos do modelo.
