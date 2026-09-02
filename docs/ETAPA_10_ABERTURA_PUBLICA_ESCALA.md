# Etapa 10 — Abertura pública, capacidade e escala

**Status:** ⏳ planejada  
**Posição:** penúltima etapa do roadmap, depois da Etapa 9 — Hardening e antes da Etapa 11 — Idiomas e internacionalização  
**Objetivo:** validar tecnicamente a abertura pública do Butler e elevar a capacidade real do sistema para suportar o maior número de usuários possível com segurança, previsibilidade e custo controlado.

> Esta etapa não deve estimar capacidade apenas por número de usuários cadastrados. O critério é carga real: mensagens, leituras/escritas D1, cron, Durable Objects, chamadas Telegram, armazenamento, latência e custo por usuário ativo.

---

## 1. Princípio de lançamento

O Butler não deve ser aberto irrestritamente ao público antes de existir uma resposta medida para estas perguntas:

```text
quantos usuários ativos/dia o plano atual suporta?
quantas mensagens por usuário/dia foram assumidas e observadas?
qual recurso acaba primeiro?
quanto custa dobrar a base?
qual é o limite seguro antes de degradar o serviço?
o que acontece quando esse limite é atingido?
```

Não usar apenas limites teóricos do provedor. Medir o comportamento do runtime real.

---

## 2. Auditoria completa de Cloudflare

Na execução desta etapa, consultar novamente a documentação/preços vigentes do Cloudflare. Não congelar no roadmap números que podem mudar.

Inventariar o consumo e os limites aplicáveis de:

- Workers requests;
- CPU time / duração;
- D1 rows read;
- D1 rows written;
- D1 storage;
- queries por invocação e tamanho do banco;
- Durable Objects requests;
- Durable Objects storage/SQLite;
- cron triggers;
- subrequests/fetches externos;
- logs/observabilidade;
- limites do plano Free e do plano pago atualmente disponível.

Produzir uma tabela do tipo:

```text
recurso | limite atual | uso medido | uso por usuário ativo | margem segura | gargalo?
```

---

## 3. Auditoria de D1 e SQL

D1 deve ser tratado como provável gargalo até prova em contrário.

Revisar todas as consultas relevantes do runtime e jobs agendados:

- identificar scans completos de tabelas;
- conferir índices usados pelos filtros reais;
- eliminar consultas globais que poderiam ser filtradas antes;
- medir rows read por operação comum;
- medir rows written por operação comum;
- revisar `SELECT *` desnecessários;
- revisar consultas executadas em toda mensagem;
- revisar consultas executadas a cada minuto;
- revisar N+1 queries;
- revisar duplicação de consultas entre handlers;
- verificar crescimento de `notification_log`, históricos e tabelas de eventos;
- definir retenção/arquivamento quando aplicável.

Casos conhecidos devem ser reavaliados, incluindo consultas globais relacionadas a Day-off e qualquer fluxo criado depois deste documento.

Sempre que houver índice novo:

```text
hipótese → EXPLAIN/medição → migration → regressão → medição após mudança
```

Não criar índice por reflexo sem verificar seletividade e benefício.

---

## 4. Auditoria do scheduler

O Butler possui trabalho recorrente e isso pode custar mais que as mensagens dos usuários quando a base cresce.

Revisar:

- cron de minuto;
- presença;
- lembretes;
- rotinas;
- resumos;
- Durable Objects/alarmes pessoais;
- scans de usuários para decidir que nada precisa ser feito;
- jobs que poderiam consultar apenas itens vencidos/próximos;
- redundâncias entre Cron e Durable Objects;
- idempotência e `notification_log`.

Objetivo: o custo de um minuto sem eventos relevantes deve ser próximo do mínimo possível e não crescer linearmente com todos os usuários sem necessidade.

---

## 5. Hot path de cada mensagem

Mapear o caminho real de uma mensagem Telegram até a resposta.

Para os principais fluxos, medir:

- quantidade de queries D1;
- rows read;
- rows written;
- chamadas à API do Telegram;
- chamadas externas;
- tempo total;
- CPU do Worker;
- handlers visitados antes do consumo;
- alocações/parse desnecessários quando mensuráveis.

Cenários mínimos:

```text
/start
abrir menu
listar Hoje
criar tarefa
criar compromisso
consulta acadêmica
registrar presença
rotina
RU
musculação
Ler/Ver Depois
mensagem não entendida
```

Criar orçamento de performance por operação para detectar regressões futuras.

---

## 6. Telegram Bot API

Validar os limites e comportamento atuais do Telegram na época da abertura.

