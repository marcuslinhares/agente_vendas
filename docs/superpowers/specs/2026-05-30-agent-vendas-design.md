# Agente de Vendas com LangGraph — Design Document

**Data:** 2026-05-30
**Status:** Draft v3
**Autor:** Marcus (via brainstorming)

---

## 1. Visão Geral

Sistema multi-serviço de agente de vendas para WhatsApp com memória em 3 níveis, catálogo de tools híbrido, CRM completo e armazenamento de mídias. Operado via Docker Compose em monorepo.

### Stack Principal

| Serviço | Runtime | Framework | Função |
|---|---|---|---|
| Hono | Node.js 22 | Hono + ioredis | Webhook WhatsApp → Redis Stream |
| FastAPI | Python 3.12+ | FastAPI + LangGraph | Agente IA + memória + tools |
| NestJS | Node.js 22 | NestJS + @nestjs/bullmq | API CRM + persistência + jobs |
| Next.js | Node.js 22 | Next.js 14 App Router | CRM Frontend |
| PostgreSQL | — | pgvector v0.7+ | Dados + embeddings vetoriais |
| Redis | — | Redis Stack 7+ | Streams + cache + BullMQ |
| MinIO | — | MinIO | Armazenamento de mídias |

### Escopo e Sub-projetos

Este spec cobre o sistema completo. A implementação será dividida em **3 planos sequenciais**:

| Plano | Serviços | Depende de |
|---|---|---|
| **P1: Infra + Core** | PostgreSQL, Redis, MinIO, Hono, FastAPI/LangGraph | Nada |
| **P2: Persistência + Jobs** | NestJS (consumer + API + BullMQ) | P1 (streams e DB prontos) |
| **P3: CRM** | Next.js | P2 (API NestJS pronta) |

Cada plano é implementado, testado e validado individualmente.

---

## 2. Arquitetura de Serviços

### Fluxo de Dados

```
Evolution API ──▶ Hono ──▶ Redis Stream (webhook:incoming)
                               │
                               ▼
                          FastAPI / LangGraph
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
           Redis Stream   Redis Stream   Redis Stream
           (whatsapp:outbox)           (message:persist)
                    │                      │
                    ▼                      ▼
                  Hono                  NestJS
                    │                      │
                    ▼                      ▼
              Evolution API ───▶ WhatsApp   PostgreSQL + pgvector
                                                    │
                                                    ▼
                                                MinIO (mídias)
```

### Filas (Redis Streams)

Cada stream opera com **consumer groups** para entrega garantida e processamento em paralelo.

| Stream | Producer | Consumer Grupo | Payload |
|---|---|---|---|
| `webhook:incoming` | Hono | `fastapi-workers` | `{ whatsapp_id, message, media?, timestamp }` |
| `whatsapp:outbox` | FastAPI | `hono-workers` | `{ to, text, media_url? }` |
| `message:persist` | FastAPI | `nestjs-workers` | `{ conversation_id, role, content, media?, metadata }` |

### Resiliência nas Streams

- **Dead-letter automática**: mensagens que falham 3+ vezes vão pro stream `{stream}:deadletter` com metadados do erro
- **ACK explícito**: `XACK` só após processamento bem-sucedido
- **Claim mechanism**: workers que falham têm seus pending messages retomados por outros workers (timeout configurável por stream)

---

## 3. LangGraph — Grafo do Agente

### State Schema (TypedDict)

```python
from typing import TypedDict, Optional
from typing_extensions import NotRequired

class AgentState(TypedDict):
    """Estado que flui entre os nós do grafo LangGraph."""
    # Entrada
    whatsapp_id: str
    conversation_id: str
    message_id: str                     # ULID único (idempotência)
    raw_content: str                    # texto original do webhook
    media_url: Optional[str]            # URL do MinIO (se mídia)
    media_type: Optional[str]           # image | audio | video | document
    
    # Parse
    parsed_content: str                 # texto após transcrição/descrição
    intent: str                         # saudacao | duvida | pedido | followup
    customer_id: Optional[str]
    
    # Memória
    l1_messages: list                   # últimas 10 mensagens
    l2_summary: str                     # resumo da conversa
    l3_memories: list                   # resultados da busca vetorial
    l3_triggered: bool                  # se o gate ativou L3
    
    # Execução
    agent_response: str                 # resposta gerada pela LLM
    tool_calls: list                    # tools chamadas na execução
    metadata: dict                      # sentimento, intenção, produto mencionado
    
    # Pós-processamento
    should_update_summary: bool         # message_count % 10 == 0
    new_summary: Optional[str]          # novo resumo gerado
    new_embedding: Optional[list]       # embedding da interação
```

