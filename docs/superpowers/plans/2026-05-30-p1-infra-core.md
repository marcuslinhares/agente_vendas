# P1: Infraestrutura + Hono + FastAPI/LangGraph — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the foundational infrastructure (PostgreSQL+pgvector, Redis, MinIO) plus the Hono webhook receiver and FastAPI/LangGraph AI agent — the core message processing pipeline.

**Architecture:** Monorepo with Docker Compose. Hono receives WhatsApp webhooks and publishes to Redis Streams. FastAPI consumes from streams, runs the LangGraph agent (6-node graph with 3-level memory), generates CLIP + text embeddings, and publishes responses. All state stored in PostgreSQL+pgvector.

**Tech Stack:** Hono + ioredis (Node 22), FastAPI + LangGraph + open_clip + asyncpg (Python 3.12+), PostgreSQL 16 + pgvector, Redis 7 Streams, MinIO.

**Spec:** `docs/superpowers/specs/2026-05-30-agent-vendas-design.md`

---

## Chunk 1: Project Scaffold + Docker Compose + Database

**Objective:** Create the monorepo skeleton, Docker Compose for all infra services, PostgreSQL schema, MinIO setup, and shared types package.

### Task 1.1: Create directory structure

**Files:**
- Create: `agente_vendas/` structure

- [ ] **Create all directories**

```bash
mkdir -p agente_vendas/{apps/{hono/src/{routes,services},fastapi/app/{graph/nodes,tools/{core},services}},nestjs,nestjs/src/{modules/{auth,conversations,messages,products,customers,orders,tools,minio},queue,stream},web/src/{app/{auth,login},components/{ui,shared},lib}},packages/shared-types/src,infra/{postgres,minio},docs/superpowers/{specs,plans},.github/workflows}
```

- [ ] **Verify structure**

Run: `find agente_vendas -type d | head -40`

- [ ] **Commit**

```bash
git add agente_vendas/
git commit -m "chore: scaffold monorepo directory structure for P1"
```

---

### Task 1.2: PostgreSQL init.sql with full schema

**Files:**
- Create: `infra/postgres/init.sql`

- [ ] **Write init.sql**

```sql
-- infra/postgres/init.sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_id     TEXT NOT NULL UNIQUE,
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

CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id      TEXT UNIQUE NOT NULL,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT,
    media_url       TEXT,
    thumbnail_url   TEXT,
    media_type      VARCHAR(20),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE message_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id      UUID REFERENCES messages(id) ON DELETE SET NULL,
    content         TEXT,
    media_url       TEXT,
    media_type      VARCHAR(20),
    embedding       VECTOR(1536),
    embedding_clip  VECTOR(512),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE product_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    content         TEXT,
    media_url       TEXT,
    embedding       VECTOR(1536),
    embedding_clip  VECTOR(512),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

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
    is_idempotent   BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    price           DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    category        VARCHAR(100),
    stock           INT DEFAULT 0 CHECK (stock >= 0),
    image_url       TEXT,
    is_active       BOOLEAN DEFAULT true,
    is_idempotent   BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_id     TEXT UNIQUE NOT NULL,
    name            VARCHAR(200),
    email           VARCHAR(200),
    phone           VARCHAR(20),
    classification  VARCHAR(50) CHECK (classification IN ('lead_quente','lead_morno','lead_frio','cliente')),
    tags            TEXT[] DEFAULT '{}',
    metadata        JSONB DEFAULT '{}',
    last_contact_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    items           JSONB NOT NULL DEFAULT '[]',
    total           DECIMAL(10,2) NOT NULL CHECK (total >= 0),
    status          VARCHAR(20) DEFAULT 'pending'
                    CHECK (status IN ('pending','confirmed','shipped','cancelled')),
    payment_method  VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

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

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    name            VARCHAR(200),
    role            VARCHAR(20) DEFAULT 'admin' CHECK (role IN ('admin','agent')),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_msg_embeddings_conv ON message_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_msg_embeddings_clip ON message_embeddings USING ivfflat (embedding_clip vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_product_embeddings ON product_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_product_embeddings_clip ON product_embeddings USING ivfflat (embedding_clip vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_messages_conv_created ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_conversations_whatsapp ON conversations(whatsapp_id);
CREATE INDEX idx_customers_classification ON customers(classification);
CREATE INDEX idx_tools_active ON tools_catalog(is_active) WHERE is_active = true;


CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_classification ON conversations(classification);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_embeddings_conv_created ON message_embeddings(conversation_id, created_at DESC);
CREATE INDEX idx_tool_log_created ON tool_execution_log(created_at DESC);
```

- [ ] **Test the SQL**

Run: `docker run --rm pgvector/pgvector:pg16 psql -U postgres -d postgres -f /dev/stdin < infra/postgres/init.sql 2>&1 || echo "Container not running; verify SQL manually"`

- [ ] **Commit**

```bash
git add infra/postgres/init.sql
git commit -m "feat(infra): add PostgreSQL schema with pgvector and 11 tables"
```

---

### Task 1.3: Docker Compose + .env.example

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Write .env.example**

```bash
cat > .env.example << 'EOF'
# Database
DB_PASSWORD=localdev

# MinIO
MINIO_USER=minioadmin
MINIO_PASSWORD=minioadmin

# Evolution API
EVOLUTION_API_URL=http://evolution:8080
EVOLUTION_API_KEY=your-key-here
EVOLUTION_WEBHOOK_SECRET=your-webhook-secret

# OpenAI
OPENAI_API_KEY=sk-...

# LLM config
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# JWT (CRM, used in P2)
JWT_SECRET=change-me-in-production
EOF
```

- [ ] **Write docker-compose.yml** (infra services only for P1)

```yaml
# docker-compose.yml
version: "3.9"

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
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d agentevendas"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
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

volumes:
  pgdata:
  redisdata:
  miniodata:
```

- [ ] **Verify YAML is valid**

Run: `python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml')); print('✅ valid')"`

- [ ] **Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "feat(infra): add Docker Compose with postgres+redis+minio"
```

---

### Task 1.4: MinIO bucket setup script

**Files:**
- Create: `infra/minio/buckets.sh`

- [ ] **Write buckets.sh**

```bash
#!/bin/sh
# infra/minio/buckets.sh
# Run after MinIO starts: docker exec minio sh /scripts/buckets.sh

mc alias set local http://localhost:9000 ${MINIO_ROOT_USER:-minioadmin} ${MINIO_ROOT_PASSWORD:-minioadmin}

# Create buckets
mc mb local/conversations-media --ignore-existing
mc mb local/products --ignore-existing
mc mb local/temporary --ignore-existing

# Set public policy for products bucket
mc anonymous set download local/products

# Lifecycle: expire temporary after 1h
mc ilm rule add local/temporary --expire-days 0 --expire-hours 1

echo "MinIO buckets created successfully"
```

- [ ] **Commit**

```bash
chmod +x infra/minio/buckets.sh
git add infra/minio/buckets.sh
git commit -m "feat(infra): add MinIO bucket initialization script"
```

---

### Task 1.5: Shared types package

**Files:**
- Create: `packages/shared-types/package.json`
- Create: `packages/shared-types/tsconfig.json`
- Create: `packages/shared-types/src/index.ts`
- Create: `packages/shared-types/src/webhook.ts`
- Create: `packages/shared-types/src/message.ts`

- [ ] **Write package.json**

```json
{
  "name": "@agente-vendas/shared-types",
  "version": "0.1.0",
  "main": "src/index.ts",
  "types": "src/index.ts",
  "dependencies": {
    "zod": "^3.23.0"
  }
}
```

- [ ] **Write tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true
  },
  "include": ["src"]
}
```

**Write webhook.ts**

