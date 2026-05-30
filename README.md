# Agente de Vendas — AI Sales Agent for WhatsApp

A multi-service, production-ready AI sales agent system that integrates with WhatsApp via the [Evolution API](https://github.com/EvolutionAPI/evolution-api). Built around a **LangGraph** AI agent with three-level memory, a hybrid tool catalog, and a full CRM frontend — all orchestrated through Docker Compose.

---

## Architecture Overview

The system is composed of **7 Docker containers** communicating through **Redis Streams** for guaranteed, at-least-once message delivery:

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
                                                MinIO (media)
```

### Services

| Service | Runtime | Framework | Purpose |
|---------|---------|-----------|---------|
| **Hono** | Node.js 22 | Hono + ioredis | WhatsApp webhook receiver → Redis Stream |
| **FastAPI** | Python 3.12+ | FastAPI + LangGraph | AI Agent core: memory, tools, graph execution |
| **NestJS** | Node.js 22 | NestJS + TypeORM + BullMQ | REST API, persistence consumer, scheduled jobs |
| **Next.js** | Node.js 22 | Next.js 14 App Router | CRM frontend (7 pages) |
| **PostgreSQL** | — | pgvector 0.7+ | Relational data + vector embeddings |
| **Redis** | — | Redis 7 Streams | Message queues, cache, BullMQ backend |
| **MinIO** | — | MinIO | S3-compatible media storage |

### Communication

Three Redis Streams with consumer groups form the backbone:

| Stream | Producer | Consumer Group | Payload |
|--------|----------|----------------|---------|
| `webhook:incoming` | Hono | `fastapi-workers` | `{ whatsapp_id, message, media?, timestamp }` |
| `whatsapp:outbox` | FastAPI | `hono-workers` | `{ to, text, media_url? }` |
| `message:persist` | FastAPI | `nestjs-workers` | `{ conversation_id, role, content, media, embeddings }` |

Each stream uses explicit ACKs (`XACK`), consumer groups for parallel processing, and automatic dead-letter streams after 3 failed delivery attempts.

---

## Features

### WhatsApp Integration
- Webhook receiver via Evolution API with HMAC-SHA256 signature verification
- Media download (images, audio, video, documents) → MinIO upload
- Auto-thumbnailing for large images (>100KB)
- Outbound message delivery via Evolution API

### LangGraph AI Agent
6-node directed acyclic graph:

| Node | Function | Fallback |
|------|----------|----------|
| **parse_classify** | Extract content, detect intent (saudação/duvida/pedido/agradecimento), get/create conversation | Graceful degradation |
| **memory_hydrate** | Load L1 (last 10 messages) + L2 (summary) from PostgreSQL | Empty context |
| **memory_gate** | LLM decides if message references distant past → triggers L3 | `trigger_l3: false` |
| **l3_search** | pgvector cosine similarity search (top-5, threshold > 0.75) | Empty results |
| **agent_execute** | Build system prompt with all context, call LLM with tool catalog | Error message to user |
| **post_process** | Generate CLIP + text embeddings for persistence | Skip embeddings |

### Three-Level Memory System

| Level | Source | Trigger | Scope |
|-------|--------|---------|-------|
| **L1 — Recency** | `messages` table (PostgreSQL) | Every request | Last 10 messages |
| **L2 — Summary** | `conversations.summary` (PostgreSQL) | Every request | LLM-generated conversation summary (~500B–2KB) |
| **L3 — Vector Search** | `message_embeddings` (pgvector) | LLM gate decides | Cosine similarity on 1536d embeddings, score > 0.75 |

The **Memory Gate** (L3) is an LLM call with a structured JSON prompt: `{"trigger_l3": bool, "reason": "..."}`. It only activates semantic search when the user references something said earlier in the conversation.

### Dual Embedding System

- **CLIP ViT-B-32** (512 dimensions): Visual embedding of raw images (pretrained on LAION-2B)
- **text-embedding-3-small** (1536 dimensions): Textual embedding of message content

Both are generated in the **post_process** node and persisted to `message_embeddings` by NestJS. Product embeddings use the same dual system for RAG catalog search.

### Hybrid Tool Catalog

**6 Core Tools** (Python, versioned with repo):

| Tool | Description | Idempotent |
|------|-------------|------------|
| `get_products` | List products with category/search filters | ✅ |
| `check_stock` | Check stock for a specific product | ✅ |
| `create_order` | Create a new order (customer, items, total, payment) | ❌ |
| `get_order_status` | Query order status by ID | ✅ |
| `classify_client` | Classify lead (lead_quente/morno/frio/cliente) | ✅ |
| `schedule_followup` | Schedule a follow-up message | ❌ |

**Dynamic Tools** (DB-backed, manageable via CRM):
- Stored in `tools_catalog` table with schema, endpoint, headers, rate limits
- Loaded at FastAPI startup + cached in Redis (TTL 5min)
- Invalidated via Redis Pub/Sub (`tools:updated` channel)
- HTTP execution with configurable timeout and rate limiting

### BullMQ Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| `followup:classification` | Daily 09:00 | Send follow-up to `lead_morno` customers without contact >3 days |
| `products:reindex` | Daily 02:00 | Generate embeddings for products missing them |
| `summaries:stale` | Every 30min | Recover stale conversation summaries |
| `dlq:monitor` | Every 1h | Monitor dead-letter queues |

### JWT-Authenticated REST API

All endpoints under `/api/v1` with JWT Bearer auth (except login/register):

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Login, receive JWT |
| GET | `/conversations` | List conversations (filter by status, classification) |
| GET | `/conversations/:id` | Conversation details + messages |
| POST | `/conversations/:id/send` | Send message to conversation via outbox stream |
| GET | `/messages/:conversationId` | Paginated messages (offset/limit) |
| GET | `/products` | List products (filter by category, search) |
| GET | `/products/:id` | Get product by ID |
| POST | `/products` | Create product |
| PUT | `/products/:id` | Update product |
| DELETE | `/products/:id` | Soft-delete product |
| GET | `/customers` | List customers (filter by classification) |
| GET | `/customers/:id` | Get customer by ID |
| POST | `/customers/classify` | Classify customer |
| GET | `/orders` | List orders (filter by status, paginated) |
| GET | `/orders/:id` | Get order by ID |
| GET | `/tools` | List active dynamic tools |
| GET | `/tools/all` | List all tools |
| GET | `/tools/:id` | Get tool definition |
| POST | `/tools` | Create a new dynamic tool |
| PUT | `/tools/:id` | Update a tool |
| POST | `/tools/:id/test` | Test a tool (dry-run HTTP call) |
| POST | `/upload/product/:productId` | Upload product image → MinIO |

### CRM Frontend (Next.js)

7 pages with Portuguese UI:

| Page | Route | Description |
|------|-------|-------------|
| **Dashboard** | `/` | Stats: active conversations, leads, orders, conversion rate |
| **Conversas** | `/conversations` | List/search conversations, view messages, send manual replies |
| **Produtos** | `/products` | CRUD products, upload images, manage catalog |
| **Clientes** | `/customers` | Search customers, filter by classification, manual classify |
| **Pedidos** | `/orders` | List orders with status filters |
| **Tools** | `/tools` | Register/test dynamic tools, manage catalog |
| **Configurações** | `/settings` | Account settings |

### Media Pipeline

1. Webhook arrives with media (image/audio/video/document)
2. Hono downloads from Evolution API → uploads to MinIO (`conversations-media/` bucket)
3. Hono publishes stream event with `media_url` pointing to MinIO
4. FastAPI's post_process node:
   - Downloads image from MinIO
   - Generates CLIP visual embedding (512d) on raw image
   - Generates text-embedding-3-small (1536d) on description
5. Both embeddings published in `message:persist` stream
6. NestJS persists message + embeddings to pgvector

Product images follow a similar flow via the CRM upload endpoint → `products/` bucket (public, CDN-ready).

---

## Project Structure

```
agente_vendas/
├── apps/
│   ├── hono/                    # WhatsApp webhook receiver
│   │   ├── src/
│   │   │   ├── index.ts         # HTTP server + outbox consumer
│   │   │   ├── routes/
│   │   │   │   ├── webhook.ts   # POST /webhook/evolution
│   │   │   │   └── health.ts    # GET /health, /ready
│   │   │   └── services/
│   │   │       ├── redis.ts     # Redis Streams (publish webhook, consume outbox)
│   │   │       ├── evolution.ts # Evolution API client (send, download, verify)
│   │   │       └── minio.ts     # S3 client for media upload
│   │   └── Dockerfile
│   │
│   ├── fastapi/                  # LangGraph AI Agent
│   │   ├── app/
│   │   │   ├── main.py          # FastAPI app with stream consumer background task
│   │   │   ├── config.py        # Pydantic settings (env vars)
│   │   │   ├── graph/
│   │   │   │   ├── agent.py     # LangGraph StateGraph: 6 nodes, conditional edges
│   │   │   │   ├── state.py     # AgentState TypedDict
│   │   │   │   └── nodes/
│   │   │   │       ├── parse_classify.py   # Content extraction + intent
│   │   │   │       ├── memory_hydrate.py   # L1 + L2 loading
│   │   │   │       ├── memory_gate.py      # LLM gate for L3 trigger
│   │   │   │       ├── l3_search.py        # pgvector cosine similarity search
│   │   │   │       ├── agent_execute.py    # LLM call with tools
│   │   │   │       └── post_process.py     # CLIP + text embeddings
│   │   │   ├── tools/
│   │   │   │   ├── registry.py  # ToolRegistry: core + dynamic tools, logging
│   │   │   │   └── core/
│   │   │   │       ├── products.py   # get_products, check_stock
│   │   │   │       ├── orders.py     # create_order, get_order_status
│   │   │   │       └── customers.py  # classify_client, schedule_followup
│   │   │   └── services/
│   │   │       ├── postgres.py  # asyncpg pool, queries, vector search
│   │   │       ├── redis.py     # Redis Stream consumer/publisher helpers
│   │   │       └── minio.py     # S3 client for media download
│   │   └── Dockerfile
│   │
│   ├── nestjs/                   # Backend API + Persistence + Jobs
│   │   ├── src/
│   │   │   ├── main.ts          # NestJS bootstrap (prefix /api/v1, CORS, validation)
│   │   │   ├── app.module.ts    # TypeORM, BullMQ, all modules
│   │   │   ├── entities/        # TypeORM entities (11 tables)
│   │   │   ├── modules/
│   │   │   │   ├── auth/        # JWT login/register
│   │   │   │   ├── conversations/ # Conversations CRUD + manual send
│   │   │   │   ├── messages/    # Paginated message history
│   │   │   │   ├── products/    # Product CRUD
│   │   │   │   ├── customers/   # Customer list + classify
│   │   │   │   ├── orders/      # Order list
│   │   │   │   ├── tools/       # Dynamic tools catalog CRUD + test
│   │   │   │   └── minio/       # Product image upload
│   │   │   ├── stream/
│   │   │   │   └── persist.consumer.ts  # message:persist consumer
│   │   │   └── queue/
│   │   │       ├── followup.processor.ts # Daily lead follow-up
│   │   │       └── reindex.processor.ts  # Nightly embedding reindex
│   │   └── Dockerfile
│   │
│   └── web/                      # Next.js CRM Frontend
│       ├── src/
│       │   ├── app/
│       │   │   ├── (auth)/       # Login + Register pages
│       │   │   ├── (dashboard)/  # Dashboard, Conversations, Products, Customers,
│       │   │   │                 # Orders, Tools, Settings (7 pages)
│       │   │   ├── layout.tsx
│       │   │   └── page.tsx
│       │   ├── components/
│       │   │   ├── ui/           # Reusable UI components (card, input, badge, etc.)
│       │   │   └── providers.tsx
│       │   └── lib/
│       │       ├── api-client.ts # JWT-authenticated fetch wrapper
│       │       └── utils.ts      # Tailwind CSS utility merge
│       ├── tailwind.config.ts
│       └── Dockerfile
│
├── packages/
│   └── shared-types/             # Shared Zod schemas (npm workspace)
│       └── src/
│
├── infra/
│   ├── postgres/
│   │   └── init.sql             # Schema: 8 tables, pgvector indexes, IVFFlat indices
│   └── minio/
│       └── buckets.sh           # Creates buckets + lifecycle policies on startup
│
├── docs/
│   └── superpowers/
│       ├── specs/               # Design document (828 lines, 8 sections)
│       └── plans/               # Implementation plans (P1 infra, P2 backend, P3 frontend)
│
├── docker-compose.yml           # 7 services with healthchecks and dependencies
└── .env.example                 # All required environment variables
```

---

## Quick Start

### Prerequisites

- Docker and Docker Compose v2
- An [Evolution API](https://github.com/EvolutionAPI/evolution-api) instance (or use one from the ecosystem)
- OpenAI API key with access to `gpt-4o` and `text-embedding-3-small`

### Setup

```bash
# 1. Clone and enter the project
git clone <repo-url> agente_vendas
cd agente_vendas

# 2. Configure environment variables
cp .env.example .env

# 3. Edit .env with your keys
#    Minimum required:
#    - DB_PASSWORD (change from default in production)
#    - OPENAI_API_KEY (gpt-4o + text-embedding-3-small access)
#    - JWT_SECRET (32+ character random string)
#    - EVOLUTION_API_URL + EVOLUTION_API_KEY
#    - EVOLUTION_WEBHOOK_SECRET

# 4. Start all services
docker compose up -d --build --wait

# 5. Access the CRM
open http://localhost:3001

# 6. Create your admin account
open http://localhost:3001/register
```

### Verify Health

```bash
# Check all services
curl http://localhost:3000/health    # Hono
curl http://localhost:8000/health    # FastAPI/LangGraph
curl http://localhost:4000/api/v1    # NestJS (will return 404 but confirms reachable)

# FastAPI readiness (checks DB connectivity)
curl http://localhost:8000/ready
```

### Configure WhatsApp Webhook

Point your Evolution API instance to:

```
POST http://localhost:3000/webhook/evolution
```

Add the `x-evolution-signature` header and configure `EVOLUTION_WEBHOOK_SECRET` matching both sides.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_PASSWORD` | ✅ | — | PostgreSQL password |
| `MINIO_USER` | | `minioadmin` | MinIO root user |
| `MINIO_PASSWORD` | | `minioadmin` | MinIO root password |
| `EVOLUTION_API_URL` | ✅ | `http://evolution:8080` | Evolution API base URL |
| `EVOLUTION_API_KEY` | ✅ | — | Evolution API authentication key |
| `EVOLUTION_WEBHOOK_SECRET` | ✅ | — | HMAC-SHA256 secret for webhook verification |
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key |
| `OPENAI_MODEL` | | `gpt-4o` | LLM model for agent + memory gate |
| `OPENAI_EMBEDDING_MODEL` | | `text-embedding-3-small` | Embedding model for L3 search |
| `JWT_SECRET` | ✅ | — | Secret key for JWT token signing (change in production) |

---

## Database Schema (PostgreSQL + pgvector)

8 tables with IVFFlat vector indexes on 1536d and 512d embeddings:

| Table | Purpose | Key Columns | Vector |
|-------|---------|-------------|--------|
| `customers` | WhatsApp contacts with classification | `whatsapp_id`, `classification`, `tags` | — |
| `conversations` | Chat sessions per WhatsApp ID | `whatsapp_id`, `status`, `summary`, `message_count` | — |
| `messages` | Individual messages (user/assistant/system) | `message_id` (ULID, idempotent), `role`, `content`, `media_url` | — |
| `message_embeddings` | L3 memory vector store | `conversation_id`, `content`, `media_url` | VECTOR(1536) + VECTOR(512) |
| `products` | Product catalog | `name`, `price`, `stock`, `category`, `image_url` | — |
| `product_embeddings` | RAG catalog embeddings | `product_id`, `content`, `media_url` | VECTOR(1536) + VECTOR(512) |
| `orders` | Customer orders | `customer_id`, `items` (JSONB), `total`, `status` | — |
| `tools_catalog` | Dynamic tool definitions | `name`, `endpoint`, `schema` (JSONB), `rate_limit` | — |
| `users` | CRM user accounts | `email`, `password_hash`, `role` | — |
| `tool_execution_log` | Audit trail for all tool calls | `tool_name`, `parameters`, `duration_ms`, `success` | — |

Vector indexes use `IVFFlat` with `vector_cosine_ops` for efficient approximate nearest neighbor search.

---

## MinIO Buckets

| Bucket | Purpose | Access | TTL |
|--------|---------|--------|-----|
| `conversations-media` | Chat media (images, audio, video) | Private (signed URLs) | Indefinite |
| `products` | Product images (WebP, max 1920px) | Public (CDN-ready) | Indefinite |
| `temporary` | Temp uploads | Private | 1 hour |

---

## Development

### Architecture Principles

- **Independent deployability**: Each service has its own Dockerfile and can be scaled independently
- **Loose coupling via streams**: No direct HTTP between services — Redis Streams provide buffering, retry, and backpressure
- **Graceful degradation**: Every node has fallback behavior; the agent never crashes from a downstream failure
- **Idempotency**: Message IDs (ULIDs) prevent double-processing in the NestJS persist consumer

### Adding a New Core Tool

1. Create a file in `apps/fastapi/app/tools/core/` with your tool function
2. Define a `ToolDef` with name, description, JSON schema, and execute callback
3. Register it in `apps/fastapi/app/tools/core/__init__.py`
4. The tool is automatically available to the LLM on next request

### Adding a Dynamic Tool (via CRM)

1. Navigate to **Tools** page in the CRM
2. Define: name, description, JSON schema for parameters, endpoint URL, HTTP method
3. The tool appears in the agent's tool catalog after cache TTL (up to 5min) or on next cache invalidation
4. Test via the **Test** button (dry-run HTTP call)

---

## License

This project is provided as a reference architecture for AI-powered WhatsApp sales agents. See the repository license for details.

---

## Tags

`p1-infra-core` `p2-nestjs-backend` `p3-crm-frontend`
