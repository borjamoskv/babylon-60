#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-forward-tape-489302-m7}"
REGION="${REGION:-europe-west1}"
SERVICE_NAME="${SERVICE_NAME:-cortexpersist-cycle-site}"
IMAGE_URI="${IMAGE_URI:-gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest}"
CONTEXT_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${CONTEXT_DIR}"
}
trap cleanup EXIT

echo "Preparing isolated build context at ${CONTEXT_DIR}"

mkdir -p "${CONTEXT_DIR}/deploy/gcp" "${CONTEXT_DIR}/scripts" "${CONTEXT_DIR}/src" "${CONTEXT_DIR}/public"

cp package.json package-lock.json astro.config.mjs "${CONTEXT_DIR}/"
cp src/content.config.ts "${CONTEXT_DIR}/src/content.config.ts"
cp -R src/. "${CONTEXT_DIR}/src"
cp -R public/. "${CONTEXT_DIR}/public"
cp scripts/build-site.mjs "${CONTEXT_DIR}/scripts/build-site.mjs"
cp deploy/gcp/site.Dockerfile "${CONTEXT_DIR}/Dockerfile"
cp deploy/gcp/nginx-site.conf "${CONTEXT_DIR}/deploy/gcp/nginx-site.conf"

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
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 \
  --memory 512Mi \
  --max-instances 3

echo "Deployment completed for ${SERVICE_NAME}"