Revisar:

- taxa de envio global;
- taxa por chat;
- rajadas de resumo/lembretes no mesmo minuto;
- `/aviso` para muitos usuários;
- retries em `429`;
- respeito a `retry_after`;
- filas/batches quando necessário;
- falhas parciais de broadcast;
- usuários que bloquearam o bot;
- limpeza/estado desses usuários sem loop de erro.

Broadcast administrativo nunca deve derrubar o tráfego operacional normal.

---

## 7. Modelo de capacidade

Criar pelo menos três perfis de uso:

### Leve

Usuário consulta o Butler algumas vezes por dia e recebe poucos lembretes.

### Moderado

Usuário usa tarefas, agenda, universidade, rotinas e consultas ao longo do dia.

### Intenso

Usuário mantém vários domínios ativos, treinos, rotinas, lembretes, contexto e muitas mensagens.

Para cada perfil calcular/medir:

```text
mensagens/dia
requests Worker/dia
D1 reads/dia
D1 writes/dia
DO requests/dia
Telegram sends/dia
armazenamento/mês
```

A capacidade pública deve ser apresentada como faixa, por exemplo:

```text
X usuários ativos intensos
Y moderados
Z leves
```

Não converter automaticamente `100 mil requests / mensagens por pessoa` em capacidade se D1 ou scheduler acabar antes.

---

## 8. Testes de carga

Criar um simulador/replay que reproduza tráfego sem depender de usuários reais.

Testar progressivamente:

```text
10 usuários simultâneos
50
100
250
500
1.000
2.500
5.000
...
```

Continuar enquanto fizer sentido para a arquitetura/plano.

Os números são degraus de teste, não promessa de capacidade.

Cada rodada deve registrar:

- taxa de sucesso;
- p50/p95/p99 de latência;
- erros;
- timeouts;
- consumo D1;
- CPU;
- filas/429 do Telegram;
- custo estimado;
- comportamento do scheduler sob carga.

Testar também picos, não apenas média diária.

---

## 9. Testes de crescimento de banco

Popular base sintética com volumes crescentes para detectar consultas que parecem rápidas apenas porque hoje existem poucos registros.

Cenários sugeridos:

```text
100 usuários
1.000 usuários
10.000 usuários
100.000 usuários
```

Com histórico plausível de tarefas, notificações, rotinas, sessões, presença e demais domínios.

Validar tamanho, latência e rows read, sem assumir que o volume máximo será atingido no lançamento.

---

## 10. Proteções contra abuso

Bot público precisa assumir entrada hostil ou uso acidental excessivo.

Implementar conforme necessário:

- rate limit por usuário/chat;
- limite para uploads;
- limite de tamanho de texto/documento;
- cooldown para operações caras;
- proteção de endpoints não Telegram;
- webhook secret obrigatório em produção pública;
- bloqueio de callbacks inválidos/repetidos;
- proteção contra spam de `/start` e criação em massa;
- limites administrativos;
- não revelar diagnósticos internos para usuário comum.

Preferir respostas claras a simplesmente descartar tráfego.

---

## 11. Isolamento e privacidade multiusuário

Antes da abertura:

- auditar toda query que lê/escreve dado pessoal;
- verificar presença de `user_id`/escopo equivalente;
- testar dois e múltiplos usuários concorrentes;
- impedir vazamento por cache/contexto curto;
- revisar fontes compartilhadas intencionais, como cardápio público do RU;
- revisar comandos do proprietário;
- revisar logs para evitar exposição de conteúdo desnecessário;
- definir política básica de dados/remoção de conta caso o produto se torne realmente público.

Teste obrigatório: um usuário nunca consegue listar, alterar ou receber dados pessoais de outro.

---

## 12. Onboarding público

Revisar experiência de um usuário que nunca viu o Butler:

- `/start` sem dados do proprietário;
- explicação curta do que o Butler faz;
- menu coerente após a reformulação da Etapa 4;
- importações opcionais;
- nenhuma funcionalidade pressupõe dados pessoais do desenvolvedor;
- erros orientam recuperação;
- funções indisponíveis não aparecem ou explicam claramente o motivo.

---

## 13. Observabilidade de capacidade

Criar painel/checklist operacional capaz de responder pelo menos:

```text
usuários cadastrados
DAU / usuários ativos
mensagens recebidas
mensagens enviadas
falhas Telegram
429
latência
D1 rows read/write
consultas mais caras quando possível
cron executado/falhando
Durable Object alarms
uso aproximado do plano
```

Definir alertas antes dos limites, não quando já foram ultrapassados.