### Nós do Grafo

1. **PARSE_AND_CLASSIFY** → `parsed_content`, `intent`, `customer_id`
   - Extrai texto/mídia do webhook. Se mídia: chama Visão LLM (imagem → descrição) ou Whisper (áudio → texto).
2. **MEMORY_HYDRATE** → `l1_messages`, `l2_summary`
   - Carrega L1 (10 últimas mensagens) + L2 (resumo da conversa) do PostgreSQL.
3. **MEMORY_GATE** → `l3_triggered`
   - LLM avalia se mensagem atual referencia passado distante. Prompt estruturado: `{"trigger_l3": bool, "reason": str}`.
4. **L3_VECTOR_SEARCH** → `l3_memories`
   - Só executa se `l3_triggered == true`. Busca cosine similarity no pgvector, top-5 com score > 0.75.
5. **AGENT_EXECUTE** → `agent_response`, `tool_calls`
   - Monta system prompt com contexto completo (L1 + L2 + L3 se ativado), executa tools, LLM gera resposta.
6. **POST_PROCESS** → `should_update_summary`, `new_embedding`
   - Marca se precisa atualizar resumo (quando message_count % 10 == 0) e gera embedding da interação.
   - A **execução real** da atualização do resumo e salvamento do embedding **não bloqueia a resposta**:
     - FastAPI publica a resposta em `whatsapp:outbox`
     - FastAPI publica em `message:persist` (com flags `update_summary` e `embedding` no metadata)
     - **NestJS** ao consumir `message:persist` executa as atualizações de resumo/embedding de forma síncrona no consumer (já que está fora do grafo, não bloqueia a resposta)

### Error Handling no Grafo

- Cada nó tem `try/except` com fallback definido
- **MEMORY_HYDRATE**: se PostgreSQL falhar, grafo continua com contexto vazio (graceful degradation)
- **MEMORY_GATE**: se LLM falhar, assume `trigger_l3: false` e prossegue
- **AGENT_EXECUTE**: máximo 3 retries com exponential backoff (nó pode se repetir no grafo via `add_conditional_edges`)
- **POST_PROCESS**: falha no resumo/embedding não bloqueia a resposta — NestJS processa ao persistir

### Saída do Grafo

Duas publicações em paralelo:
- **whatsapp:outbox** → Hono envia resposta via Evolution API
- **message:persist** → NestJS persiste no PostgreSQL (inclui flags para atualizar resumo/embedding)

---

## 4. Sistema de Memória (3 Níveis)

### Nível 1 — Recência (Sempre ativo)
- **Fonte:** PostgreSQL, tabela `messages`
- **Query:** `SELECT * FROM messages WHERE conversation_id = :id ORDER BY created_at DESC LIMIT 10`
- **Disparo:** Sempre, em todo request
- **Fallback:** se query falhar, contexto L1 vazio

### Nível 2 — Resumo da Conversa (A cada 10 mensagens)
- **Fonte:** PostgreSQL, tabela `conversations` campo `summary`
- **Formato:** Texto curto gerado por LLM (~500b-2KB)
- **Atualização:** Marcado no POST_PROCESS, executado pelo NestJS ao consumir `message:persist`
  - Se `message_count % 10 == 0`, NestJS chama LLM com prompt: *"Resuma a conversa completa até agora, incorporando este novo bloco"*
  - Atualiza `conversations.summary` e incrementa `summary_version`
- **Fallback:** se não existir resumo, L2 vazio. Se LLM falhar ao atualizar, tenta de novo no próximo ciclo.

