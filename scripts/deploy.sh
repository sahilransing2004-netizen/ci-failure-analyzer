#!/usr/bin/env bash
set -euo pipefail

IMAGE="ghcr.io/sahilransing2004-netizen/ci-failure-analyzer"
TAG="${1:?Usage: scripts/deploy.sh <image-tag>}"
NETWORK="ci-failure-analyzer_default"
PROD_NAME="cfa-prod"
PROD_PORT=8080
STAGING_NAME="cfa-staging"
STAGING_PORT=8001
STAGING_HEALTH_PATH="${STAGING_HEALTH_PATH:-/health}"
PROD_HEALTH_PATH="${PROD_HEALTH_PATH:-/health}"

set -a
. ./.env
set +a

run_container() {
  local name="$1" port="$2" image="$3"
  docker run -d --name "$name" --network "$NETWORK" -p "$port:8000" \
    -e DATABASE_URL="postgresql+psycopg2://cfa:cfa_local_dev@db:5432/cfa" \
    -e OLLAMA_URL="http://ollama:11434" \
    -e OLLAMA_MODEL="llama3.2:3b" \
    -e WEBHOOK_TOKEN="$WEBHOOK_TOKEN" \
    "$image" > /dev/null
}

wait_healthy() {
  local port="$1" path="$2"
  for _ in $(seq 1 15); do
    if curl -fsS "http://localhost:${port}${path}" > /dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

echo "==> Pulling ${IMAGE}:${TAG}"
docker pull "${IMAGE}:${TAG}"

echo "==> Starting staging on port ${STAGING_PORT}"
docker rm -f "$STAGING_NAME" > /dev/null 2>&1 || true
run_container "$STAGING_NAME" "$STAGING_PORT" "${IMAGE}:${TAG}"

if ! wait_healthy "$STAGING_PORT" "$STAGING_HEALTH_PATH"; then
  echo "==> STAGING FAILED. Logs:"
  docker logs --tail 20 "$STAGING_NAME" || true
  docker rm -f "$STAGING_NAME" > /dev/null
  echo "==> Production was NOT touched."
  exit 1
fi
echo "==> Staging healthy"
docker rm -f "$STAGING_NAME" > /dev/null

PREVIOUS="$(docker inspect -f '{{.Config.Image}}' "$PROD_NAME" 2>/dev/null || true)"
echo "==> Previous production image: ${PREVIOUS:-none}"

echo "==> Deploying to production on port ${PROD_PORT}"
docker rm -f "$PROD_NAME" > /dev/null 2>&1 || true
run_container "$PROD_NAME" "$PROD_PORT" "${IMAGE}:${TAG}"

if wait_healthy "$PROD_PORT" "$PROD_HEALTH_PATH"; then
  echo "==> DEPLOY OK: ${IMAGE}:${TAG}"
  exit 0
fi

echo "==> PRODUCTION UNHEALTHY. Rolling back."
docker logs --tail 20 "$PROD_NAME" || true
docker rm -f "$PROD_NAME" > /dev/null
if [ -n "$PREVIOUS" ]; then
  run_container "$PROD_NAME" "$PROD_PORT" "$PREVIOUS"
  if wait_healthy "$PROD_PORT" "/health"; then
    echo "==> ROLLED BACK to ${PREVIOUS}"
  else
    echo "==> ROLLBACK FAILED. Manual action needed."
  fi
else
  echo "==> No previous image to roll back to."
fi
exit 1