# P2: NestJS Backend — Stream Consumer + REST API + BullMQ Jobs

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the NestJS backend that consumes the `message:persist` Redis Stream, exposes a REST API for the CRM, and runs scheduled jobs via BullMQ.

**Architecture:** NestJS with modular structure. A Stream consumer reads from Redis Streams (ioredis) and persists data to PostgreSQL (TypeORM + pgvector). A REST API layer exposes CRUD endpoints protected by JWT auth. BullMQ workers handle scheduled jobs (follow-ups, reindexing, cleanup).

**Tech Stack:** Node.js 22, NestJS 10, TypeORM 0.3, pgvector, @nestjs/bullmq, ioredis, JWT (passport), MinIO S3 client.

**Spec:** `docs/superpowers/specs/2026-05-30-agent-vendas-design.md` (§7, §9)

---

## Chunk 1: Project Setup + Database Entities

### Task 1.1: Scaffold NestJS project

**Files:**
- Create: `apps/nestjs/package.json`
- Create: `apps/nestjs/tsconfig.json`
- Create: `apps/nestjs/nest-cli.json`
- Create: `apps/nestjs/Dockerfile`

- [ ] **Write package.json**

```json
{
  "name": "@agente-vendas/nestjs",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "build": "nest build",
    "start": "node dist/main",
    "dev": "nest start --watch"
  },
  "dependencies": {
    "@nestjs/common": "^10.4.0",
    "@nestjs/core": "^10.4.0",
    "@nestjs/platform-express": "^10.4.0",
    "@nestjs/typeorm": "^10.0.0",
    "@nestjs/bullmq": "^10.2.0",
    "@nestjs/jwt": "^10.2.0",
    "@nestjs/passport": "^10.0.3",
    "typeorm": "^0.3.20",
    "pg": "^8.13.0",
    "ioredis": "^5.4.0",
    "bullmq": "^5.12.0",
    "passport": "^0.7.0",
    "passport-jwt": "^4.0.1",
    "bcrypt": "^5.1.1",
    "class-validator": "^0.14.1",
    "class-transformer": "^0.5.1",
    "@aws-sdk/client-s3": "^3.600.0",
    "ulid": "^2.3.0",
    "openai": "^4.60.0"
  },
  "devDependencies": {
    "@nestjs/cli": "^10.4.0",
    "@nestjs/schematics": "^10.1.0",
    "typescript": "^5.5.0",
    "@types/node": "^20.14.0",
    "@types/bcrypt": "^5.0.2",
    "@types/passport-jwt": "^4.0.1"
  }
}
```

- [ ] **Write tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "dist",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "emitDecoratorMetadata": true,
    "experimentalDecorators": true,
    "baseUrl": "./",
    "paths": { "@/*": ["src/*"] }
  },
  "include": ["src/**/*"]
}
```

- [ ] **Write nest-cli.json**

```json
{
  "$schema": "https://json.schemastore.org/nest-cli",
  "collection": "@nestjs/schematics",
  "sourceRoot": "src",
  "compilerOptions": {
    "deleteOutDir": true
  }
}
```

- [ ] **Write Dockerfile**

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
COPY --from=builder /app/dist dist/
COPY --from=builder /app/node_modules node_modules/
EXPOSE 4000
CMD ["node", "dist/main"]
```

- [ ] **Install deps and verify**

Run: `cd apps/nestjs && npm install 2>&1 | tail -3`

Expected: packages installed

- [ ] **Commit**

```bash
git add apps/nestjs/
git commit -m "feat(nestjs): scaffold project with package.json and Dockerfile"
```

---

### Task 1.2: TypeORM entities (PostgreSQL + pgvector)

**Files:**
- Create: `apps/nestjs/src/entities/conversation.entity.ts`
- Create: `apps/nestjs/src/entities/message.entity.ts`
- Create: `apps/nestjs/src/entities/message-embedding.entity.ts`
- Create: `apps/nestjs/src/entities/product.entity.ts`
- Create: `apps/nestjs/src/entities/product-embedding.entity.ts`
- Create: `apps/nestjs/src/entities/customer.entity.ts`
- Create: `apps/nestjs/src/entities/order.entity.ts`
- Create: `apps/nestjs/src/entities/tool-catalog.entity.ts`
- Create: `apps/nestjs/src/entities/tool-execution-log.entity.ts`
- Create: `apps/nestjs/src/entities/user.entity.ts`
- Create: `apps/nestjs/src/entities/index.ts`

- [ ] **Write each entity file**

