# P3: CRM Next.js — Frontend

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development.

**Goal:** Implement the CRM frontend in Next.js that consumes the NestJS API.

**Architecture:** Next.js 14 App Router with shadcn/ui components. Server components for auth pages, client components for interactive dashboards. @tanstack/react-query for API calls to NestJS backend.

**Tech Stack:** Next.js 14, React 18, shadcn/ui, Tailwind CSS, @tanstack/react-query, lucide-react.

**Spec:** `docs/superpowers/specs/2026-05-30-agent-vendas-design.md` (§11)

---

## Chunk 1: Project Setup + Auth

### Task 1.1: Scaffold Next.js project

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tailwind.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/Dockerfile`

- [ ] **Write package.json**

```json
{
  "name": "@agente-vendas/web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "@tanstack/react-query": "^5.56.0",
    "lucide-react": "^0.441.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.5.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "@types/node": "^20.14.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "shadcn-ui": "^0.9.0"
  }
}
```

- [ ] **Write next.config.ts** — configure API proxy

```typescript
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000/api/v1'}/:path*`,
      },
    ];
  },
};

export default nextConfig;
```

- [ ] **Write tailwind.config.ts, tsconfig.json, Dockerfile** — standard Next.js configs

- [ ] **Install + verify**

Run: `cd apps/web && npm install 2>&1 | tail -3`

- [ ] **Commit**

```bash
git add apps/web/
git commit -m "feat(web): scaffold Next.js project"
```

---

### Task 1.2: Layout + Providers + shadcn/ui init

**Files:**
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/globals.css`
- Create: `apps/web/src/lib/api-client.ts`
- Create: `apps/web/src/components/ui/` (shadcn button, card, input, table)

- [ ] **Write layout.tsx** — React Query provider + metadata + font
- [ ] **Write globals.css** — Tailwind imports + shadcn CSS variables
- [ ] **Write api-client.ts** — fetch wrapper that adds JWT from cookie/localStorage

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000/api/v1';

export async function apiClient<T = any>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  let token: string | null = null;
  if (typeof window !== 'undefined') {
    // Read token from localStorage (simplified — httpOnly cookie in production)
    token = localStorage.getItem('token');
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message || `HTTP ${res.status}`);
  }

  return res.json();
}
```

- [ ] **Install shadcn/ui** — `npx shadcn-ui@latest init` then add button, card, input, table, badge, dialog

- [ ] **Commit**

```bash
git add apps/web/src/
git commit -m "feat(web): add layout, API client, and shadcn/ui components"
```

---

### Task 1.3: Auth pages — Login + Register

**Files:**
- Create: `apps/web/src/app/(auth)/login/page.tsx`
- Create: `apps/web/src/app/(auth)/register/page.tsx`

- [ ] **Write login page** — email + password form, calls `/api/auth/login`, stores token

```tsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const { accessToken } = await apiClient<{ accessToken: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem('token', accessToken);
      router.push('/');
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <form onSubmit={handleSubmit} className="w-96 space-y-4 p-8">
        <h1 className="text-2xl font-bold">Login</h1>
        {error && <p className="text-red-500">{error}</p>}
        <input type="email" placeholder="Email" value={email}
          onChange={e => setEmail(e.target.value)}
          className="w-full rounded border p-2" required />
        <input type="password" placeholder="Senha" value={password}
          onChange={e => setPassword(e.target.value)}
          className="w-full rounded border p-2" required />
        <button type="submit" className="w-full rounded bg-blue-600 p-2 text-white">
          Entrar
        </button>
        <a href="/register" className="block text-center text-sm text-blue-600">
          Criar conta
        </a>
      </form>
    </div>
  );
}
```

- [ ] **Write register page** — similar form, calls POST /api/auth/register

- [ ] **Commit**

```bash
git add apps/web/src/app/(auth)/
git commit -m "feat(web): add login and register pages"
```

---

## Chunk 2: Dashboard + Conversations

### Task 2.1: Dashboard page

**Files:**
- Create: `apps/web/src/app/(dashboard)/layout.tsx` — sidebar navigation
- Create: `apps/web/src/app/(dashboard)/page.tsx` — dashboard with KPIs

- [ ] **Write dashboard layout** — sidebar with Navigation links + logout button

Pages in sidebar: Dashboard, Conversas, Produtos, Clientes, Pedidos, Tools, Config

- [ ] **Write dashboard page** — stat cards (active conversations, leads by classification, orders today) using apiClient

- [ ] **Commit**

```bash
git add apps/web/src/app/(dashboard)/
git commit -m "feat(web): add dashboard layout and KPI page"
```

---

### Task 2.2: Conversations page + Chat view

**Files:**
- Create: `apps/web/src/app/(dashboard)/conversations/page.tsx`
- Create: `apps/web/src/app/(dashboard)/conversations/[id]/page.tsx`

- [ ] **Write conversations list** — table with status, classification, last message, date
  - Uses `useQuery` from @tanstack/react-query
  - Filter by status/classification

- [ ] **Write conversation detail/chat** — message history + send message form
  - Fetches `GET /api/conversations/:id`
  - Shows message bubbles (user vs assistant)
  - Form to send message via `POST /api/conversations/:id/send`

- [ ] **Commit**

```bash
git add apps/web/src/app/(dashboard)/conversations/
git commit -m "feat(web): add conversations list and chat view"
```

---

## Chunk 3: Products + Customers + Tools

### Task 3.1: Products CRUD page

**Files:**
- Create: `apps/web/src/app/(dashboard)/products/page.tsx`

- [ ] **Write products page** — table of products (name, price, stock, category)
  - CRUD dialog forms using shadcn dialog component
  - Image upload via file input → calls `/api/upload/product/:id`

- [ ] **Commit**

```bash
git add apps/web/src/app/(dashboard)/products/
git commit -m "feat(web): add products CRUD page"
```

---

### Task 3.2: Customers page

**Files:**
- Create: `apps/web/src/app/(dashboard)/customers/page.tsx`

- [ ] **Write customers page** — table with classification badges, search, filter
  - Classification action: dropdown to change classification
  - Calls `POST /api/customers/classify`

- [ ] **Commit**

```bash
git add apps/web/src/app/(dashboard)/customers/
git commit -m "feat(web): add customers page"
```

---

### Task 3.3: Tools + Orders + Settings pages

**Files:**
- Create: `apps/web/src/app/(dashboard)/tools/page.tsx`
- Create: `apps/web/src/app/(dashboard)/orders/page.tsx`
- Create: `apps/web/src/app/(dashboard)/settings/page.tsx`

- [ ] **Write tools page** — list tools, create/edit dialog with JSON schema editor
- [ ] **Write orders page** — table with status filter
- [ ] **Write settings page** — Evolution API, LLM model, webhook status display

- [ ] **Commit**

```bash
git add apps/web/src/app/(dashboard)/tools/ apps/web/src/app/(dashboard)/orders/ apps/web/src/app/(dashboard)/settings/
git commit -m "feat(web): add tools, orders, and settings pages"
```

---

## Chunk 4: Docker Compose + Final Integration

### Task 4.1: Add web service to Docker Compose + verify

- [ ] **Update docker-compose.yml** — add web service after nestjs

```yaml
  web:
    build: ./apps/web
    ports:
      - "3001:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://nestjs:4000/api/v1
    depends_on:
      - nestjs
```

- [ ] **Rebuild and verify**

Run: `docker compose up -d --build --wait`

Verify: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/`

Expected: 200 (login page loads)

- [ ] **Tag P3**

```bash
git tag -a "p3-crm-frontend" -m "P3: CRM Next.js frontend"
```

- [ ] **Final report**
