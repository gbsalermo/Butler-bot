# Etapa 4.3 — Progresso e Continuar curso

**Status:** implementada na branch da Etapa 4.  
**Autoridade de persistência:** `cloudflare/src/course_domain.py`.

## Objetivo

Expor no Telegram o progresso que já existia no domínio sem transformar navegação ou tempo decorrido em conclusão fictícia.

## Operações

Na tela do curso:

- `▶️ Continuar curso` abre o próximo conteúdo `pending` retornado por `next_content()`;
- `📊 Progresso` mostra concluídos, pulados, pendentes e próximo conteúdo;
- `🏁 Concluir curso` abre confirmação explícita;
- curso concluído pode ser `↩️ Reabrir curso`.

Na tela do conteúdo:

- `✅ Concluir conteúdo` → `completed`;
- `⏭️ Pular conteúdo` → `skipped`;
- `↩️ Voltar para pendente` → `pending`.

## Invariantes preservados

1. abrir curso, módulo ou conteúdo não muda progresso;
2. `Continuar curso` é consulta pura e nunca conclui o item aberto;
3. `skipped` conta como resolvido, mas não como concluído/aprendido;
4. concluir o último conteúdo não conclui o curso;
5. conclusão do curso exige confirmação explícita;
6. curso autogerido segue posição persistida de módulo/conteúdo;
7. curso ao vivo continua seguindo `scheduled_at` persistido;
8. todas as mutações continuam passando por `course_domain.py`;
9. isolamento por usuário continua obrigatório.

## Implementação

- `cloudflare/src/course_stage4.py` — UX incremental da 4.3;
- `cloudflare/src/operational_menu.py` — instala e despacha a extensão antes do CRUD 4.2;
- `cloudflare/tests/test_stage4_3_course_progress.py` — regressões de explicitness, continuar, reabrir e isolamento.

A integração com Modo Estudo continua fora desta subetapa e só entra na 4.4.
