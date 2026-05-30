#!/bin/sh
# infra/minio/buckets.sh
# Run after MinIO starts to create required buckets.
# Usage: docker compose exec -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin minio sh /scripts/buckets.sh

mc alias set local http://localhost:9000 ${MINIO_ROOT_USER:-minioadmin} ${MINIO_ROOT_PASSWORD:-minioadmin}

# Create buckets (ignore if already exists)
mc mb local/conversations-media --ignore-existing
mc mb local/products --ignore-existing
mc mb local/temporary --ignore-existing

# Set public download policy for products
mc anonymous set download local/products

# Lifecycle: expire temporary files after 1 hour
mc ilm rule add local/temporary --expire-days 0 --expire-hours 1

echo "MinIO buckets initialized successfully"