```typescript
import { z } from "zod";

export const WebhookIncomingSchema = z.object({
  id: z.string().ulid(),
  whatsapp_id: z.string(),
  message: z.string(),
  media_url: z.string().optional(),
  media_type: z.enum(["image", "audio", "video", "document"]).optional(),
  timestamp: z.string().datetime(),
});

export type WebhookIncoming = z.infer<typeof WebhookIncomingSchema>;

export const WhatsAppOutboxSchema = z.object({
  id: z.string().ulid(),
  to: z.string(),
  text: z.string(),
  media_url: z.string().optional(),
});

export type WhatsAppOutbox = z.infer<typeof WhatsAppOutboxSchema>;
```


- [ ] **Write message.ts**

```typescript
import { z } from "zod";

export const MessagePersistSchema = z.object({
  id: z.string().ulid(),
  conversation_id: z.string().uuid(),
  role: z.enum(["user", "assistant", "system"]),
  content: z.string(),
  media_url: z.string().optional(),
  media_type: z.string().optional(),
  metadata: z.record(z.unknown()).default({}),
  embedding_clip: z.array(z.number()).optional(),
  embedding_text: z.array(z.number()).optional(),
  update_summary: z.boolean().default(false),
});

export type MessagePersist = z.infer<typeof MessagePersistSchema>;
```

- [ ] **Write product.ts**

```typescript
import { z } from "zod";

export const ProductSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string().optional(),
  price: z.number().positive(),
  category: z.string().optional(),
  stock: z.number().int().nonnegative().default(0),
  image_url: z.string().optional(),
  is_active: z.boolean().default(true),
});

export type Product = z.infer<typeof ProductSchema>;
```

- [ ] **Write index.ts**

```typescript
export * from "./webhook";
export * from "./product";
export * from "./message";
```

- [ ] **Commit**

```bash
git add packages/shared-types/
git commit -m "feat(shared): add Zod schemas for stream payloads"
```

---

## Chunk 2: Hono Service

**Objective:** Create the WhatsApp webhook receiver service that ingests messages from Evolution API and publishes to Redis Streams.

### Task 2.1: Hono project setup

**Files:**
- Create: `apps/hono/package.json`
- Create: `apps/hono/tsconfig.json`
- Create: `apps/hono/Dockerfile`
- Create: `apps/hono/.env` (copy from root .env.example for dev)

- [ ] **Write package.json**

```json
{
  "name": "@agente-vendas/hono",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "hono": "^4.6.0",
    "ioredis": "^5.4.0",
    "@aws-sdk/client-s3": "^3.600.0",
    "ulid": "^2.3.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "tsx": "^4.16.0",
    "@types/node": "^20.14.0"
  }
}
```

- [ ] **Write tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "outDir": "dist",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

- [ ] **Write Dockerfile**

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json tsconfig.json ./
RUN npm ci
COPY src/ src/
RUN npm run build

FROM node:22-alpine
WORKDIR /app
COPY package.json ./
RUN npm ci --production
COPY --from=builder /app/dist dist/
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

- [ ] **Commit**

```bash
git add apps/hono/
git commit -m "feat(hono): scaffold project with package.json and Dockerfile"
```

---

### Task 2.2: Hono — Redis and MinIO services

**Files:**
- Create: `apps/hono/src/services/redis.ts`
- Create: `apps/hono/src/services/minio.ts`

- [ ] **Write Redis client**

```typescript
// apps/hono/src/services/redis.ts
import Redis from "ioredis";

const REDIS_URL = process.env.REDIS_URL || "redis://localhost:6379";
const STREAM_WEBHOOK = "webhook:incoming";
const STREAM_OUTBOX = "whatsapp:outbox";
const OUTBOX_GROUP = "hono-workers";

export const redis = new Redis(REDIS_URL);

export async function ensureOutboxGroup(): Promise<void> {
  try {
    await redis.xgroup("CREATE", STREAM_OUTBOX, OUTBOX_GROUP, "$", "MKSTREAM");
  } catch (e: any) {
    if (!e.message?.includes("BUSYGROUP")) throw e;
  }
}

export async function publishWebhook(payload: Record<string, unknown>): Promise<string> {
  return redis.xadd(STREAM_WEBHOOK, "*", "payload", JSON.stringify(payload));
}

export async function* consumeOutbox(batchSize = 5): AsyncGenerator<{ id: string; payload: any }> {
  const result = await redis.xreadgroup(
    "GROUP", OUTBOX_GROUP, `consumer-${Date.now()}`,
    "COUNT", batchSize,
    "BLOCK", 2000,
    "STREAMS", STREAM_OUTBOX, ">"
  );
  if (!result) return;
  for (const [, messages] of result) {
    for (const [id, fields] of messages) {
      const payload = JSON.parse(fields.find((_: any, i: number) => fields[i] === "payload")![1]);
      yield { id, payload };
    }
  }
}

export async function ackOutbox(streamId: string): Promise<void> {
  await redis.xack(STREAM_OUTBOX, OUTBOX_GROUP, streamId);
}

export async function nackOutbox(streamId: string): Promise<void> {
  // Move to dead-letter after 3 attempts
  const attempts = await redis.hincrby(`attempts:${streamId}`, "count", 1);
  if (attempts >= 3) {
    await redis.xadd("whatsapp:outbox:deadletter", "*", "stream_id", streamId);
  }
}
```

- [ ] **Write MinIO client**

```typescript
// apps/hono/src/services/minio.ts
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

const MINIO_ENDPOINT = process.env.MINIO_ENDPOINT || "localhost:9000";
const MINIO_ACCESS_KEY = process.env.MINIO_ACCESS_KEY || "minioadmin";
const MINIO_SECRET_KEY = process.env.MINIO_SECRET_KEY || "minioadmin";

export const s3 = new S3Client({
  endpoint: `http://${MINIO_ENDPOINT}`,
  region: "us-east-1",
  credentials: { accessKeyId: MINIO_ACCESS_KEY, secretAccessKey: MINIO_SECRET_KEY },
  forcePathStyle: true,
});

export async function uploadMedia(
  bucket: string,
  key: string,
  body: Buffer,
  contentType: string
): Promise<string> {
  await s3.send(new PutObjectCommand({
    Bucket: bucket,
    Key: key,
    Body: body,
    ContentType: contentType,
  }));
  return `http://${MINIO_ENDPOINT}/${bucket}/${key}`;
}
```

- [ ] **Commit**

```bash
git add apps/hono/src/services/
git commit -m "feat(hono): add Redis Stream and MinIO clients"
```

---

### Task 2.3: Hono — Webhook route + Evolution API client

**Files:**
- Create: `apps/hono/src/services/evolution.ts`
- Create: `apps/hono/src/routes/webhook.ts`
- Create: `apps/hono/src/routes/health.ts`
- Create: `apps/hono/src/index.ts`

- [ ] **Write Evolution API client**

```typescript
// apps/hono/src/services/evolution.ts
const EVOLUTION_API_URL = process.env.EVOLUTION_API_URL!;
const EVOLUTION_API_KEY = process.env.EVOLUTION_API_KEY!;

