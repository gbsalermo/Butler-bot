# Butler — Pós-roadmap: integração progressiva de IA

**Status:** planejado para depois da conclusão do roadmap oficial 0–10  
**Pré-condição:** Butler estável em produção após o fechamento da Etapa 10  
**Provedor inicial escolhido:** Groq  
**Objetivo:** evoluir o Butler de um assistente majoritariamente determinístico para um assistente híbrido, capaz de compreender linguagem natural e orquestrar ferramentas existentes sem entregar regras de negócio ou persistência diretamente ao modelo.

> Esta trilha NÃO faz parte das Etapas 0–10 e não deve ser iniciada antes do fechamento do roadmap atual. A prioridade é concluir e estabilizar o Butler existente primeiro.

---

## 1. Decisão de produto

A IA entra somente depois que o Butler atual estiver funcional, testado e estável.

Ordem obrigatória:

```text
Etapas 0–10 concluídas
        ↓
Gate de estabilidade pós-roadmap
        ↓
Trilha de IA
```

A intenção é evitar usar IA para mascarar bugs, inconsistências de domínio ou dívida técnica que ainda deveriam ser resolvidos deterministicamente.

---

## 2. Gate de estabilidade antes da IA

A trilha de IA só pode começar quando, no mínimo:

- [ ] Etapas 0–10 oficialmente concluídas;
- [ ] regressão completa verde;
- [ ] deploy de produção validado separadamente;
- [ ] nenhum incidente crítico aberto de scheduler, webhook, persistência ou isolamento multiusuário;
- [ ] principais fluxos usados em produção por um período suficiente para revelar regressões reais;
- [ ] backup/restore e observabilidade operacionais;
- [ ] módulos autoritativos por domínio identificados;
- [ ] dívida técnica crítica reduzida;
- [ ] documentação atualizada;
- [ ] baseline de latência e confiabilidade registrado.

Não existe obrigação de começar IA imediatamente após a Etapa 10. Se o sistema ainda precisar de estabilização, a estabilização vence.

---

## 3. Arquitetura desejada

A IA deve evoluir como camada de compreensão e orquestração, mantendo as regras de negócio no Butler.

```text
Telegram
   ↓
Butler / Cloudflare Worker
   ↓
Camada de IA
   ↓
interpretação / decisão de ferramenta
   ↓
validador determinístico
   ↓
ferramenta do domínio
   ↓
D1 / Durable Objects / Telegram
```

Regra permanente:

```text
LLM escolhe/intenciona
Butler valida
Core executa
```

Nunca:

```text
LLM → SQL livre → D1
```

O modelo não recebe poder direto para:

- escrever SQL;
- criar migrations;
- concluir tarefas sem ferramenta autorizada;
- registrar presença sem regra explícita;
- inventar treino, carga ou progresso;
- ignorar validações de data/horário;
- contornar confirmação quando o domínio exigir.

---

## 4. Provedor inicial

Decisão atual: **Groq**.

Motivos registrados:

- serviço de inferência em nuvem separado da infraestrutura Cloudflare do Butler;
- baixa latência como característica importante para conversa interativa;
- suporte a modelos abertos;
- suporte a structured outputs/tool calling;
- possibilidade de começar no plano gratuito vigente;
- permite evoluir da simples interpretação para orquestração de ferramentas sem redesenhar o produto.

### Regra contra acoplamento

Não espalhar chamadas Groq pelo código.

Criar uma abstração própria, por exemplo:

```text
AIProvider
└── GroqProvider
```

Com possibilidade futura de:

```text
AIProvider
├── GroqProvider
├── WorkersAIProvider
├── OllamaProvider
└── outro provedor
```

O contrato da aplicação deve ser nosso, não do fornecedor.

### Modelo

Não congelar no roadmap um nome de modelo específico.

Na data de implementação, reavaliar:

- modelos open-source disponíveis no free tier do Groq;
- qualidade em português brasileiro informal;
- structured outputs;
- tool calling;
- latência;
- limites gratuitos vigentes;
- tamanho/contexto;
- estabilidade do modelo.

A preferência é usar o menor modelo que atenda com boa confiabilidade, escalando somente quando necessário.

---

## 5. Fase AI-1 — compreensão de linguagem

Primeira integração real.

Objetivo: o modelo apenas interpreta a fala do usuário e auxilia a tomada de decisão. Não executa ações diretamente.

