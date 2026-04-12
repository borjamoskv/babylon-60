#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SKILLS_ROOT="${1:-${HOME}/.gemini/antigravity/skills}"
REPORT_DIR="${2:-${REPO_ROOT}/reports/skill-audit}"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"

JSON_PATH="${REPORT_DIR}/skill_audit_${TIMESTAMP}.json"
MARKDOWN_PATH="${REPORT_DIR}/skill_audit_${TIMESTAMP}.md"
LATEST_JSON_PATH="${REPORT_DIR}/skill_audit_latest.json"
LATEST_MARKDOWN_PATH="${REPORT_DIR}/skill_audit_latest.md"

mkdir -p "${REPORT_DIR}"

python3 "${REPO_ROOT}/scratch/skill_auditor.py" \
  --skills-root "${SKILLS_ROOT}" \
  --json-out "${JSON_PATH}" \
  --markdown-out "${MARKDOWN_PATH}" \
  --stdout-format summary

cp "${JSON_PATH}" "${LATEST_JSON_PATH}"
cp "${MARKDOWN_PATH}" "${LATEST_MARKDOWN_PATH}"

printf 'Audit reports written to:\n- %s\n- %s\n' "${JSON_PATH}" "${MARKDOWN_PATH}"