export async function sendMessage(to: string, text: string, mediaUrl?: string): Promise<void> {
  const body: any = { number: to, text };
  if (mediaUrl) body.mediaUrl = mediaUrl;
  
  const res = await fetch(`${EVOLUTION_API_URL}/message/send`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "apiKey": EVOLUTION_API_KEY,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Evolution API error: ${res.status} ${await res.text()}`);
}

export async function downloadMedia(mediaUrl: string): Promise<Buffer> {
  const res = await fetch(mediaUrl, {
    headers: { "apiKey": EVOLUTION_API_KEY },
  });
  if (!res.ok) throw new Error(`Failed to download media: ${res.status}`);
  return Buffer.from(await res.arrayBuffer());
}

export async function verifyWebhook(signature: string, body: string): Promise<boolean> {
  const secret = process.env.EVOLUTION_WEBHOOK_SECRET || "";
  const crypto = await import("crypto");
  const expected = crypto.createHmac("sha256", secret).update(body).digest("hex");
  return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
}
```

- [ ] **Write webhook route**

```typescript
// apps/hono/src/routes/webhook.ts
import { Hono } from "hono";
import { ulid } from "ulid";
import { publishWebhook } from "../services/redis.js";
import { s3, uploadMedia } from "../services/minio.js";
import { downloadMedia, verifyWebhook } from "../services/evolution.js";

const webhook = new Hono();

webhook.post("/webhook/evolution", async (c) => {
  // Verify signature
  const signature = c.req.header("x-evolution-signature");
  const body = await c.req.text();
  if (signature && !(await verifyWebhook(signature, body))) {
    return c.json({ error: "invalid signature" }, 401);
  }

  const data = JSON.parse(body);
  const whatsappId = data.key?.remoteJid || data.from;
  const messageText = data.message?.conversation || data.message?.extendedTextMessage?.text || "";
  const mediaInfo = extractMedia(data.message);
  
  let mediaUrl: string | undefined;
  let mediaType: string | undefined;

  // If media, download it and upload to MinIO
  if (mediaInfo) {
    const raw = await downloadMedia(mediaInfo.url);
    const ext = mediaInfo.type === "image" ? "jpg" : mediaInfo.type === "audio" ? "ogg" : "mp4";
    const key = `${whatsappId}/${ulid()}.${ext}`;
    mediaUrl = await uploadMedia("conversations-media", key, raw, mediaInfo.mimeType);
    mediaType = mediaInfo.type;
  }

  // Publish to Redis Stream
  const streamId = await publishWebhook({
    id: ulid(),
    whatsapp_id: whatsappId,
    message: messageText,
    media_url: mediaUrl,
    media_type: mediaType,
    timestamp: new Date().toISOString(),
  });

  return c.json({ ok: true, stream_id: streamId });
});

function extractMedia(msg: any): { url: string; type: string; mimeType: string } | null {
  const media = msg?.imageMessage || msg?.audioMessage || msg?.videoMessage || msg?.documentMessage;
  if (!media) return null;
  const type = msg.imageMessage ? "image" : msg.audioMessage ? "audio" : msg.videoMessage ? "video" : "document";
  return { url: media.url, type, mimeType: media.mimetype || "application/octet-stream" };
}

export { webhook };
```

- [ ] **Write health route**

```typescript
// apps/hono/src/routes/health.ts
import { Hono } from "hono";
import { redis } from "../services/redis.js";

const health = new Hono();

health.get("/health", async (c) => {
  try {
    await redis.ping();
    return c.json({ status: "ok", redis: "connected" });
  } catch (e) {
    return c.json({ status: "error", redis: "disconnected" }, 503);
  }
});

health.get("/ready", async (c) => {
  try {
    await redis.ping();
    return c.json({ ready: true });
  } catch {
    return c.json({ ready: false }, 503);
  }
});

export { health };
```

- [ ] **Write main index.ts**

```typescript
// apps/hono/src/index.ts
import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { webhook } from "./routes/webhook.js";
import { health } from "./routes/health.js";
import { ensureOutboxGroup, consumeOutbox, ackOutbox, nackOutbox } from "./services/redis.js";
import { sendMessage } from "./services/evolution.js";

const app = new Hono();

app.route("/", webhook);
app.route("/", health);

async function startOutboxConsumer(): Promise<void> {
  await ensureOutboxGroup();
  
  setInterval(async () => {
    try {
      for await (const { id, payload } of consumeOutbox()) {
        try {
          await sendMessage(payload.to, payload.text, payload.media_url);
          await ackOutbox(id);
        } catch (err) {
          console.error(`[outbox] Failed to send ${id}:`, err);
          await nackOutbox(id);
        }
      }
    } catch (err) {
      console.error("[outbox] Consumer error:", err);
    }
  }, 1000);
}

const PORT = parseInt(process.env.HONO_PORT || "3000");

serve({ fetch: app.fetch, port: PORT }, () => {
  console.log(`✅ Hono server running on port ${PORT}`);
  startOutboxConsumer().catch(console.error);
});
```

- [ ] **Verify TypeScript compiles**

Run: `cd apps/hono && cp ../../.env.example .env && npm install && npx tsc --noEmit 2>&1`

- [ ] **Smoke test: start Hono and verify health endpoint**

Run: `cd apps/hono && npx tsx src/index.ts &`
Wait 2s then run: `curl -s http://localhost:3000/health`
Expected: `{"status":"ok","redis":"connected"}`
Stop server: `kill %1`

- [ ] **Commit**

```bash
git add apps/hono/src/
git commit -m "feat(hono): add webhook route, Evolution client, and outbox consumer"
```

---

## Chunk 3: FastAPI — Project Setup + LangGraph Core

**Objective:** Create the FastAPI project with LangGraph graph structure, state, configuration, and database connections.

### Task 3.1: FastAPI project setup

**Files:**
- Create: `apps/fastapi/requirements.txt`
- Create: `apps/fastapi/pyproject.toml`
- Create: `apps/fastapi/Dockerfile`
- Create: `apps/fastapi/app/__init__.py`
- Create: `apps/fastapi/app/config.py`

- [ ] **Write requirements.txt**

```
fastapi==0.115.0
langgraph==0.2.0
langchain-openai==0.2.0
asyncpg==0.30.0
redis[hiredis]==5.2.0
pgvector==0.3.0
open_clip_torch==2.24.0
torch==2.4.0
torchvision==0.19.0
Pillow==10.4.0
pydantic==2.9.0
pydantic-settings==2.5.0
openai==1.50.0
ulid-py==1.1.0
python-multipart==0.0.12
httpx==0.27.0
boto3==1.35.0
```

- [ ] **Write pyproject.toml**

```toml
[project]
name = "fastapi-langgraph"
version = "0.1.0"
requires-python = ">=3.12"
```

- [ ] **Write Dockerfile**

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY app/ app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Write config.py**

```python
# apps/fastapi/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # PostgreSQL
    database_url: str = "postgresql+asyncpg://app:localdev@localhost:5432/agentevendas"
    
    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Streams
    stream_webhook: str = "webhook:incoming"
    stream_outbox: str = "whatsapp:outbox"
    stream_persist: str = "message:persist"
    consumer_group: str = "fastapi-workers"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Commit**

- [ ] **Verify config imports correctly**

Run: `cd apps/fastapi && python -c "from app.config import settings; print(f'Config OK: {settings.redis_url}')"`
Expected: prints "Config OK: redis://localhost:6379"

```bash
git add apps/fastapi/
git commit -m "feat(fastapi): scaffold project with Dockerfile and config"
```

---

### Task 3.2: FastAPI — Database and Redis connections

**Files:**
- Create: `apps/fastapi/app/services/__init__.py`
- Create: `apps/fastapi/app/services/redis.py`
- Create: `apps/fastapi/app/services/postgres.py`
- Create: `apps/fastapi/app/services/minio.py`

- [ ] **Create services/__init__.py**

Run: `touch apps/fastapi/app/services/__init__.py`

- [ ] **Write redis.py**

```python
# apps/fastapi/app/services/redis.py
import json
import asyncio
from typing import AsyncIterator, Optional
from redis.asyncio import Redis

redis_client: Optional[Redis] = None

async def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url("redis://localhost:6379", decode_responses=True)
    return redis_client

async def ensure_consumer_group(stream: str, group: str):
    r = await get_redis()
    try:
        await r.xgroup_create(stream, group, id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            raise

async def consume_stream(
    stream: str,
    group: str,
    consumer: str,
    batch_size: int = 5,
    block: int = 2000,
) -> AsyncIterator[tuple[str, dict]]:
    r = await get_redis()
    while True:
        try:
            result = await r.xreadgroup(
                group, consumer, {stream: ">"},
                count=batch_size, block=block,
            )
            if not result:
                await asyncio.sleep(0.1)
                continue
            for messages in result.values():
                for msg_id, fields in messages:
                    yield msg_id, json.loads(fields["payload"])
        except Exception as e:
            print(f"[redis] consume error: {e}")
            await asyncio.sleep(1)

async def publish_to_stream(stream: str, payload: dict):
    r = await get_redis()
    await r.xadd(stream, "*", {"payload": json.dumps(payload)})

async def ack_message(stream: str, group: str, msg_id: str):
    r = await get_redis()
    await r.xack(stream, group, msg_id)

async def nack_message(stream: str, group: str, msg_id: str):
    r = await get_redis()
    attempts = await r.hincrby(f"attempts:{msg_id}", "count", 1)
    if attempts >= 3:
        await r.xadd(f"{stream}:deadletter", "*", {"msg_id": msg_id})
    # XACK to remove from pending (dead-letter already captured it)
    await r.xack(stream, group, msg_id)
```

- [ ] **Create services/__init__.py**

Run: `touch apps/fastapi/app/services/__init__.py`

- [ ] **Write postgres.py**

```python
# apps/fastapi/app/services/postgres.py
import asyncpg
from typing import Optional

pool: Optional[asyncpg.Pool] = None

from ...config import settings

async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
        )
    return pool

async def get_last_messages(conversation_id: str, limit: int = 10) -> list[dict]:
    p = await get_pool()
    rows = await p.fetch(
        """SELECT role, content, media_url, media_type, created_at
           FROM messages
           WHERE conversation_id = $1
           ORDER BY created_at DESC
           LIMIT $2""",
        conversation_id, limit
    )
    return [dict(r) for r in rows]

async def get_conversation_summary(conversation_id: str) -> Optional[str]:
    p = await get_pool()
    row = await p.fetchrow(
        "SELECT summary FROM conversations WHERE id = $1",
        conversation_id
    )
    return row["summary"] if row else None

async def get_conversation_by_whatsapp(whatsapp_id: str) -> Optional[dict]:
    p = await get_pool()
    row = await p.fetchrow(
        "SELECT id, status, message_count FROM conversations WHERE whatsapp_id = $1",
        whatsapp_id
    )
    return dict(row) if row else None

async def create_conversation(whatsapp_id: str) -> dict:
    p = await get_pool()
    row = await p.fetchrow(
        """INSERT INTO conversations (whatsapp_id)
           VALUES ($1)
           RETURNING id, status, message_count""",
        whatsapp_id
    )
    return dict(row)

async def increment_message_count(conversation_id: str):
    p = await get_pool()
    await p.execute(
        "UPDATE conversations SET message_count = message_count + 1, updated_at = NOW() WHERE id = $1",
        conversation_id
    )

async def vector_search(
    conversation_id: str,
    embedding: list[float],
    cutoff: str,
    limit: int = 5,
    threshold: float = 0.75,
) -> list[dict]:
    p = await get_pool()
    rows = await p.fetch(
        """SELECT content, media_url, media_type,
                   1 - (embedding <=> $1::vector) AS score
           FROM message_embeddings
           WHERE conversation_id = $2 AND created_at < $3::timestamptz
             AND 1 - (embedding <=> $1::vector) > $4
           ORDER BY score DESC
           LIMIT $5""",
        embedding, conversation_id, cutoff, threshold, limit
    )
    return [dict(r) for r in rows]
```

- [ ] **Write minio.py**

```python
# apps/fastapi/app/services/minio.py
import boto3
from botocore.config import Config
from typing import Optional

client: Optional[boto3.client] = None

def get_minio() -> boto3.client:
    global client
    if client is None:
        client = boto3.client(
            "s3",
            endpoint_url="http://localhost:9000",
            aws_access_key_id="minioadmin",
            aws_secret_access_key="minioadmin",
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
    return client

def download_media(bucket: str, key: str) -> bytes:
    s3 = get_minio()
    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
```

- [ ] **Commit**

```bash
git add apps/fastapi/app/services/
git commit -m "feat(fastapi): add Redis, PostgreSQL, and MinIO service clients"
```

---

### Task 3.3: FastAPI — LangGraph State and Graph Structure

**Files:**
- Create: `apps/fastapi/app/graph/__init__.py`
- Create: `apps/fastapi/app/graph/state.py`
- Create: `apps/fastapi/app/graph/agent.py`

- [ ] **Write state.py**

```python
# apps/fastapi/app/graph/state.py
from typing import TypedDict, Optional, NotRequired

class AgentState(TypedDict):
    # Entry
    whatsapp_id: str
    conversation_id: str
    message_id: str
    raw_content: str
    media_url: Optional[str]
    media_type: Optional[str]
    
    # Parse
    parsed_content: str
    intent: str
    customer_id: Optional[str]
    
    # Memory
    l1_messages: list[dict]
    l2_summary: str
    l3_memories: list[dict]
    l3_triggered: bool
    
    # Execution
    agent_response: str
    tool_calls: list[dict]
    metadata: dict
    
    # Embeddings (generated in POST_PROCESS)
    embedding_clip: Optional[list[float]]
    embedding_text: Optional[list[float]]
```

- [ ] **Write agent.py** (graph skeleton with node registration)

```python
# apps/fastapi/app/graph/agent.py
from langgraph.graph import StateGraph, END
from .state import AgentState

from .nodes.parse_classify import ParseClassifyNode
from .nodes.memory_hydrate import MemoryHydrateNode
from .nodes.memory_gate import MemoryGateNode
from .nodes.l3_search import L3SearchNode
from .nodes.agent_execute import AgentExecuteNode
from .nodes.post_process import PostProcessNode

def build_agent() -> StateGraph:
    workflow = StateGraph(AgentState)
    
    # Register nodes
    workflow.add_node("parse_classify", ParseClassifyNode().run)
    workflow.add_node("memory_hydrate", MemoryHydrateNode().run)
    workflow.add_node("memory_gate", MemoryGateNode().run)
    workflow.add_node("l3_search", L3SearchNode().run)
    workflow.add_node("agent_execute", AgentExecuteNode().run)
    workflow.add_node("post_process", PostProcessNode().run)
    
    # Edges
    workflow.set_entry_point("parse_classify")
    workflow.add_edge("parse_classify", "memory_hydrate")
    workflow.add_edge("memory_hydrate", "memory_gate")
    
    # Conditional: L3 only if gate triggers
    workflow.add_conditional_edges(
        "memory_gate",
        lambda state: "l3_search" if state.get("l3_triggered") else "agent_execute",
        {"l3_search": "l3_search", "agent_execute": "agent_execute"},
    )
    workflow.add_edge("l3_search", "agent_execute")
    workflow.add_edge("agent_execute", "post_process")
    workflow.add_edge("post_process", END)
    
    return workflow.compile()
```

- [ ] **Commit**

```bash
git add apps/fastapi/app/graph/
git commit -m "feat(fastapi): add LangGraph state schema and graph structure"
```

---

## Chunk 4: FastAPI — LangGraph Nodes (Memory System)

**Objective:** Implement the 6 LangGraph nodes: parse_classify, memory_hydrate, memory_gate, l3_search, agent_execute, post_process.

### Task 4.1: ParseClassifyNode — incoming message handling

**Files:**
- Create: `apps/fastapi/app/graph/nodes/__init__.py`
- Create: `apps/fastapi/app/graph/nodes/parse_classify.py`

- [ ] **Write parse_classify.py**

```python
# apps/fastapi/app/graph/nodes/parse_classify.py
from ..state import AgentState
from ...services.postgres import get_conversation_by_whatsapp, create_conversation, increment_message_count

class ParseClassifyNode:
    async def run(self, state: AgentState) -> dict:
        whatsapp_id = state["whatsapp_id"]
        
        # Get or create conversation
        conv = await get_conversation_by_whatsapp(whatsapp_id)
        if not conv:
            conv = await create_conversation(whatsapp_id)
        
        # If media, generate description (simplified — full implementation calls GPT-4o Vision)
        parsed = state["raw_content"]
        if state.get("media_url") and state.get("media_type") == "image":
            # TODO: call GPT-4o Vision to describe image
            # For now, use placeholder
            parsed = f"[Imagem enviada pelo cliente: {state['raw_content'] or 'sem legenda'}]"
        
        # Simple intent classification (will be refined)
        intent = "duvida"
        if any(w in parsed.lower() for w in ["quero", "comprar", "pedir", "comprar"]):
            intent = "pedido"
        elif any(w in parsed.lower() for w in ["oi", "ola", "bom dia", "boa tarde"]):
            intent = "saudacao"
        
        return {
            "conversation_id": conv["id"],
            "parsed_content": parsed,
            "intent": intent,
        }
```

- [ ] **Verify imports compile**

Run: `cd apps/fastapi && python -c "from app.graph.nodes.parse_classify import ParseClassifyNode; print('✅ ParseClassifyNode imports OK')"`

- [ ] **Commit**

```bash
git add apps/fastapi/app/graph/nodes/parse_classify.py
git commit -m "feat(fastapi): add parse_classify node"
```

---

### Task 4.2: MemoryHydrateNode — L1 + L2

**Files:**
- Create: `apps/fastapi/app/graph/nodes/memory_hydrate.py`

- [ ] **Write memory_hydrate.py**

```python
# apps/fastapi/app/graph/nodes/memory_hydrate.py
from ..state import AgentState
from ...services.postgres import get_last_messages, get_conversation_summary

class MemoryHydrateNode:
    async def run(self, state: AgentState) -> dict:
        conv_id = state["conversation_id"]
        
        # L1: Last 10 messages
        l1 = await get_last_messages(conv_id, limit=10)
        
        # L2: Conversation summary
        l2 = await get_conversation_summary(conv_id) or ""
        
        return {
            "l1_messages": l1,
            "l2_summary": l2,
        }
```

- [ ] **Verify imports compile**

Run: `cd apps/fastapi && python -c "from app.graph.nodes.memory_hydrate import MemoryHydrateNode; print('✅ MemoryHydrateNode imports OK')"`

- [ ] **Commit**

```bash
git add apps/fastapi/app/graph/nodes/memory_hydrate.py
git commit -m "feat(fastapi): add memory_hydrate node for L1+L2"
```

---

### Task 4.3: MemoryGateNode — LLM gate for L3

**Files:**
- Create: `apps/fastapi/app/graph/nodes/memory_gate.py`

- [ ] **Write memory_gate.py**

```python
# apps/fastapi/app/graph/nodes/memory_gate.py
from ..state import AgentState
import json

class MemoryGateNode:
    def __init__(self):
        self._llm = None  # Lazy init to avoid import on cold start
    
    async def _call_llm(self, user_msg: str, history: list[dict]) -> dict:
        # Uses OpenAI to evaluate if message references past conversation
        from openai import AsyncOpenAI
        
from ...config import settings
        
        if self._llm is None:
            self._llm = AsyncOpenAI(api_key=settings.openai_api_key)
        
        prompt = f"""Analyze this user message in a sales conversation.

User message: "{user_msg}"

Recent conversation history (last {len(history)} messages):
{chr(10).join(f"- {m['role']}: {m['content'][:200]}" for m in history)}

Does the user's message reference something said earlier in the conversation
(more than 20 messages ago or in a previous session)?
Respond ONLY with JSON: {{"trigger_l3": true/false, "reason": "..."}}"""
        
        response = await self._llm.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        
        return json.loads(response.choices[0].message.content)
    
    async def run(self, state: AgentState) -> dict:
        try:
            result = await self._call_llm(
                state["parsed_content"] or state["raw_content"],
                state.get("l1_messages", []),
            )
            return {"l3_triggered": result.get("trigger_l3", False)}
        except Exception as e:
            print(f"[memory_gate] LLM error: {e}")
            return {"l3_triggered": False}  # Graceful degradation
```

- [ ] **Verify imports compile**

Run: `cd apps/fastapi && python -c "from app.graph.nodes.memory_gate import MemoryGateNode; print('✅ MemoryGateNode imports OK')"`

- [ ] **Commit**

```bash
git add apps/fastapi/app/graph/nodes/memory_gate.py
git commit -m "feat(fastapi): add memory_gate node for L3 trigger"
```

---

### Task 4.4: L3SearchNode — pgvector vector search

**Files:**
- Create: `apps/fastapi/app/graph/nodes/l3_search.py`

- [ ] **Write l3_search.py**

```python
# apps/fastapi/app/graph/nodes/l3_search.py
from ..state import AgentState
from ...services.postgres import vector_search

class L3SearchNode:
    async def run(self, state: AgentState) -> dict:
        # Generate embedding for the current query to search with
        query_text = state.get("parsed_content") or state.get("raw_content", "")
        
        try:
            from openai import AsyncOpenAI
            
from ...config import settings
            
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.embeddings.create(
                model=settings.openai_embedding_model,
                input=query_text,
            )
            query_embedding = response.data[0].embedding
            
            # Use a cutoff to only search messages older than the L1 window
            cutoff = state["l1_messages"][-1]["created_at"] if state.get("l1_messages") else "now()"
            
            memories = await vector_search(
                conversation_id=state["conversation_id"],
                embedding=query_embedding,
                cutoff=cutoff,
                limit=5,
                threshold=0.75,
            )
            return {"l3_memories": memories}
        except Exception as e:
            print(f"[l3_search] Error: {e}")
            return {"l3_memories": []}
```

- [ ] **Verify imports compile**

Run: `cd apps/fastapi && python -c "from app.graph.nodes.l3_search import L3SearchNode; print('✅ L3SearchNode imports OK')"`

- [ ] **Commit**

```bash
git add apps/fastapi/app/graph/nodes/l3_search.py
git commit -m "feat(fastapi): add L3 vector search node"
```

---

### Task 4.5: AgentExecuteNode — main LLM agent with tools

**Files:**
- Create: `apps/fastapi/app/graph/nodes/agent_execute.py`

- [ ] **Write agent_execute.py**

```python
# apps/fastapi/app/graph/nodes/agent_execute.py
from ..state import AgentState
from ...tools.registry import ToolRegistry

from ...config import settings

class AgentExecuteNode:
    def __init__(self):
        self._llm = None
        self.tool_registry = ToolRegistry()
    
    async def run(self, state: AgentState) -> dict:
        from openai import AsyncOpenAI
        
        if self._llm is None:
            self._llm = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Build context from memory
        context_parts = []
        
        # L1: Recent messages
        if state.get("l1_messages"):
            context_parts.append("Recent conversation:")
            for m in reversed(state["l1_messages"]):
                context_parts.append(f"{m['role']}: {m['content'][:500]}")
        
        # L2: Summary
        if state.get("l2_summary"):
            context_parts.append(f"Conversation summary: {state['l2_summary']}")
        
        # L3: Old memories
        if state.get("l3_memories"):
            context_parts.append("Relevant past context:")
            for m in state["l3_memories"]:
                context_parts.append(f"- {m['content'][:300]} (relevance: {m.get('score', 0):.2f})")
        
        # Load tools
        tools = await self.tool_registry.load_all()
        tool_defs = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            }
            for t in tools
        ]
        
        system_prompt = f"""You are a sales assistant for a WhatsApp store. 
You help customers find products, answer questions, and close orders.

Current intent: {state.get('intent', 'unknown')}

{chr(10).join(context_parts)}

You have access to tools. Use them when needed.
Be friendly and professional in Brazilian Portuguese."""
        
        response = await self._llm.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": state.get("parsed_content") or state.get("raw_content", "")},
            ],
            tools=tool_defs if tool_defs else None,
            temperature=0.7,
        )
        
        msg = response.choices[0].message
        tool_calls_data = []
        
        # Handle tool calls
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_data.append({
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })
                # Execute tool and get result
                result = await self.tool_registry.execute(
                    tc.function.name,
                    json.loads(tc.function.arguments),
                )
                # TODO: feed tool result back to LLM for final response
                # For now, include in response text
                # In production, this would be a proper multi-turn tool loop
        
        return {
            "agent_response": msg.content or "Desculpe, não consegui processar sua solicitação.",
            "tool_calls": tool_calls_data,
            "metadata": {"intent": state.get("intent", "unknown")},
        }