### Nível 3 — Busca Vetorial (Sob demanda, via gate)
- **Fonte:** pgvector, tabela `message_embeddings`
- **Gate:** Nó MEMORY_GATE — chamada LLM estruturada.
- **Query:** `SELECT content, media_url, media_type, 1 - (embedding <=> :query_embedding) AS score FROM message_embeddings WHERE conversation_id = :id AND created_at < :cutoff ORDER BY score DESC LIMIT 5`
- **Threshold:** Score > 0.75
- **Embedding model:** `text-embedding-3-small` (1536 dimensões)
- **Fallback:** se LLM do gate falhar, assume `trigger_l3: false`. Se pgvector falhar, L3 vazio.

---

## 5. Integração com Mídias (MinIO + pgvector)

### Fluxo de Mídia

```
Webhook chega com mídia (imagem/áudio/vídeo/doc)
    │
    ├─ 1. Hono baixa da Evolution API para buffer em memória
    │
    ├─ 2. Hono faz upload pro MinIO
    │      bucket: conversations-media/
    │      prefix: {whatsapp_id}/{uuid}.{ext}
    │
    ├─ 3. Hono publica no stream webhook:incoming
    │      { ..., media_url: "http://minio:9000/conversations-media/{id}/{uuid}.ext",
    │        media_type: "image" }
    │
    └─ 4. FastAPI recebe o stream:
         ├─ 4a. Baixa do MinIO (via URL) para processamento
         ├─ 4b. Gera representação textual:
         │      - Imagem → Visão LLM (gpt-4o) descreve
         │      - Áudio → Whisper transcreve
         │      - Vídeo → extrai frames, descreve cenas
         │      - Documento → extrai texto (Tika / PyMuPDF)
         ├─ 4c. Salva descrição como `parsed_content` no state
         │
         └─ 4d. FastAPI gera DOIS embeddings no nó POST_PROCESS:
              ├─ CLIP ViT-B-32: embedding VISUAL da imagem bruta (512d)
              └─ text-embedding-3-small: embedding TEXTUAL da descrição (1536d)
         │
         └─ 4e. Publica ambos no stream message:persist
              { embedding_clip: [...512], embedding_text: [...1536] }

    NestJS ao consumir message:persist:
    ├─ Salva a mensagem com content + media_url (aponta pro MinIO)
    ├─ Salva embedding_clip + embedding_text no pgvector
    └─ NÃO gera embedding — só persiste o que veio pronto

    Produtos (upload no CRM):
    └─ NestJS gera embedding na hora do upload:
         ├─ CLIP na imagem do produto
         └─ text-embedding-3-small na descrição
         └─ Salva direto em product_embeddings
```

### Thumbnails

- **Quem gera:** Hono (no momento do upload), redimensiona imagem para 200x200 webp
- **Onde salva:** Mesmo bucket `conversations-media/`, prefix `thumbnails/{whatsapp_id}/{uuid}.webp`
- **Quando:** Opcional — só para imagens > 100KB. Hono publica `media_url` e `thumbnail_url` separados no stream

### Buckets MinIO

| Bucket | Finalidade | Política | TTL |
|---|---|---|---|
| `conversations-media` | Mídias de conversas + thumbnails (prefixos) | Privado (URLs assinadas) | Indefinido |
| `products` | Imagens de produtos (webp, max 1920px) | Público (CDN-ready) | Indefinido |
| `temporary` | Uploads temporários (cleanup job) | Privado | 1h |

### Tabelas de Embedding

- **message_embeddings** — Embeddings de mensagens de conversa (L3)
  - Geração: FastAPI (nó POST_PROCESS) — CLIP na imagem bruta + text-embedding-3-small na descrição
  - NestJS apenas persiste os embeddings prontos no pgvector
  - Fallback: se embedding falhar, mensagem persiste sem embedding — job noturno reconcilia
- **product_embeddings** — Embeddings de produtos (RAG de catálogo)
  - Geração: NestJS (síncrono no upload do produto via CRM)
  - CLIP na imagem do produto + text-embedding-3-small na descrição
  - Job noturno de reconciliação: varre produtos sem embedding

Índice vetorial: `IVFFlat` com `vector_cosine_ops`, lists parametrizável.

---

## 6. Catálogo de Tools

### Arquitetura Híbrida

**Core Tools** (código Python, versionadas com o repositório):

