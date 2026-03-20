#!/usr/bin/env bash
set -e

IMAGE_NAME="job-matcher-postgres"
CONTAINER_NAME="job-matcher-db"

POSTGRES_USER="postgres"
POSTGRES_PASSWORD="postgres"
POSTGRES_DB="job_matcher"
POSTGRES_PORT="5432"
DOCKERFILE="Dockerfile.db"

echo "Stopping old container if it exists..."
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

echo "Building Docker image..."
docker build -f "${DOCKERFILE}" -t "${IMAGE_NAME}" .

echo "Starting Postgres container..."
docker run -d \
  --name "${CONTAINER_NAME}" \
  -p "${POSTGRES_PORT}:5432" \
  -e POSTGRES_USER="${POSTGRES_USER}" \
  -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  -e POSTGRES_DB="${POSTGRES_DB}" \
  "${IMAGE_NAME}"

echo "Waiting a few seconds for Postgres to start..."
sleep 5

echo "Container started."
echo "Connection string:"
echo "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"