#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# CORTEX MCP Toolbox Launcher
#
# Starts the MCP Toolbox for Databases server against cortex.db.
# Prerequisites: install the current Toolbox binary or use npx:
#   go install github.com/googleapis/genai-toolbox@latest
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE="${TOOLBOX_PROFILE:-summary}"
case "${PROFILE}" in
    summary)
        TOOLS_FILE="${SCRIPT_DIR}/cortex-summary.yaml"
        ;;
    readonly)
        TOOLS_FILE="${SCRIPT_DIR}/cortex-readonly.yaml"
        ;;
    graph)
        TOOLS_FILE="${SCRIPT_DIR}/cortex-graph.yaml"
        ;;
    full)
        TOOLS_FILE="${SCRIPT_DIR}/tools.yaml"
        ;;
    *)
        echo "❌ Unknown TOOLBOX_PROFILE: ${PROFILE}"
        echo "   Expected one of: summary, readonly, graph, full"
        exit 1
        ;;
esac
export CORTEX_DB="${CORTEX_DB:-${HOME}/.cortex/cortex.db}"
PORT="${TOOLBOX_PORT:-5050}"
MODE="${TOOLBOX_MODE:-http}"

# Add Go bin to PATH (Homebrew Go installs here)
export PATH="${HOME}/go/bin:${PATH}"

TOOLBOX_CMD=()

# ── Preflight ─────────────────────────────────────────────────────────

if command -v toolbox &>/dev/null; then
    TOOLBOX_CMD=("toolbox")
elif command -v genai-toolbox &>/dev/null; then
    TOOLBOX_CMD=("genai-toolbox")
elif command -v npx &>/dev/null; then
    TOOLBOX_CMD=("npx" "-y" "@toolbox-sdk/server")
else
    echo "❌ Toolbox launcher not found in PATH."
    echo "   Install one of:"
    echo "   - go install github.com/googleapis/genai-toolbox@latest"
    echo "   - npm/npx with @toolbox-sdk/server"
    exit 1
fi

if [[ ! -f "${CORTEX_DB}" ]]; then
    echo "❌ CORTEX database not found at: ${CORTEX_DB}"
    echo "   Set CORTEX_DB env var or ensure ~/.cortex/cortex.db exists."
    exit 1
fi

if [[ ! -f "${TOOLS_FILE}" ]]; then
    echo "❌ tools.yaml not found at: ${TOOLS_FILE}"
    exit 1
fi

# ── Launch ────────────────────────────────────────────────────────────

echo "🧠 CORTEX MCP Toolbox — Knowledge Membrane"
echo "   DB:    ${CORTEX_DB}"
echo "   Profile: ${PROFILE}"
echo "   Mode:  ${MODE}"
if [[ "${MODE}" != "stdio" ]]; then
    echo "   Port:  ${PORT}"
fi
echo "   Tools: ${TOOLS_FILE}"
echo "   Cmd:   ${TOOLBOX_CMD[*]}"
echo ""

TOOLBOX_ARGS=(
    --tools-file "${TOOLS_FILE}"
)

if [[ "${MODE}" == "stdio" ]]; then
    TOOLBOX_ARGS+=(--stdio)
else
    TOOLBOX_ARGS+=(--port "${PORT}")
fi

exec "${TOOLBOX_CMD[@]}" \
    "${TOOLBOX_ARGS[@]}" \
    "$@"
