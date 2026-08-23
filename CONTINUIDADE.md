# Continuidade do desenvolvimento — Butler

> Documento de decisões duradouras e contexto histórico. Para saber **o que a produção executa hoje**, use `docs/ARCHITECTURE.md` como fonte de verdade e confirme o dispatcher em `cloudflare/src/entry.py`.

## 1. Objetivo permanente

Butler é um assistente pessoal via Telegram. Não deve virar apenas um CRUD com botões nem uma coleção de respostas soltas.

Princípios que permanecem válidos independentemente da implementação:

1. operações críticas são determinísticas;
2. ação explícita do usuário tem prioridade sobre contexto antigo;
3. o sistema não inventa presença, conclusão, gasto, compromisso, treino ou memória;
4. dados e estado são isolados por usuário;
5. ambiguidade de escrita deve ser tratada conservadoramente;
6. botões e texto natural podem coexistir;
7. contexto ajuda, mas não deve sequestrar uma mudança explícita de assunto;
8. comportamento novo precisa de regressão;
9. não criar uma camada nova quando o módulo dono já pode resolver o problema;
10. documentação deve distinguir código ativo de código preservado.

## 2. Runtime oficial atual

A `main` usa:

```text
Telegram Webhook
→ Cloudflare Python Worker
→ D1 / Durable Objects
→ Telegram Bot API
```

Entrypoint de deploy:

```text
cloudflare/src/worker.py
```

Dispatcher:

```text
cloudflare/src/entry.py
```

O diretório `src/` na raiz é a implementação antiga de polling/SQLite e não governa a produção atual.

## 3. Evolução arquitetural importante

Em uma fase anterior foi construída uma arquitetura estruturada com:

```text
context_router.py
intent_parser.py
action_policy.py
context_memory.py
suggestion_engine.py
Butler Library
```

A intenção era:

```text
Core
> contexto explícito
> memória
> sugestões
> Library
> conversa genérica
```

Essa direção continua conceitualmente útil e o código foi preservado, porém **o dispatcher operacional atual não usa essa pilha como roteador central**.

A produção passou a privilegiar:

- handlers explícitos e ordenados;
- fast paths conservadores;
- estados guiados;
- módulos autoritativos por domínio;
- fallback estreito.

O `/health` atual registra NLU ampla, Library genérica, sugestões transversais genéricas e memória pessoal genérica como desabilitadas.

### Regra de continuidade

Nunca reative uma camada preservada apenas importando o módulo. Reativação precisa definir:

- posição no dispatcher;
- precedência contra o Core;
- política de escrita;
- isolamento por usuário;
- testes do fluxo final;
- flags coerentes no `/health`.

## 4. Core operacional atual

Continuam ativos ou preservados no Core de produção:

- tarefas e pendências;
- compromissos e agenda;
- lembretes;
- matérias, grade, provas, presença e faltas;
- mercado/lista de itens faltando;
- rotinas;
- metas;
- musculação;
- Ler/Ver Depois;
- finanças;
- Day-off;
- resumos e schedulers.

A autoridade exata por domínio está mapeada em `cloudflare/src/README.md`.

## 5. Política de conversa × ação

A intenção histórica era distinguir:

```text
comentário → conversa
pedido explícito → ação
problema → ajuda/sugestão
ambiguidade → confirmação
```

No runtime atual essa política não é aplicada por `action_policy.py` globalmente. Ela é implementada de forma distribuída nos handlers ativos.

### Exemplo importante: mercado

A arquitetura antiga documentava:

```text
acabou o café
→ sugerir adicionar
→ esperar confirmação
```

O comportamento operacional atual é diferente: `grocery_phrase_patch.py` considera frases claras como `acabou`, `falta` e `tô sem` uma atualização explícita do estado doméstico e grava diretamente na lista.

Essa divergência foi mantida na auditoria porque mudar política de negócio silenciosamente seria arriscado. Se a intenção voltar a ser “sugerir e confirmar”, faça isso em uma mudança funcional separada com testes.

## 6. Contexto atual

Há duas formas de contexto no repositório.

### Contexto operacional ativo

`conversation_layer.py` usa `natural_events` para referências recentes, como:

```text
concluir essa
adiar ela
```

Estados de wizard ficam principalmente em `user_sessions`.

### Contexto estruturado preservado

`context_memory.py` e `context_sync.py` mantêm a arquitetura experimental de tópicos recentes por usuário. A migration `0004_conversation_context.sql` preserva o schema, mas essa camada não é hoje o roteador central do webhook.

## 7. Memória pessoal

A arquitetura de memória determinística com entidades e preferências continua preservada em módulos como:

- `deterministic_memory.py`;
- `personal_profile.py`;
- `general_memory.py`;
- família `companion_*`.

O runtime operacional atual não habilita a memória pessoal genérica como camada global de resposta.

Princípios que continuam obrigatórios se essa frente for retomada:

- salvar somente fatos explícitos;
- permitir correção;
- não inferir relação pessoal;
- isolar por usuário;
- não confundir entidade pessoal com entidade cultural homônima.

## 8. Butler Library