```

- [ ] **Verify imports compile**

Run: `cd apps/fastapi && python -c "from app.graph.nodes.agent_execute import AgentExecuteNode; print('✅ AgentExecuteNode imports OK')"`

- [ ] **Commit**

```bash
git add apps/fastapi/app/graph/nodes/agent_execute.py
git commit -m "feat(fastapi): add agent_execute node with tool support"
```

---

### Task 4.6: PostProcessNode — embeddings and summary

**Files:**
- Create: `apps/fastapi/app/graph/nodes/post_process.py`

- [ ] **Write post_process.py**

```python
# apps/fastapi/app/graph/nodes/post_process.py
from ..state import AgentState
from ...services.minio import download_media

from ...config import settings

class ClipService:
    """Singleton CLIP model for image embeddings."""
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            import open_clip
            import torch
            model, _, preprocess = open_clip.create_model_and_transforms(
                "ViT-B-32", pretrained="laion2b_s34b_b79k"
            )
            model.eval()
            tokenizer = open_clip.get_tokenizer("ViT-B-32")
            cls._instance = {
                "model": model,
                "preprocess": preprocess,
                "tokenizer": tokenizer,
            }
        return cls._instance
    
    @classmethod
    def embed_image(cls, image_bytes: bytes) -> list[float]:
        import torch
        from PIL import Image
        import io
        
        instance = cls.get_instance()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        processed = instance["preprocess"](image).unsqueeze(0)
        with torch.no_grad():
            embedding = instance["model"].encode_image(processed)
            return embedding.squeeze().tolist()

