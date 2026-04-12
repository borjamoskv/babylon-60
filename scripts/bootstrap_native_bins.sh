#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEST_DIR="${REPO_ROOT}/build/native/bin"

DEFAULT_SOURCE_ROOT="${HOME}/10_PROJECTS/Cortex-Persist/engine/cortex-core/target/release"
SOURCE_ROOT="${CORTEX_NATIVE_SOURCE_ROOT:-${DEFAULT_SOURCE_ROOT}}"

mkdir -p "${DEST_DIR}"

link_binary() {
  local binary_name="$1"
  local explicit_path="${2:-}"
  local source_path=""

  if [[ -n "${explicit_path}" ]]; then
    source_path="${explicit_path}"
  else
    source_path="${SOURCE_ROOT}/${binary_name}"
  fi

  if [[ ! -x "${source_path}" ]]; then
    echo "skip ${binary_name}: source not executable at ${source_path}" >&2
    return 1
  fi

  ln -snf "${source_path}" "${DEST_DIR}/${binary_name}"
  echo "linked ${binary_name} -> ${source_path}"
}

link_binary "cortex-db" "${CORTEX_NATIVE_DB_BIN:-${CORTEX_DB_BIN:-}}"
link_binary "cortex-strike" "${CORTEX_NATIVE_STRIKE_BIN:-${CORTEX_STRIKE_BIN:-}}"

echo "native cache ready at ${DEST_DIR}"