| Tool | Descrição | Parâmetros | Idempotente? |
|---|---|---|---|
| `get_products` | Lista produtos com filtro | `{ category?, search?, page, limit }` | ✅ Sim (leitura) |
| `check_stock` | Verifica estoque | `{ product_id }` | ✅ Sim (leitura) |
| `create_order` | Fecha pedido | `{ customer_id, items[], payment_method }` | ❌ Não → usa idempotency key |
| `get_order_status` | Consulta status | `{ order_id }` | ✅ Sim (leitura) |
| `classify_client` | Classifica lead | `{ conversation_id, sentiment, intent }` | ✅ Sim (idempotente) |
| `schedule_followup` | Agenda follow-up | `{ customer_id, days, message_template }` | ❌ Não → usa idempotency key |

**Regra de retry por tipo:**

| Tipo | Retry | Justificativa |
|---|---|---|
| Tools de **leitura** (GET) | 2 retries com backoff | Seguro — não causa efeito colateral |
| Tools de **escrita** (POST/PUT) | Sem retry automático | Usa **idempotency key** (hash dos parâmetros + timestamp) — se falhar, retry manual seguro |
| **Tools dinâmicas** | Sem retry | API externa não temos controle — retry pode causar duplicação |

**Dynamic Tools** (armazenadas no banco, gerenciáveis via CRM):

- Tabela `tools_catalog`: name, description, schema (JSON), endpoint, http_method, headers, is_active, rate_limit, timeout_ms
- Carregadas no startup do FastAPI. Cache em Redis com TTL 5min.
- Invalidação: NestJS publica Redis Pub/Sub canal `tools:updated` → FastAPI deleta cache.
- Execução: HTTP para o endpoint registrado, validado pelo schema.

### Interface Padronizada

```python
@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict  # JSON Schema
    is_idempotent: bool
    execute: Callable[[dict], Awaitable[str]]
```

### Error Handling em Tools

- **Timeout:** cada tool tem timeout configurável (default 10s). Se expirar, retorna "Tool X timed out".
- **HTTP error:** se endpoint retornar 4xx/5xx, retorna mensagem de erro amigável pro LLM.
- **Log:** toda execução registrada em `tool_execution_log` (tool_name, params, response, duration_ms, success, error_message).
- **Rate limit:** tools dinâmicas têm campo `rate_limit` (req/min) — FastAPI respeita com Redis contador.

---

## 7. NestJS — Backend e Jobs

### Stream Consumer (`message:persist`)

Consome do consumer group `nestjs-workers` com `XREADGROUP`:

```typescript
async handleMessage(msg: MessagePersistDTO) {
  // Idempotência: verifica se mensagem já foi processada pelo ID único
  if (await this.messageRepo.exists(msg.message_id)) {
    return; // ACK silencioso
  }

  // 1. Salvar mensagem
  const message = await this.messageRepo.save({ ... });

  // 2. Gerar embedding (falha não-bloqueante)
  if (msg.generate_embedding) {
    try {
      const embedding = await this.embeddingService.generate(msg.content);
      await this.embeddingRepo.save({ messageId: message.id, embedding });
    } catch (err) {
      this.logger.warn(`Embedding failed for message ${message.id}`);
      // Mensagem persiste — job noturno reconcilia
    }
  }

  // 3. Atualizar resumo (L2) se necessário
  if (msg.update_summary) {
    try {
      const fullHistory = await this.messageRepo.findByConversation(msg.conversation_id);
      const newSummary = await this.llmService.summarize(fullHistory);
      await this.conversationRepo.updateSummary(msg.conversation_id, newSummary);
    } catch (err) {
      this.logger.warn(`Summary update failed for conversation ${msg.conversation_id}`);
      // Job summaries:stale vai recuperar
    }
  }

  // 4. Atualizar customer.last_contact_at
  await this.customerRepo.updateLastContact(msg.whatsapp_id);
}
```

**Dead-letter:** após 3 falhas, mensagem vai pra `message:persist:deadletter`. Job `dlq:monitor` notifica admin.