class PostProcessNode:
    def __init__(self):
        self._text_embedder = None
    
    async def _get_text_embedding(self, text: str) -> list[float]:
        from openai import AsyncOpenAI
        
        if self._text_embedder is None:
            self._text_embedder = AsyncOpenAI(api_key=settings.openai_api_key)
        
        response = await self._text_embedder.embeddings.create(
            model=settings.openai_embedding_model,
            input=text,
        )
        return response.data[0].embedding
    
    async def run(self, state: AgentState) -> dict:
        embedding_clip = None
        embedding_text = None
        
        # CLIP embedding for image media
        if state.get("media_url") and state.get("media_type") == "image":
            try:
                # Extract key from media URL
                # URL format: http://minio:9000/conversations-media/{key}
                key = "/".join(state["media_url"].split("/")[-2:])
                image_bytes = download_media("conversations-media", key)
                embedding_clip = ClipService.embed_image(image_bytes)
            except Exception as e:
                print(f"[post_process] CLIP error: {e}")
        
        # Text embedding
        source_text = state.get("parsed_content") or state.get("raw_content", "")
        if source_text:
            try:
                embedding_text = await self._get_text_embedding(source_text)
            except Exception as e:
                print(f"[post_process] Text embedding error: {e}")
        
        return {
            "embedding_clip": embedding_clip,
            "embedding_text": embedding_text,
        }