```typescript
// apps/nestjs/src/entities/conversation.entity.ts
import { Entity, Column, PrimaryGeneratedColumn, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity('conversations')
export class Conversation {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'text', unique: true })
  whatsappId: string;

  @Column({ nullable: true })
  customerId: string;

  @Column({ default: 'active' })
  status: string;

  @Column({ type: 'text', nullable: true })
  summary: string;

  @Column({ default: 0 })
  summaryVersion: number;

  @Column({ default: 0 })
  messageCount: number;

  @Column({ nullable: true })
  classification: string;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}
```

Create similar entities for all 10+ tables following the spec schema (§8).

Key entity details:
- `Message`: messageId (unique), conversationId FK, role, content, mediaUrl, mediaType, metadata JSONB
- `MessageEmbedding`: conversationId FK, messageId FK, content, mediaUrl, embedding VECTOR (string column in TypeORM — pgvector uses string format), embeddingClip VECTOR
- `Product`: name, description, price DECIMAL, category, stock INT, imageUrl
- `ProductEmbedding`: productId FK, content, mediaUrl, embedding VECTOR, embeddingClip VECTOR
- `Customer`: whatsappId unique, name, email, phone, classification, tags TEXT[], metadata JSONB
- `Order`: customerId FK, items JSONB, total DECIMAL, status, paymentMethod
- `ToolCatalog`: name unique, description, schema JSONB, endpoint, httpMethod, headers JSONB, rateLimit, timeoutMs, isActive
- `ToolExecutionLog`: toolName, conversationId, parameters JSONB, response, durationMs, success, errorMessage
- `User`: email unique, passwordHash, name, role

For vector columns, use TypeORM's `column: { type: 'vector', array: true }` or string.

- [ ] **Write index.ts**

```typescript
export { Conversation } from './conversation.entity';
export { Message } from './message.entity';
export { MessageEmbedding } from './message-embedding.entity';
export { Product } from './product.entity';
export { ProductEmbedding } from './product-embedding.entity';
export { Customer } from './customer.entity';
export { Order } from './order.entity';
export { ToolCatalog } from './tool-catalog.entity';
export { ToolExecutionLog } from './tool-execution-log.entity';
export { User } from './user.entity';
```

- [ ] **Commit**

```bash
git add apps/nestjs/src/entities/
git commit -m "feat(nestjs): add TypeORM entities for all 10 tables"
```

---

### Task 1.3: App module + TypeORM + Redis config

**Files:**
- Create: `apps/nestjs/src/app.module.ts`
- Create: `apps/nestjs/src/main.ts`

- [ ] **Write app.module.ts**

```typescript
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { BullModule } from '@nestjs/bullmq';
import { entities } from './entities';

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'postgres',
      url: process.env.DATABASE_URL || 'postgresql://app:localdev@localhost:5432/agentevendas',
      entities,
      synchronize: false, // Use migrations in production
    }),
    BullModule.forRoot({
      connection: {
        host: process.env.REDIS_URL?.replace('redis://', '')?.split(':')[0] || 'localhost',
        port: parseInt(process.env.REDIS_URL?.split(':')[2] || '6379'),
      },
    }),
  ],
})
export class AppModule {}
```

- [ ] **Write main.ts**

```typescript
import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  
  app.setGlobalPrefix('api/v1');
  app.enableCors();
  app.useGlobalPipes(new ValidationPipe({ transform: true, whitelist: true }));
  
  const port = process.env.NESTJS_PORT || 4000;
  await app.listen(port);
  console.log(`✅ NestJS running on port ${port}`);
}
bootstrap();
```

- [ ] **Verify builds**

Run: `cd apps/nestjs && npx tsc --noEmit 2>&1 | head -20`

Expected: Compilation succeeds

- [ ] **Commit**

```bash
git add apps/nestjs/src/app.module.ts apps/nestjs/src/main.ts
git commit -m "feat(nestjs): add AppModule with TypeORM and BullMQ config"
```

---

## Chunk 2: Stream Consumer + Auth

### Task 2.1: Redis Stream consumer for message:persist

**Files:**
- Create: `apps/nestjs/src/stream/persist.consumer.ts`
- Create: `apps/nestjs/src/stream/stream.module.ts`

- [ ] **Write persist.consumer.ts**

The consumer reads from `message:persist` Redis Stream using ioredis, processes messages:
1. Check idempotency (messageId already exists?)
2. Save message to messages table
3. Save embedding if provided
4. Update customer last_contact_at
5. Update conversation summary if update_summary flag is set