Exemplo:

```text
Usuário:
"me dá um toque daqui uns vinte min pra olhar o arroz"

IA:
{
  "intent": "quick_alert",
  "confidence": 0.97,
  "entities": {
    "action": "olhar o arroz",
    "delay_minutes": 20
  },
  "needs_clarification": false
}
```

O Core atual continua executando.

### Início recomendado: Shadow Mode

```text
mensagem
   ├── Butler atual → resposta real
   └── IA → interpretação silenciosa para avaliação
```

A IA não influencia produção no começo.

Medir pelo menos:

- intenção correta;
- entidades corretas;
- falso positivo;
- falso negativo;
- necessidade de esclarecimento;
- latência;
- falha/timeout/429;
- comparação com parser determinístico atual.

Só promover a IA para fallback real depois de evidência suficiente.

---

## 6. Fase AI-2 — ferramentas básicas

Depois da AI-1 estar validada, permitir que o modelo escolha ferramentas controladas para:

```text
create_task
update_task
complete_task
cancel_task
create_appointment
update_appointment
create_reminder
create_timer
cancel_timer
get_today
get_tomorrow
```

O modelo produz intenção/tool call. O domínio valida antes de persistir.

Escrita ambígua continua exigindo confirmação quando necessário.

---

## 7. Fase AI-3 — acadêmico

Adicionar ferramentas de leitura/escrita acadêmica já existentes no Butler, por exemplo:

```text
list_subjects
get_subject_schedule
get_next_class
register_exam
get_absences
register_absence
get_ru_menu
```

Presença nunca é inferida automaticamente.

O modelo não substitui a política acadêmica; apenas interpreta e escolhe ferramentas.

---

## 8. Fase AI-4 — Modo Estudo

Permitir conversa contextual sobre sessões de estudo.

Exemplos desejados:

```text
"tô sem muita cabeça, mas preciso estudar derivada uns 30 min"

"não terminei, vou continuar mais 20"
```

Ferramentas do Modo Estudo continuam impondo a regra:

**tempo encerrado nunca conclui tópico sozinho.**

---

## 9. Fase AI-5 — musculação

Adicionar ferramentas como:

```text
get_today_workout
start_workout
register_set
replace_exercise
finish_exercise
finish_workout
get_previous_load
```

O modelo ajuda a entender frases naturais, mas cargas, repetições e conclusão continuam dependendo de dados explicitamente informados pelo usuário.

---

## 10. Fases posteriores

Depois dos domínios acima estarem maduros, expandir progressivamente para:

- cursos e trilhas;
- projetos/trabalho;
- inbox;
- metas/rotinas;
- memória seletiva;
- recomendações contextuais;
- priorização explicável;
- conversa integrada entre áreas da vida.

A ordem exata após AI-5 pode ser reavaliada conforme uso real.

---

## 11. Fallback obrigatório

A IA nunca pode ser ponto único de falha.

```text
Groq disponível
→ IA auxilia

Groq indisponível / timeout / limite
→ Butler determinístico continua funcionando
```

O sistema deve tratar explicitamente:

- timeout;
- 429/rate limit;
- resposta inválida;
- JSON fora do schema;
- modelo indisponível;
- baixa confiança;
- falha de rede.

Nunca deixar uma falha do provedor derrubar webhook, scheduler ou funções determinísticas.

---

## 12. Critério de sucesso da trilha

A IA só é considerada uma melhoria quando:

- entende melhor linguagem natural real do que o parser atual;
- não reduz confiabilidade das ações;
- não aumenta latência a ponto de piorar a experiência;
- mantém fallback determinístico;
- não ganha autoridade direta sobre persistência;
- respeita isolamento multiusuário;
- reduz complexidade de linguagem artesanal em vez de apenas adicionar outra camada;
- evolui por domínio, com testes e gates próprios.

Objetivo final:

```text
IA = cérebro conversacional/orquestrador
Butler = regras, ferramentas, estado e confiabilidade
```

---

## 13. Relação com o roadmap oficial

Esta trilha começa **somente após** `docs/ETAPA_10_ABERTURA_PUBLICA_ESCALA.md` estar concluída e o gate de estabilidade pós-roadmap deste documento estar fechado.

Até lá:

**não antecipar Groq, LLM/SLM, AIProvider ou tool calling para resolver problemas que pertencem às Etapas 0–10.**