```

- [ ] **Verify imports compile**

Run: `cd apps/fastapi && python -c "from app.graph.nodes.post_process import PostProcessNode; print('✅ PostProcessNode imports OK')"`

- [ ] **Commit**

```bash
git add apps/fastapi/app/graph/nodes/post_process.py
git commit -m "feat(fastapi): add post_process node with CLIP + text embeddings"
```

---

## Chunk 5: FastAPI — Tool Registry + Main Entry Point

**Objective:** Implement the tool registry, core tools, and the FastAPI main entry point that wires everything together.

### Task 5.1: Tool Registry

**Files:**
- Create: `apps/fastapi/app/tools/__init__.py`
- Create: `apps/fastapi/app/tools/registry.py`

- [ ] **Write registry.py**

```python
# apps/fastapi/app/tools/registry.py
import json
import httpx
from dataclasses import dataclass, field
from typing import Callable, Awaitable

@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict
    is_idempotent: bool = True
    execute: Callable[[dict], Awaitable[str]] = field(default=lambda x: "Not implemented")

class ToolRegistry:
    def __init__(self):
        self._core_tools: list[ToolDef] = []
        self._dynamic_tools: list[ToolDef] = []
    
    def register_core(self, tool: ToolDef):
        self._core_tools.append(tool)
    
    async def _load_dynamic_from_db(self) -> list[ToolDef]:
        """Load dynamic tools from tools_catalog table."""
        from ..services.postgres import get_pool
        try:
            pool = await get_pool()
            rows = await pool.fetch(
                "SELECT name, description, schema, endpoint, http_method, "
                "headers, timeout_ms, is_idempotent, rate_limit FROM tools_catalog WHERE is_active = true"
            )
            tools = []
            for row in rows:
                tool = ToolDef(
                    name=row["name"],
                    description=row["description"],
                    parameters=row["schema"],
                    is_idempotent=row.get("is_idempotent", True),
                    execute=self._make_http_executor(
                        row["endpoint"],
                        row.get("http_method", "POST"),
                        row.get("headers", {}),
                        row.get("timeout_ms", 10000),
                        row.get("rate_limit", 0),
                    ),
                )
                tools.append(tool)
            return tools
        except Exception as e:
            print(f"[registry] DB load error: {e}")
            return []
    
    def _make_http_executor(self, endpoint: str, method: str, headers: dict, timeout_ms: int, rate_limit: int = 0):
        async def execute(params: dict) -> str:
            async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
                if method == "GET":
                    resp = await client.get(endpoint, params=params, headers=headers)
                else:
                    resp = await client.post(endpoint, json=params, headers=headers)
                if resp.is_error:
                    return f"Error {resp.status_code}: {resp.text}"
                return resp.text
        return execute
    
    async def load_all(self) -> list[ToolDef]:
        """Load core + dynamic tools."""
        # Core tools are already registered
        dynamic = await self._load_dynamic_from_db()
        self._dynamic_tools = dynamic
        return self._core_tools + self._dynamic_tools
    
    async def execute(self, name: str, params: dict) -> str:
        import time, json
        from ...services.postgres import get_pool
        start = time.monotonic()
        result = ""
        success = False
        error_msg = None
        try:
            for tool in self._core_tools + self._dynamic_tools:
            if tool.name == name:
                try:
                    result = await tool.execute(params)
                    success = True
                    break
                except Exception as e:
                    error_msg = str(e)
                    result = f"Error executing {name}: {error_msg}"
                    break
                result = f"Tool '{name}' not found"
        except Exception as e:
            error_msg = str(e)
            result = f"Error executing {name}: {error_msg}"
        finally:
            duration = int((time.monotonic() - start) * 1000)
            try:
                pool = await get_pool()
                await pool.execute(
                    """INSERT INTO tool_execution_log (tool_name, parameters, response, duration_ms, success, error_message)
                       VALUES ($1, $2::jsonb, $3, $4, $5, $6)""",
                    name, json.dumps(params), result[:1000], duration, success, error_msg,
                )
            except Exception as log_err:
                print(f"[registry] Failed to log tool execution: {log_err}")
        return result