### REST API (/api/v1)

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| GET | /conversations | Lista conversas (filtro: status, classification, date) | JWT |
| GET | /conversations/:id | Detalhes + mensagens paginadas | JWT |
| GET | /messages/:conv_id | Mensagens paginadas (offset/limit) | JWT |
| POST | /products | Criar produto | JWT |
| PUT | /products/:id | Atualizar produto | JWT |
| DELETE | /products/:id | Deletar produto | JWT |
| GET | /customers | Listar clientes (filtro: classification, tags) | JWT |
| POST | /customers/classify | Classificar cliente manualmente | JWT |
| POST | /tools | Criar tool dinâmica | JWT + admin |
| PUT | /tools/:id | Atualizar tool | JWT + admin |
| GET | /tools | Listar tools ativas | JWT |
| POST | /tools/:id/test | Testar tool (dry-run) | JWT + admin |
| GET | /orders | Listar pedidos | JWT |
| POST | /upload/product | Upload imagem produto → MinIO | JWT |
| POST | /auth/login | Login (email + senha) | Público |
| POST | /auth/register | Registrar usuário | Público |

### BullMQ Jobs

| Job | Trigger | Descrição | Error Handling |
|---|---|---|---|
| followup:classification | Cron 9h diário | Busca leads mornos sem contato >3d, publica em `whatsapp:outbox` | Retry 3x, log, pula lead |
| products:reindex | Cron 2h noturno | Varre produtos sem embedding, gera e salva | Retry 3x por produto, log |
| minio:cleanup | Cron 6h | Remove temporários >1h | Best-effort |
| summaries:stale | Cron 30min | Fallback: atualiza resumos pendentes | Log apenas |
| dlq:monitor | Cron 1h | Verifica dead-letter queues, notifica se >0 | Log |

---

## 8. Schema PostgreSQL (pgvector) — Completo

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Tabelas