```typescript
import { Injectable, OnModuleInit, Logger } from '@nestjs/common';
import Redis from 'ioredis';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Message, Conversation, MessageEmbedding, Customer } from '../entities';

@Injectable()
export class PersistConsumer implements OnModuleInit {
  private readonly logger = new Logger(PersistConsumer.name);
  private redis: Redis;

  constructor(
    @InjectRepository(Message) private msgRepo: Repository<Message>,
    @InjectRepository(Conversation) private convRepo: Repository<Conversation>,
    @InjectRepository(MessageEmbedding) private embRepo: Repository<MessageEmbedding>,
    @InjectRepository(Customer) private custRepo: Repository<Customer>,
  ) {
    this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
  }

  async onModuleInit() {
    this.startConsumer();
  }

  private async startConsumer() {
    const group = 'nestjs-workers';
    const stream = 'message:persist';
    const consumer = `consumer-${Date.now()}`;

    try {
      await this.redis.xgroup('CREATE', stream, group, '$', 'MKSTREAM');
    } catch (e: any) {
      if (!e.message?.includes('BUSYGROUP')) throw e;
    }

    this.logger.log(`Listening to ${stream} as ${consumer}`);

    setInterval(async () => {
      try {
        const result = await this.redis.xreadgroup(
          'GROUP', group, consumer,
          'COUNT', 5,
          'BLOCK', 2000,
          'STREAMS', stream, '>',
        );
        if (!result) return;

        for (const [, messages] of result) {
          for (const [msgId, fields] of messages) {
            await this.processMessage(msgId, JSON.parse(fields['payload']));
            await this.redis.xack(stream, group, msgId);
          }
        }
      } catch (err) {
        this.logger.error('Consumer error', err);
      }
    }, 1000);
  }

  private async processMessage(msgId: string, payload: any) {
    // Idempotency check
    const exists = await this.msgRepo.findOne({ where: { messageId: payload.id } });
    if (exists) {
      this.logger.debug(`Skipping duplicate message ${payload.id}`);
      return;
    }

    // Save message
    const message = this.msgRepo.create({
      messageId: payload.id,
      conversationId: payload.conversation_id,
      role: payload.role,
      content: payload.content,
      mediaUrl: payload.media_url,
      mediaType: payload.media_type,
      metadata: payload.metadata || {},
    });
    await this.msgRepo.save(message);

    // Save embedding if provided
    if (payload.embedding_clip || payload.embedding_text) {
      try {
        const emb = this.embRepo.create({
          conversationId: payload.conversation_id,
          messageId: message.id,
          content: payload.content,
          mediaUrl: payload.media_url,
          embedding: payload.embedding_text ? JSON.stringify(payload.embedding_text) : null,
          embeddingClip: payload.embedding_clip ? JSON.stringify(payload.embedding_clip) : null,
        });
        await this.embRepo.save(emb);
      } catch (err) {
        this.logger.warn(`Failed to save embedding for message ${payload.id}: ${err}`);
      }
    }

    // Update customer last_contact_at
    try {
      await this.custRepo.update(
        { whatsappId: payload.whatsapp_id },
        { lastContactAt: new Date() },
      );
    } catch { /* Customer may not exist yet — that's fine */ }

    this.logger.debug(`Processed message ${payload.id}`);
  }
}
```

- [ ] **Write stream.module.ts**

```typescript
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { PersistConsumer } from './persist.consumer';
import { Message, Conversation, MessageEmbedding, Customer } from '../entities';

@Module({
  imports: [TypeOrmModule.forFeature([Message, Conversation, MessageEmbedding, Customer])],
  providers: [PersistConsumer],
})
export class StreamModule {}
```

- [ ] **Commit**

```bash
git add apps/nestjs/src/stream/
git commit -m "feat(nestjs): add Redis Stream consumer for message:persist"
```

---

### Task 2.2: JWT Auth module

**Files:**
- Create: `apps/nestjs/src/modules/auth/auth.module.ts`
- Create: `apps/nestjs/src/modules/auth/auth.controller.ts`
- Create: `apps/nestjs/src/modules/auth/auth.service.ts`
- Create: `apps/nestjs/src/modules/auth/jwt.strategy.ts`
- Create: `apps/nestjs/src/modules/auth/jwt-auth.guard.ts`

- [ ] **Write auth.service.ts** — register (bcrypt hash) + login (validate + JWT sign)
- [ ] **Write auth.controller.ts** — POST /api/v1/auth/register, POST /api/v1/auth/login
- [ ] **Write jwt.strategy.ts** — extracts JWT from Authorization Bearer header
- [ ] **Write jwt-auth.guard.ts** — @Injectable() guard extending AuthGuard('jwt')
- [ ] **Write auth.module.ts** — imports JwtModule, TypeOrmModule.forFeature([User]), provides strategies

- [ ] **Commit**

```bash
git add apps/nestjs/src/modules/auth/
git commit -m "feat(nestjs): add JWT auth module with register and login"
```

---

## Chunk 3: REST API Modules

### Task 3.1: Conversations + Messages modules

**Files:**
- Create: `apps/nestjs/src/modules/conversations/`
- Create: `apps/nestjs/src/modules/messages/`

