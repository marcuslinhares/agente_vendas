#!/bin/bash
# setup.sh — Initialize the project for development
set -e

echo "🚀 Agente de Vendas — Setup"
echo "============================"

# 1. Environment file
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✅ .env created from .env.example"
else
  echo "✅ .env already exists"
fi

# 2. Install dependencies
echo ""
echo "📦 Installing dependencies..."

echo "  → Hono..."
cd apps/hono && npm install --silent 2>/dev/null && cd ../..

echo "  → FastAPI..."
cd apps/fastapi && pip install -q -r requirements.txt 2>/dev/null && cd ../..

echo "  → NestJS..."
cd apps/nestjs && npm install --silent 2>/dev/null && cd ../..

echo "  → Next.js..."
cd apps/web && npm install --silent 2>/dev/null && cd ../..

# 3. Start services
echo ""
echo "🐳 Starting Docker services..."
docker compose up -d --wait 2>&1 | tail -3

# 4. Init MinIO buckets
echo ""
echo "🪣 Initializing MinIO buckets..."
docker compose exec -e MINIO_ROOT_USER=${MINIO_USER:-minioadmin} -e MINIO_ROOT_PASSWORD=${MINIO_PASSWORD:-minioadmin} minio sh -c "
  mc alias set local http://localhost:9000 ${MINIO_USER:-minioadmin} ${MINIO_PASSWORD:-minioadmin} 2>/dev/null
  mc mb local/conversations-media --ignore-existing 2>/dev/null
  mc mb local/products --ignore-existing 2>/dev/null
  mc mb local/temporary --ignore-existing 2>/dev/null
  mc anonymous set download local/products 2>/dev/null
" 2>/dev/null
echo "✅ MinIO buckets ready"

# 5. Verify
echo ""
echo "📡 Verifying services..."
sleep 3
for url in http://localhost:3000/health http://localhost:8000/health http://localhost:4000/health; do
  status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "$url" 2>/dev/null || echo "000")
  name=$(echo "$url" | awk -F/ '{print $3}' | awk -F: '{print $1}')
  port=$(echo "$url" | awk -F/ '{print $3}' | awk -F: '{print $2}')
  if [ "$status" != "000" ]; then
    echo "  ✅ $name ($port) — HTTP $status"
  else
    echo "  ❌ $name ($port) — offline"
  fi
done

echo ""
echo "✅ Setup complete!"
echo "   CRM:  http://localhost:3001"
echo "   API:  http://localhost:4000/api/v1"
