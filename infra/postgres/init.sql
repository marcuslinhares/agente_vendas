CREATE EXTENSION IF NOT EXISTS vector;

-- ======================
-- Tables (ordered by FK dependencies)
-- ======================

-- Customers
CREATE TABLE IF NOT EXISTS customers (
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
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Products
CREATE TABLE IF NOT EXISTS products (
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

-- Dynamic tools catalog
CREATE TABLE IF NOT EXISTS tools_catalog (
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

-- CRM users
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    name            VARCHAR(200),
    role            VARCHAR(20) DEFAULT 'admin' CHECK (role IN ('admin', 'agent')),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_id     TEXT NOT NULL UNIQUE,
    customer_id     UUID REFERENCES customers(id) ON DELETE SET NULL,
    status          VARCHAR(20) DEFAULT 'active'
                    CHECK (status IN ('active', 'closed', 'followup')),
    summary         TEXT,
    summary_version INT DEFAULT 0,
    message_count   INT DEFAULT 0,
    classification  VARCHAR(50) CHECK (classification IN ('lead_quente','lead_morno','lead_frio','cliente')),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Messages
CREATE TABLE IF NOT EXISTS messages (
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

-- Orders
CREATE TABLE IF NOT EXISTS orders (
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

-- Message embeddings (L3 memory + vector search)
CREATE TABLE IF NOT EXISTS message_embeddings (
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

-- Product embeddings (RAG catalog)
CREATE TABLE IF NOT EXISTS product_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    content         TEXT,
    media_url       TEXT,
    embedding       VECTOR(1536),
    embedding_clip  VECTOR(512),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Tool execution log
CREATE TABLE IF NOT EXISTS tool_execution_log (
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

-- ======================
-- Indexes
-- ======================

-- Vector indexes (IVFFlat)
CREATE INDEX IF NOT EXISTS idx_msg_embeddings_conv ON message_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_msg_embeddings_clip ON message_embeddings
    USING ivfflat (embedding_clip vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_product_embeddings ON product_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_product_embeddings_clip ON product_embeddings
    USING ivfflat (embedding_clip vector_cosine_ops) WITH (lists = 100);

-- B-tree indexes for query performance
CREATE INDEX IF NOT EXISTS idx_messages_conv_created ON messages(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_whatsapp ON conversations(whatsapp_id);
CREATE INDEX IF NOT EXISTS idx_conversations_customer ON conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_classification ON conversations(classification);
CREATE INDEX IF NOT EXISTS idx_customers_classification ON customers(classification);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_embeddings_conv_created ON message_embeddings(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tools_active ON tools_catalog(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_tool_log_created ON tool_execution_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_log_conv ON tool_execution_log(conversation_id);