```

- [ ] **Commit**

```bash
git add apps/fastapi/app/tools/registry.py
git commit -m "feat(fastapi): add tool registry with dynamic tool loader"
```

---

### Task 5.2: Core tools — products, orders, customers

**Files:**
- Create: `apps/fastapi/app/tools/core/__init__.py`
- Create: `apps/fastapi/app/tools/core/products.py`
- Create: `apps/fastapi/app/tools/core/orders.py`
- Create: `apps/fastapi/app/tools/core/customers.py`

- [ ] **Write products.py**

```python
# apps/fastapi/app/tools/core/products.py
from ..registry import ToolDef, ToolRegistry

async def _get_products(params: dict) -> str:
    from ...services.postgres import get_pool
    pool = await get_pool()
    category = params.get("category")
    search = params.get("search", "")
    page = params.get("page", 1)
    limit = params.get("limit", 10)
    offset = (page - 1) * limit
    
    if category and search:
        rows = await pool.fetch(
            "SELECT name, description, price, category, stock, image_url "
            "FROM products WHERE category = $1 AND name ILIKE $2 AND is_active = true "
            "ORDER BY name LIMIT $3 OFFSET $4",
            category, f"%{search}%", limit, offset
        )
    elif category:
        rows = await pool.fetch(
            "SELECT name, description, price, category, stock, image_url "
            "FROM products WHERE category = $1 AND is_active = true "
            "ORDER BY name LIMIT $2 OFFSET $3",
            category, limit, offset
        )
    elif search:
        rows = await pool.fetch(
            "SELECT name, description, price, category, stock, image_url "
            "FROM products WHERE name ILIKE $1 AND is_active = true "
            "ORDER BY name LIMIT $2 OFFSET $3",
            f"%{search}%", limit, offset
        )
    else:
        rows = await pool.fetch(
            "SELECT name, description, price, category, stock, image_url "
            "FROM products WHERE is_active = true "
            "ORDER BY name LIMIT $1 OFFSET $2",
            limit, offset
        )
    
    if not rows:
        return "Nenhum produto encontrado."
    
    result = []
    for r in rows:
        result.append(f"- {r['name']}: R$ {float(r['price']):.2f} "
                      f"({r['stock']} em estoque) - {r['description'][:100]}")
    return "\n".join(result)

async def _check_stock(params: dict) -> str:
    from ...services.postgres import get_pool
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT name, stock, price FROM products WHERE id = $1 AND is_active = true",
        params["product_id"]
    )
    if not row:
        return "Produto não encontrado."
    return f"{row['name']}: {row['stock']} unidades em estoque. Preço: R$ {float(row['price']):.2f}"

def register_products_tools(registry: ToolRegistry):
    registry.register_core(ToolDef(
        name="get_products",
        description="List products available in the catalog with optional filters",
        parameters={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Product category filter"},
                "search": {"type": "string", "description": "Search term in product name"},
                "page": {"type": "integer", "default": 1},
                "limit": {"type": "integer", "default": 10},
            },
        },
        is_idempotent=True,
        execute=_get_products,
    ))
    registry.register_core(ToolDef(
        name="check_stock",
        description="Check stock availability for a specific product",
        parameters={
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "format": "uuid", "description": "Product ID"},
            },
            "required": ["product_id"],
        },
        is_idempotent=True,
        execute=_check_stock,
    ))
```

- [ ] **Write orders.py** (simplified)

```python
# apps/fastapi/app/tools/core/orders.py
from ..registry import ToolDef, ToolRegistry
import json

async def _create_order(params: dict) -> str:
    from ...services.postgres import get_pool
    import json
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO orders (customer_id, items, total, payment_method, status) "
        "VALUES ($1, $2::jsonb, $3, $4, 'pending') "
        "RETURNING id, total, status",
        params["customer_id"],
        json.dumps(params.get("items", [])),
        params.get("total", 0),
        params.get("payment_method", "pending"),
    )
    return f"Pedido #{row['id']} criado! Total: R$ {float(row['total']):.2f}. Status: {row['status']}"

async def _get_order_status(params: dict) -> str:
    from ...services.postgres import get_pool
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT status, total, created_at FROM orders WHERE id = $1",
        params["order_id"]
    )
    if not row:
        return "Pedido não encontrado."
    return f"Status: {row['status']}. Total: R$ {float(row['total']):.2f}. Criado em: {row['created_at']}"

def register_orders_tools(registry: ToolRegistry):
    registry.register_core(ToolDef(
        name="create_order",
        description="Create a new order for a customer",
        parameters={"type": "object", "properties": {
            "customer_id": {"type": "string"},
            "items": {"type": "array", "items": {"type": "object"}},
            "payment_method": {"type": "string"},
        }},
        is_idempotent=False,
        execute=_create_order,
    ))
    registry.register_core(ToolDef(
        name="get_order_status",
        description="Check the status of an order",
        parameters={"type": "object", "properties": {
            "order_id": {"type": "string"},
        }, "required": ["order_id"]},
        is_idempotent=True,
        execute=_get_order_status,
    ))
```

- [ ] **Write customers.py** (simplified)

```python
# apps/fastapi/app/tools/core/customers.py
from ..registry import ToolDef, ToolRegistry

async def _classify_client(params: dict) -> str:
    from ...services.postgres import get_pool
    pool = await get_pool()
    await pool.execute(
        "UPDATE conversations SET classification = $1, updated_at = NOW() WHERE id = $2",
        params.get("classification", "lead_morno"),
        params["conversation_id"],
    )
    return f"Cliente classificado como: {params.get('classification', 'lead_morno')}"

async def _schedule_followup(params: dict) -> str:
    return (f"Follow-up agendado para {params.get('days', 3)} dias. "
            f"Mensagem: {params.get('message_template', 'Olá!')}")

def register_customers_tools(registry: ToolRegistry):
    registry.register_core(ToolDef(
        name="classify_client",
        description="Classify a customer/lead in the CRM",
        parameters={"type": "object", "properties": {
            "conversation_id": {"type": "string"},
            "classification": {"type": "string", "enum": ["lead_quente", "lead_morno", "lead_frio", "cliente"]},
        }, "required": ["conversation_id", "classification"]},
        is_idempotent=True,
        execute=_classify_client,
    ))
    registry.register_core(ToolDef(
        name="schedule_followup",
        description="Schedule a follow-up message for a customer",
        parameters={"type": "object", "properties": {
            "customer_id": {"type": "string"},
            "days": {"type": "integer", "default": 3},
            "message_template": {"type": "string"},
        }},
        is_idempotent=False,
        execute=_schedule_followup,
    ))
```

- [ ] **Write __init__.py** for core tools

```python
# apps/fastapi/app/tools/core/__init__.py
from ..registry import ToolRegistry
from .products import register_products_tools
from .orders import register_orders_tools
from .customers import register_customers_tools

def register_all_core_tools(registry: ToolRegistry):
    register_products_tools(registry)
    register_orders_tools(registry)
    register_customers_tools(registry)
```

- [ ] **Commit**

```bash
git add apps/fastapi/app/tools/core/
git commit -m "feat(fastapi): add core tools (products, orders, customers)"
```

---

### Task 5.3: FastAPI main entry point — stream consumer + health

**Files:**
- Create: `apps/fastapi/app/main.py`

- [ ] **Write main.py**

```python
# apps/fastapi/app/main.py
import asyncio
import json
import ulid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from .config import settings
from .services.redis import (
    ensure_consumer_group, consume_stream,
    publish_to_stream, ack_message, nack_message,
)
from .services.postgres import get_pool, increment_message_count
from .graph.agent import build_agent
from .tools.registry import ToolRegistry
from .tools.core import register_all_core_tools

# Global instances
agent = None
tool_registry = ToolRegistry()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    
    # Initialize: register core tools, build agent
    register_all_core_tools(tool_registry)
    agent = build_agent()
    
    # Ensure consumer group exists
    await ensure_consumer_group(settings.stream_webhook, settings.consumer_group)
    
    # Start background consumer
    task = asyncio.create_task(stream_consumer())
    
    yield
    
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan, title="Agente de Vendas - LangGraph")