Os acervos de culinária, jogos, cultura pop, literatura e filosofia continuam preservados em `cloudflare/src/knowledge/`.

A Library foi desenhada para evitar um `if` por conhecimento. Esse princípio continua válido.

Entretanto, o dispatcher genérico da Library está desabilitado atualmente. Veja `docs/BUTLER_LIBRARY.md` para o desenho preservado e `docs/ARCHITECTURE.md` para o estado ativo.

Direitos autorais permanecem uma regra permanente: preferir dados abertos, domínio público, documentos próprios, metadados e resumos produzidos para o projeto.

## 9. Patches e dívida arquitetural

A produção atual acumulou módulos que substituem símbolos de outros módulos no import.

Exemplos relevantes:

- performance otimiza `app.ensure_user`;
- políticas de lembrete antigas são neutralizadas pela política confiável;
- envio de scheduler é envolvido por confirmação real de entrega;
- menus-base são redefinidos por camadas operacionais.

Essa estratégia permitiu evoluir sem reescrever o Core, mas agora é uma dívida técnica.

### Regra daqui para frente

Não criar `*_fix2.py`, `*_final.py` ou nova camada paralela sem necessidade real.

Quando houver cobertura suficiente, consolidar a regra no módulo autoritativo e remover o patch antigo em PR específico.

## 10. Scheduler

A política atual de produção é documentada em `docs/ARCHITECTURE.md` e `cloudflare/README.md`.

Princípios permanentes:

- cron não deve mandar aviso obsoleto muito depois do horário;
- entrega só deve ser registrada como concluída quando o Telegram confirmar quando isso for crítico;
- `notification_log` protege idempotência;
- falha de um subsistema não deve derrubar os demais;
- Day-off deve ser respeitado conforme a categoria do aviso.

## 11. Acadêmico e presença

Aulas são previstas pelo horário cadastrado; presença não pode ser presumida.

O sistema pode:

- avisar sobre aula;
- perguntar presença/falta;
- registrar resposta explícita;
- calcular limites conforme as regras cadastradas.

Não registrar presença automaticamente só porque o horário passou.

## 12. Musculação

O perfil do proprietário preserva protocolo de 12 semanas e o perfil genérico pode trabalhar com ficha própria.

Regras:

- não aplicar protocolo pessoal a outro usuário;
- registrar carga/repetição somente quando informadas;
- substituição de exercício não deve apagar histórico;
- evolução deve usar dados reais registrados.

## 13. Perfil proprietário × usuários genéricos

O projeto nasceu como assistente pessoal e depois ganhou isolamento multiusuário. Por isso ainda há configuração/seeds pessoais em código.

A barreira `is_owner(chat_id)` não deve ser removida sem substituir o mecanismo.

Antes de distribuir o Butler como produto genérico, mover perfil/seed pessoal para configuração privada é recomendado.

## 14. Banco e migrations

A fonte formal de evolução do D1 é `cloudflare/migrations/`.

Não assumir que `runtime_schema.py` roda automaticamente; hoje ele é helper de compatibilidade.

Mudança de schema deve incluir:

1. migration numerada;
2. backfill quando necessário;
3. `ensure_schema()` somente quando houver motivo operacional;
4. teste;
5. documentação.

## 15. Bootstrap e usuários existentes

`performance_patch.py` evita repetir o bootstrap completo em cada mensagem de usuário já conhecido.

Consequência: adicionar um novo default somente em `app.ensure_user()` afeta novas contas, não garante atualização das existentes.

Para defaults retroativos, use migration/backfill explícito.

## 16. Testes e regressão

A suíte em `cloudflare/tests/` deve ser executável em CPython e proteger funções determinísticas.

O runtime real usa Pyodide. `tests/conftest.py` existe apenas para permitir imports de `js`/`pyodide`; não é simulação de rede.

Prioridade de novos testes:

- dispatcher realmente ativo;
- variações informais;
- falsos positivos;
- dois usuários distintos;
- estados/cancelamento;
- idempotência temporal;
- regressões de casos reais.

## 17. Documentos de referência

Use cada arquivo para o propósito correto:

- `README.md` — visão geral;
- `docs/ARCHITECTURE.md` — runtime ativo;
- `docs/MAINTAINER_GUIDE.md` — como editar;
- `cloudflare/src/README.md` — mapa de módulos;
- `docs/AUDIT_MAIN_2026-08.md` — achados da auditoria;
- `docs/BUTLER_LIBRARY.md` — desenho preservado da Library;
- este arquivo — decisões e direção histórica.

## 18. Próxima direção recomendada

A prioridade não é adicionar mais catálogo ou mais patches. É:

```text
1. testar o dispatcher de produção ponta a ponta com fakes
2. consolidar menus duplicados
3. consolidar política de lembretes
4. remover patches obsoletos com segurança
5. reduzir diferenças entre documentação e código
6. decidir conscientemente quais camadas preservadas serão reativadas
```

Ao concluir uma etapa futura, atualize `docs/ARCHITECTURE.md` quando o comportamento ativo mudar e este arquivo quando uma decisão arquitetural de longo prazo mudar.
