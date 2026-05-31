# Plano de Melhorias — Agente de Vendas

---

## 🔴 Críticos (produção)

- [ ] **1. HttpOnly cookie para JWT** — Migrar token de `localStorage` para cookie httpOnly setado pelo NestJS no endpoint `/auth/login`. Protege contra ataques XSS.
- [ ] **2. Rate limiting nas APIs** — Implementar `@nestjs/throttler` ou middleware Redis-based no NestJS para limitar requisições por IP. Especialmente endpoints públicos (`/auth/login`, `/auth/register`).
- [ ] **3. Webhook HMAC obrigatório** — Se `EVOLUTION_WEBHOOK_SECRET` não estiver configurado, o Hono deve recusar a inicialização. Hoje aceita requisição sem assinatura se a chave não existe.
- [ ] **4. Logs centralizados** — Adicionar coletor de logs (Loki + Promtail, ELK, ou ao menos um agregador JSON em stdout parseável por Docker).

## 🟠 Importantes

- [ ] **5. Multi-turn tool loop no LangGraph** — AgentExecuteNode hoje chama a tool e retorna. Precisa realimentar o resultado da tool na LLM para gerar resposta final contextualizada.
- [ ] **6. GPT-4o Vision para mídias** — ParseClassifyNode tem placeholder `[Imagem enviada pelo cliente]`. Substituir por chamada real ao GPT-4o Vision para descrever imagens.
- [ ] **7. Embeddings reais de produtos** — ReindexProcessor cria placeholder. Gerar embeddings CLIP + text-embedding-3-small de verdade.
- [ ] **8. Graceful shutdown** — Adicionar handlers `SIGTERM`/`SIGINT` nos consumers de stream (Hono, FastAPI, NestJS) para drenar mensagens pendentes antes de desligar.
- [ ] **9. Testes automatizados** — Implementar testes de integração do fluxo principal: webhook simulado → stream → agente → persistência no banco.
- [ ] **10. Health checks robustos** — Expandir `/health` do Hono para verificar MinIO, e do NestJS para verificar PostgreSQL + Redis + MinIO.
- [ ] **11. OpenRouter como provider alternativo** — Suporte a modelos mais baratos em dev (Claude Haiku, Gemini Flash, Llama via OpenRouter) além da OpenAI.

## 🟡 Melhorias de DX

- [ ] **12. Hot reload em todos os serviços** — Adicionar volume mounts e `nodemon`/`tsx watch` para Hono e NestJS (FastAPI já tem).
- [ ] **13. CLI de setup (`make dev`)** — Script que cria `.env` a partir de `.env.example`, instala dependências de todos os apps, roda init.sql, cria buckets MinIO, e sobe tudo com `docker compose up`.
- [ ] **14. Swagger/OpenAPI no NestJS** — Configurar `@nestjs/swagger` para gerar documentação da API automaticamente.
- [ ] **15. Migrações de banco** — Configurar TypeORM migrations para versionar o schema ao invés do `init.sql` estático.
- [ ] **16. BullMQ Dashboard** — Adicionar `@bull-board/nestjs` para visualizar filas, jobs e retries em tempo real.

---

**Prioridade sugerida:** 1 → 2 → 11 → 5 → 6 → 9 → depois os demais.