Each module follows NestJS convention: controller, service, module.

- [ ] **ConversationsController** — GET /conversations (list with filters: status, classification, date), GET /conversations/:id (detail + messages), POST /conversations/:id/send (publish to whatsapp:outbox)
- [ ] **MessagesController** — GET /messages/:conv_id (pagination: offset/limit)
- [ ] **Register both in AppModule**

- [ ] **Commit**

```bash
git add apps/nestjs/src/modules/conversations/ apps/nestjs/src/modules/messages/
git commit -m "feat(nestjs): add conversations and messages API modules"
```

---

### Task 3.2: Products + Customers + Orders modules

**Files:**
- Create: `apps/nestjs/src/modules/products/`
- Create: `apps/nestjs/src/modules/customers/`
- Create: `apps/nestjs/src/modules/orders/`

- [ ] **ProductsController** — CRUD (POST, GET, PUT, DELETE /products), with pagination, category filter
- [ ] **CustomersController** — GET /customers (list), POST /customers/classify, GET /customers/:id
- [ ] **OrdersController** — GET /orders (list with status filter), GET /orders/:id

- [ ] **Register all in AppModule**

- [ ] **Commit**

```bash
git add apps/nestjs/src/modules/products/ apps/nestjs/src/modules/customers/ apps/nestjs/src/modules/orders/
git commit -m "feat(nestjs): add products, customers, and orders API modules"
```

---

### Task 3.3: Tools + MinIO modules

**Files:**
- Create: `apps/nestjs/src/modules/tools/`
- Create: `apps/nestjs/src/modules/minio/`

- [ ] **ToolsController** — POST /tools (create dynamic tool), PUT /tools/:id, GET /tools (list active), POST /tools/:id/test (dry-run execution)
  - On tool update/create: publish Redis Pub/Sub `tools:updated` for FastAPI cache invalidation

```typescript
// On tool create/update — invalidate FastAPI cache
import Redis from 'ioredis';
const redis = new Redis(process.env.REDIS_URL);
await redis.publish('tools:updated', JSON.stringify({ action: 'updated', tool_id: tool.id }));
```

- [ ] **MinIO Service** — S3 client for product image upload
  - POST /upload/product (multipart) → upload to MinIO `products/` bucket → update product.image_url

- [ ] **Commit**

```bash
git add apps/nestjs/src/modules/tools/ apps/nestjs/src/modules/minio/
git commit -m "feat(nestjs): add tools and minio modules"
```

---

## Chunk 4: BullMQ Jobs + Docker Compose

### Task 4.1: BullMQ job processors

**Files:**
- Create: `apps/nestjs/src/queue/followup.processor.ts`
- Create: `apps/nestjs/src/queue/reindex.processor.ts`
- Create: `apps/nestjs/src/queue/cleanup.processor.ts`
- Create: `apps/nestjs/src/queue/queue.module.ts`

- [ ] **Write processors**

```typescript
// followup.processor.ts
import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Job } from 'bullmq';

@Processor('followup')
export class FollowupProcessor extends WorkerHost {
  async process(job: Job) {
    // Query conversations with classification = 'lead_morno' and no contact > 3 days
    // Publish follow-up message to whatsapp:outbox stream
  }
}
```

Similar for reindex (products without embedding → generate CLIP + text embeddings), cleanup (remove temporary MinIO files older than 1h), and dlq-monitor (check dead-letter queue sizes).

- [ ] **Write queue.module.ts** — registers all processors and schedules with @nestjs/schedule or BullMQ repeatable jobs

- [ ] **Commit**

```bash
git add apps/nestjs/src/queue/
git commit -m "feat(nestjs): add BullMQ job processors for followup, reindex, cleanup"
```

---

### Task 4.2: Update Docker Compose + verify

- [ ] **Add nestjs service to docker-compose.yml**

```yaml
  nestjs:
    build: ./apps/nestjs
    ports:
      - "4000:4000"
    environment:
      <<: *common-env
      DATABASE_URL: postgresql://app:${DB_PASSWORD}@postgres:5432/agentevendas
      JWT_SECRET: ${JWT_SECRET}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
```

- [ ] **Start all services and test**

Run: `docker compose up -d --wait`

Verify: `curl -s http://localhost:4000/api/v1/auth/login` (should return 401 or valid response)

- [ ] **End-to-end: send webhook → Hono → FastAPI → NestJS persist**

Send a test webhook to Hono, verify message appears in PostgreSQL via NestJS API:
Run: `curl -s http://localhost:4000/api/v1/conversations`

- [ ] **Tag P2**

```bash
git tag -a "p2-nestjs-backend" -m "P2: NestJS backend with Stream consumer, API, and BullMQ jobs"
```

- [ ] **Final commit and report**