Faixas recomendadas de atenção devem ser definidas na época conforme os limites reais, por exemplo 50%, 70%, 85% e 95% da cota relevante.

---

## 14. Degradação controlada

Definir o que o Butler faz quando a capacidade estiver perto do limite.

Possibilidades, conforme o gargalo:

- suspender temporariamente recursos não essenciais caros;
- reduzir frequência de tarefas de manutenção;
- preservar lembretes e agenda como prioridade;
- pausar novos cadastros com mensagem explícita;
- manter lista de espera;
- rejeitar broadcast administrativo durante saturação;
- migrar para plano pago antes de bloquear usuários ativos.

Nunca deixar exceder quota sem estratégia e descobrir o problema apenas porque o bot parou.

---

## 15. Estratégia de lançamento por ondas

Mesmo após testes sintéticos, abrir gradualmente:

```text
onda 0 — uso interno
onda 1 — beta fechado pequeno
onda 2 — 50–100 usuários reais
onda 3 — 200–500, se métricas permitirem
onda 4 — aumento progressivo
onda final — público sem convite quando a margem estiver comprovada
```

Os números são orientativos; a decisão real usa a telemetria vigente.

Em cada onda comparar estimativa × uso real e recalibrar o modelo.

---

## 16. Free vs pago

Antes de pagar, extrair o máximo razoável da arquitetura atual sem sacrificar confiabilidade.

Quando o plano Free deixar de ser adequado, produzir comparação objetiva:

```text
custo atual
custo projetado no plano pago
usuários ativos suportados
custo por 1.000 usuários ativos
margem de segurança
qual quota motiva a mudança
```

Upgrade não substitui otimização: uma query ruim continua ruim com quota maior.

---

## 17. Gate obrigatório para abertura pública

- [ ] limites/preços atuais do Cloudflare conferidos novamente;
- [ ] uso real de Worker, D1 e Durable Objects mensurado;
- [ ] todas as queries do hot path auditadas;
- [ ] jobs de minuto/scheduler auditados;
- [ ] scans globais desnecessários removidos ou justificados;
- [ ] índices importantes validados por medição;
- [ ] capacidade leve/moderada/intensa calculada;
- [ ] teste de carga executado;
- [ ] teste com banco grande executado;
- [ ] limites atuais do Telegram revisados;
- [ ] 429/retry/broadcast tratados;
- [ ] rate limiting/antiabuso definidos;
- [ ] isolamento multiusuário auditado;
- [ ] onboarding público validado com usuário limpo;
- [ ] observabilidade de capacidade disponível;
- [ ] alertas antes das quotas definidos;
- [ ] estratégia de degradação controlada definida;
- [ ] backup/restore validado;
- [ ] plano de incidente/rollback disponível;
- [ ] beta por ondas executado;
- [ ] estimativa × consumo real comparados;
- [ ] número máximo seguro de usuários ativos publicado internamente com margem;
- [ ] decisão Free × pago documentada;
- [ ] regressão completa verde;
- [ ] deploy público validado separadamente.

**O Butler só é considerado pronto para abertura pública irrestrita quando esse gate estiver concluído.**

---

## Critério de sucesso

A meta não é declarar um número grande de usuários. A meta é conseguir aumentar a base até o maior volume que a arquitetura e o orçamento suportem, sabendo exatamente:

- onde está o gargalo;
- quanto cada usuário ativo custa em recursos;
- qual margem ainda existe;
- quando otimizar;
- quando subir de plano;
- como evitar que crescimento derrube lembretes e funções essenciais.

Capacidade passa a ser uma propriedade mensurada do Butler, não um palpite.

---

## 18. Pós-roadmap — estabilidade antes de IA

A Etapa 10 encerra o roadmap funcional atual, mas **não inicia automaticamente a integração de IA**.

Após concluir esta etapa, o projeto entra primeiro em um período de estabilização:

```text
Etapa 10 concluída
        ↓
Butler operando de forma estável
        ↓
gate pós-roadmap fechado
        ↓
integração progressiva de IA
```

A trilha de IA está documentada em:

`docs/POS_ROADMAP_IA.md`

Decisão atual registrada:

- provedor inicial pretendido: **Groq**;
- começar somente após estabilidade do produto atual;
- primeira fase: IA apenas para compreensão de linguagem e auxílio à decisão;
- evolução posterior por ferramentas/domínios;
- Core determinístico permanece autoridade de regras e persistência;
- modelo específico e condições do free tier devem ser reavaliados quando a implementação realmente começar.

A IA não deve ser antecipada para resolver problemas pertencentes às Etapas 0–10.