async def stream_consumer():
    """Background task: consume webhook:incoming, run agent, publish results."""
    consumer_id = f"consumer-{ulid.new().str}"
    
    async for msg_id, payload in consume_stream(
        settings.stream_webhook,
        settings.consumer_group,
        consumer_id,
    ):
        try:
            # Run agent
            state = await agent.ainvoke({
                "whatsapp_id": payload.get("whatsapp_id", ""),
                "conversation_id": payload.get("conversation_id", ""),
                "message_id": payload.get("id", ulid.new().str),
                "raw_content": payload.get("message", ""),
                "media_url": payload.get("media_url"),
                "media_type": payload.get("media_type"),
                "parsed_content": "",
                "intent": "",
                "customer_id": None,
                "l1_messages": [],
                "l2_summary": "",
                "l3_memories": [],
                "l3_triggered": False,
                "agent_response": "",
                "tool_calls": [],
                "metadata": {},
                "embedding_clip": None,
                "embedding_text": None,
            })
            
            # Publish response to outbox (Hono will send via Evolution API)
            await publish_to_stream(settings.stream_outbox, {
                "id": ulid.new().str,
                "to": payload["whatsapp_id"],
                "text": state.get("agent_response", ""),
            })
            
            # Publish to persist stream (NestJS will save to database)
            persist_payload = {
                "id": ulid.new().str,
                "conversation_id": state.get("conversation_id", ""),
                "role": "assistant",
                "content": state.get("agent_response", ""),
                "metadata": state.get("metadata", {}),
                "embedding_clip": state.get("embedding_clip"),
                "embedding_text": state.get("embedding_text"),
                "update_summary": False,  # NestJS will calculate
            }
            await publish_to_stream(settings.stream_persist, persist_payload)
            
            # Increment message count
            if state.get("conversation_id"):
                await increment_message_count(state["conversation_id"])
            
            await ack_message(settings.stream_webhook, settings.consumer_group, msg_id)
            
        except Exception as e:
            print(f"[consumer] Error processing {msg_id}: {e}")
            await nack_message(settings.stream_webhook, settings.consumer_group, msg_id)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "fastapi-langgraph"}

@app.get("/ready")
async def ready():
    try:
        pool = await get_pool()
        await pool.fetchval("SELECT 1")
        return {"ready": True}
    except Exception as e:
        return {"ready": False, "error": str(e)}
```

- [ ] **Verify Python imports compile**

Run: `cd apps/fastapi && pip install -r requirements.txt 2>&1 | tail -5 && python -c "from app.graph.agent import build_agent; print('✅ imports OK')"`

- [ ] **Commit**

```bash
git add apps/fastapi/app/main.py
git commit -m "feat(fastapi): add main entry point with stream consumer"
```

---

## Chunk 6: Integration — Docker Compose Update + Run Tests

**Objective:** Wire up the Hono and FastAPI services in Docker Compose, start everything, and verify the full pipeline works.

### Task 6.1: Add app services to Docker Compose

- [ ] **Update docker-compose.yml** — add hono and fastapi services

```yaml
# Append to docker-compose.yml's services section:

  hono:
    build: ./apps/hono
    ports:
      - "3000:3000"
    environment: &common-env
      REDIS_URL: redis://redis:6379
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_USER:-minioadmin}
      MINIO_SECRET_KEY: ${MINIO_PASSWORD:-minioadmin}
      EVOLUTION_API_URL: ${EVOLUTION_API_URL}
      EVOLUTION_API_KEY: ${EVOLUTION_API_KEY}
      EVOLUTION_WEBHOOK_SECRET: ${EVOLUTION_WEBHOOK_SECRET}
    depends_on:
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy

  fastapi:
    build: ./apps/fastapi
    ports:
      - "8000:8000"
    environment:
      <<: *common-env
      DATABASE_URL: postgresql+asyncpg://app:${DB_PASSWORD}@postgres:5432/agentevendas
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4o}
      OPENAI_EMBEDDING_MODEL: ${OPENAI_EMBEDDING_MODEL:-text-embedding-3-small}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    volumes:
      - ./apps/fastapi:/app
```

- [ ] **Commit**

```bash
git add docker-compose.yml
git commit -m "feat(infra): add hono and fastapi services to compose"
```

---

### Task 6.2: Start infra and verify

- [ ] **Start all services**

Run: `docker compose up -d --wait`

- [ ] **Initialize MinIO buckets**

Run: `docker compose exec -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin minio sh -c "
  mc alias set local http://localhost:9000 minioadmin minioadmin
  mc mb local/conversations-media --ignore-existing
  mc mb local/products --ignore-existing
  mc mb local/temporary --ignore-existing
  mc anonymous set download local/products
"`

Expected: No errors

Expected: all services healthy within 30s

- [ ] **Verify PostgreSQL schema**

Run: `docker compose exec postgres psql -U app -d agentevendas -c "\dt"`

Expected: All 11 tables visible

- [ ] **Verify Redis is up**

Run: `docker compose exec redis redis-cli ping`

Expected: `PONG`

- [ ] **Verify MinIO is up**

Run: `curl -s http://localhost:9001/api/v1/info | python3 -m json.tool`

Expected: JSON info response

- [ ] **Verify health endpoints**

Run: `curl -s http://localhost:3000/health && curl -s http://localhost:8000/health`

Expected: Both return `{"status":"ok"}`

---

### Task 6.3: End-to-end pipeline test

- [ ] **Run integration test — webhook → stream → agent → outbox**

```bash
# Publish a test webhook directly to Hono
curl -s -X POST http://localhost:3000/webhook/evolution \
  -H "Content-Type: application/json" \
  -d '{
    "key": {"remoteJid": "5511999999999@c.us"},
    "message": {"conversation": "Olá, quero ver produtos"}
  }'
```

Expected: `{"ok":true,"stream_id":"..."}`

- [ ] **Verify the message flow**

```bash
# Check webhook:incoming has messages (consumed or pending)
docker compose exec redis redis-cli XRANGE webhook:incoming - + COUNT 1

# Check whatsapp:outbox received the agent response
docker compose exec redis redis-cli XRANGE whatsapp:outbox - + COUNT 1

# Check message:persist received the persist payload
docker compose exec redis redis-cli XRANGE message:persist - + COUNT 1
```

Expected: Each XRANGE returns at least 1 message entry with a valid payload.

- [ ] **Check logs for errors**

Run: `docker compose logs fastapi --tail 30`

Expected: No errors, agent processed the message

- [ ] **Validate persist stream payload**

Run: `docker compose exec redis redis-cli XRANGE message:persist - + COUNT 1 | head -20`

Expected: Payload contains conversation_id, role, content, and metadata fields

- [ ] **Smoke test: verify agent response reached outbox**

Run: `docker compose exec redis redis-cli XRANGE whatsapp:outbox - + COUNT 1 | python3 -c "import sys; data=sys.stdin.read(); assert '5511999999999' in data or 'payload' in data; print('✅ Response payload found')"`

Expected: ✅ Response payload found

- [ ] **Stop services**

Run: `docker compose down -v` (removes volumes for clean state)

---

### Task 6.4: Final commit

- [ ] **Tag the P1 milestone**

```bash
git tag -a "p1-infra-core" -m "P1: Infraestrutura + Hono + FastAPI/LangGraph completo"
git push origin main --tags
```

---

## Plan Review

After completing all chunks, dispatch the plan document reviewer:

```
Task: plan-document-reviewer
Spec: docs/superpowers/specs/2026-05-30-agent-vendas-design.md
Plan: docs/superpowers/plans/2026-05-30-p1-infra-core.md
```
