#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-forward-tape-489302-m7}"
REGION="${REGION:-europe-west1}"
SERVICE_NAME="${SERVICE_NAME:-cortexpersist-cycle-api}"
IMAGE_URI="${IMAGE_URI:-gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest}"
CONTEXT_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${CONTEXT_DIR}"
}
trap cleanup EXIT

echo "Preparing isolated API build context at ${CONTEXT_DIR}"

mkdir -p "${CONTEXT_DIR}"

cp Dockerfile "${CONTEXT_DIR}/Dockerfile"
cp pyproject.toml README.md "${CONTEXT_DIR}/"
cp -R cortex "${CONTEXT_DIR}/cortex"

echo "Building image ${IMAGE_URI}"
gcloud builds submit \
  --project "${PROJECT_ID}" \
  --tag "${IMAGE_URI}" \
  "${CONTEXT_DIR}"

echo "Deploying ${SERVICE_NAME} to Cloud Run (${REGION})"
gcloud run deploy "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --image "${IMAGE_URI}" \
  --no-allow-unauthenticated \
  --port 8484 \
  --cpu 1 \
  --memory 1Gi \
  --max-instances 2 \
  --set-env-vars "CORTEX_DEPLOY=cloud,CORTEX_DB=/tmp/cortex.db,CORTEX_DB_PATH=/tmp/cortex.db,CORTEX_VECTOR_STORE_PATH=/tmp/vectors,CORTEX_SHARD_DIR=/tmp/shards,ANONYMIZED_TELEMETRY=False"

echo "Deployment completed for ${SERVICE_NAME}"