```sql
-- Conversas
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_id     TEXT NOT NULL UNIQUE,          -- "5511999999999@c.us"
    customer_id     UUID REFERENCES customers(id) ON DELETE SET NULL,
    status          VARCHAR(20) DEFAULT 'active'
                    CHECK (status IN ('active', 'closed', 'followup')),
    summary         TEXT,
    summary_version INT DEFAULT 0,
    message_count   INT DEFAULT 0,
    classification  VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Mensagens
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id      TEXT UNIQUE NOT NULL,           -- ULID do FastAPI (idempotência)
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT,
    media_url       TEXT,
    thumbnail_url   TEXT,
    media_type      VARCHAR(20),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Embeddings de mensagens (L3)
CREATE TABLE message_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id      UUID REFERENCES messages(id) ON DELETE SET NULL,
    content         TEXT,
    media_url       TEXT,
    media_type      VARCHAR(20),
    embedding       VECTOR(1536),
    embedding_clip    VECTOR(512),       -- embedding visual da imagem bruta (CLIP)
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Embeddings de produtos (RAG)
CREATE TABLE product_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    content         TEXT,
    media_url       TEXT,
    embedding       VECTOR(1536),
    embedding_clip    VECTOR(512),       -- embedding visual da imagem do produto (CLIP)
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Catálogo de tools dinâmicas
CREATE TABLE tools_catalog (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL UNIQUE,
    description     TEXT NOT NULL,
    schema          JSONB NOT NULL DEFAULT '{}',
    endpoint        TEXT NOT NULL,
    http_method     VARCHAR(10) DEFAULT 'POST',
    headers         JSONB DEFAULT '{}',
    category        VARCHAR(50),
    rate_limit      INT DEFAULT 0,
    timeout_ms      INT DEFAULT 10000,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Produtos
CREATE TABLE products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    price           DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    category        VARCHAR(100),
    stock           INT DEFAULT 0 CHECK (stock >= 0),
    image_url       TEXT,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Clientes
CREATE TABLE customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_id     TEXT UNIQUE NOT NULL,
    name            VARCHAR(200),
    email           VARCHAR(200),
    phone           VARCHAR(20),
    classification  VARCHAR(50) CHECK (classification IN (
                        'lead_quente', 'lead_morno', 'lead_frio', 'cliente'
                    )),
    tags            TEXT[] DEFAULT '{}',
    metadata        JSONB DEFAULT '{}',
    last_contact_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Pedidos
CREATE TABLE orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    items           JSONB NOT NULL DEFAULT '[]',
    total           DECIMAL(10,2) NOT NULL CHECK (total >= 0),
    status          VARCHAR(20) DEFAULT 'pending'
                    CHECK (status IN ('pending', 'confirmed', 'shipped', 'cancelled')),
    payment_method  VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Log de execução de tools
CREATE TABLE tool_execution_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name       VARCHAR(100) NOT NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    parameters      JSONB DEFAULT '{}',
    response        TEXT,
    duration_ms     INT,
    success         BOOLEAN DEFAULT false,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Usuários do CRM
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    name            VARCHAR(200),
    role            VARCHAR(20) DEFAULT 'admin' CHECK (role IN ('admin', 'agent')),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Migrations tracking (opcional — pode usar TypeORM migrations)
CREATE TABLE _migrations (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    applied_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### Índices

```sql
CREATE INDEX idx_msg_embeddings_conv ON message_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_product_embeddings ON product_embeddings
CREATE INDEX idx_msg_embeddings_clip ON message_embeddings
    USING ivfflat (embedding_clip vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_product_embeddings_clip ON product_embeddings
    USING ivfflat (embedding_clip vector_cosine_ops) WITH (lists = 100);
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_messages_conv_created ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_conversations_whatsapp ON conversations(whatsapp_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_classification ON conversations(classification);
CREATE INDEX idx_customers_classification ON customers(classification);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_embeddings_conv_created ON message_embeddings(conversation_id, created_at DESC);
CREATE INDEX idx_tools_active ON tools_catalog(is_active) WHERE is_active = true;
CREATE INDEX idx_tool_log_created ON tool_execution_log(created_at DESC);
```

---

## 9. Modelo de Segurança

### Webhook Evolution API
- Verificação de assinatura: header `X-Evolution-Signature` validado com HMAC-SHA256 no Hono
- IP whitelist opcional: lista de IPs permitidos

### Inter-service Auth
- Redis Streams em rede Docker interna isolada — sem autenticação entre serviços
- MinIO: acesso por chave de acesso/secreta via env vars

### CRM Auth
- JWT-based: login em `/api/v1/auth/login`, token JWT (7d)
- Rotas protegidas por `@UseGuards(JwtAuthGuard)` no NestJS
- Roles: `admin` (tudo), `agent` (leitura + classificar cliente)

---

## 10. Observabilidade

### Logging Estruturado
- JSON em stdout (capturado pelo Docker)
- Campos: `service`, `timestamp`, `level`, `message`, `request_id`, `conversation_id`, `duration_ms`

### Métricas
- Prometheus + Grafana (add-on opcional)
- Métricas: msgs/min, latência do grafo, taxa de erro, tools executadas, chamadas LLM

### Health Checks
- Cada serviço expõe `GET /health` e `GET /ready`

---

## 11. CRM Next.js

### Páginas

| Rota | Página | Descrição |
|---|---|---|
| `/` | Dashboard | KPIs: conversas ativas, leads por classificação, pedidos hoje |
| `/conversations` | Conversas | Lista com busca e filtro |
| `/conversations/[id]` | Chat | Histórico da conversa + campo "Enviar mensagem" (envia via API NestJS → Redis Stream `whatsapp:outbox`) |
| `/products` | Produtos | CRUD com upload de imagem |
| `/customers` | Clientes | Lista com classificação e tags |
| `/tools` | Tools | Gerenciamento de tools dinâmicas |
| `/orders` | Pedidos | Lista com status |
| `/settings` | Config | Evolution API, LLM model, webhook status |

### Envio manual via CRM
O chat em `/conversations/[id]` permite ao agente humano **enviar mensagens reais** (não simuladas) para o WhatsApp do cliente. O Next.js chama `POST /api/v1/conversations/:id/send` no NestJS, que publica no stream `whatsapp:outbox` — Hono consome e envia via Evolution API.

### Data Fetching
- `@tanstack/react-query` para chamadas à API do NestJS
- Server components para páginas públicas (login)
- Client components para dashboards e CRUDs

---

## 12. Infraestrutura Docker Compose

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: agentevendas
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./infra/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d agentevendas"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD:-minioadmin}
    volumes:
      - miniodata:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 5s
      retries: 5

  hono:
    build: ./apps/hono
    ports: ["3000:3000"]
    environment: &hono-env
      REDIS_URL: redis://redis:6379
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_USER:-minioadmin}
      MINIO_SECRET_KEY: ${MINIO_PASSWORD:-minioadmin}
      EVOLUTION_API_URL: ${EVOLUTION_API_URL}
      EVOLUTION_API_KEY: ${EVOLUTION_API_KEY}
      EVOLUTION_WEBHOOK_SECRET: ${EVOLUTION_WEBHOOK_SECRET}
    depends_on:
      redis: { condition: service_healthy }
      minio: { condition: service_healthy }

  fastapi:
    build: ./apps/fastapi
    ports: ["8000:8000"]
    environment:
      <<: *hono-env
      DATABASE_URL: postgresql+asyncpg://app:${DB_PASSWORD}@postgres:5432/agentevendas
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4o}
      OPENAI_EMBEDDING_MODEL: ${OPENAI_EMBEDDING_MODEL:-text-embedding-3-small}
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }

  nestjs:
    build: ./apps/nestjs
    ports: ["4000:4000"]
    environment:
      <<: *hono-env
      DATABASE_URL: postgresql://app:${DB_PASSWORD}@postgres:5432/agentevendas
      JWT_SECRET: ${JWT_SECRET}
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
      minio: { condition: service_healthy }

  web:
    build: ./apps/web
    ports: ["3001:3000"]
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:4000/api/v1
    depends_on: [nestjs]

volumes:
  pgdata:  redisdata:  miniodata:
```

---

## 13. Estrutura do Monorepo

```
agente_vendas/
├── docker-compose.yml
├── .env.example
├── .github/workflows/
│   ├── ci.yml
│   └── deploy.yml
├── apps/
│   ├── hono/
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── index.ts
│   │       ├── routes/
│   │       │   ├── webhook.ts
│   │       │   └── health.ts
│   │       └── services/
│   │           ├── redis.ts
│   │           ├── minio.ts
│   │           └── evolution.ts
│   ├── fastapi/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── graph/
│   │       │   ├── agent.py
│   │       │   ├── nodes/
│   │       │   │   ├── parse_classify.py
│   │       │   │   ├── memory_hydrate.py
│   │       │   │   ├── memory_gate.py
│   │       │   │   ├── l3_search.py
│   │       │   │   ├── agent_execute.py
│   │       │   │   └── post_process.py
│   │       │   └── state.py
│   │       ├── tools/
│   │       │   ├── registry.py
│   │       │   ├── core/
│   │       │   │   ├── products.py
│   │       │   │   ├── orders.py
│   │       │   │   ├── customers.py
│   │       │   │   └── followup.py
│   │       │   └── dynamic_executor.py
│   │       └── services/
│   │           ├── redis.py
│   │           ├── postgres.py
│   │           └── minio.py
│   ├── nestjs/
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   ├── nest-cli.json
│   │   └── src/
│   │       ├── main.ts
│   │       ├── app.module.ts
│   │       ├── modules/
│   │       │   ├── auth/
│   │       │   ├── conversations/
│   │       │   ├── messages/
│   │       │   ├── products/
│   │       │   ├── customers/
│   │       │   ├── orders/
│   │       │   ├── tools/
│   │       │   └── minio/
│   │       ├── queue/
│   │       │   ├── followup.processor.ts
│   │       │   ├── reindex.processor.ts
│   │       │   ├── cleanup.processor.ts
│   │       │   └── dlq-monitor.processor.ts
│   │       └── stream/
│   │           └── persist.consumer.ts
│   └── web/
│       ├── Dockerfile
│       ├── package.json
│       ├── next.config.ts
│       └── src/
│           ├── app/
│           │   ├── (auth)/login/
│           │   ├── (auth)/register/
│           │   ├── (dashboard)/
│           │   │   ├── page.tsx
│           │   │   ├── conversations/
│           │   │   ├── products/
│           │   │   ├── customers/
│           │   │   ├── tools/
│           │   │   └── orders/
│           │   └── layout.tsx
│           ├── components/
│           │   ├── ui/ (shadcn)
│           │   └── shared/
│           └── lib/api-client.ts
├── packages/
│   └── shared-types/
│       ├── package.json
│       └── src/
│           ├── index.ts
│           ├── webhook.ts
│           ├── message.ts
│           └── product.ts
└── infra/
    ├── postgres/init.sql
    └── minio/buckets.sh
```
