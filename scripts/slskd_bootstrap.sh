#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# SLSKD BOOTSTRAP — CORTEX Soulseek Agent
# Instala slskd (binario .NET), configura credenciales, y arranca el daemon.
# Uso: bash scripts/slskd_bootstrap.sh <usuario_soulseek> <password_soulseek>
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

USER="${1:-}"
PASS="${2:-}"
API_KEY="cortex2026"
INSTALL_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.slskd"
CONFIG_FILE="$CONFIG_DIR/slskd.yml"
DOWNLOAD_DIR="$HOME/PROYECTOS/_ARCHIVE/Soulseek Downloads"

if [[ -z "$USER" || -z "$PASS" ]]; then
  echo "Uso: bash slskd_bootstrap.sh <usuario> <password>"
  exit 1
fi

echo "──────────────────────────────────────────"
echo "  CORTEX slskd Bootstrap"
echo "  Usuario: $USER"
echo "  Config:  $CONFIG_DIR"
echo "──────────────────────────────────────────"

# ─── 1. Instalar .NET si no existe ───────────────────────────────────────────
if ! command -v dotnet &>/dev/null; then
  echo "[1/4] Instalando .NET via Homebrew..."
  brew install dotnet
else
  echo "[1/4] .NET ya instalado: $(dotnet --version)"
fi

# ─── 2. Descargar slskd binary ───────────────────────────────────────────────
mkdir -p "$INSTALL_DIR"
SLSKD_BIN="$INSTALL_DIR/slskd"

if [[ ! -f "$SLSKD_BIN" ]]; then
  echo "[2/4] Descargando slskd (arm64)..."
  ARCH=$(uname -m)
  if [[ "$ARCH" == "arm64" ]]; then
    URL="https://github.com/slskd/slskd/releases/latest/download/slskd-osx-arm64.zip"
  else
    URL="https://github.com/slskd/slskd/releases/latest/download/slskd-osx-x64.zip"
  fi
  curl -Lo /tmp/slskd.zip "$URL"
  unzip -o /tmp/slskd.zip -d /tmp/slskd_extracted/
  mv /tmp/slskd_extracted/slskd "$SLSKD_BIN" 2>/dev/null || \
    find /tmp/slskd_extracted -name "slskd" -exec mv {} "$SLSKD_BIN" \;
  chmod +x "$SLSKD_BIN"
  rm -rf /tmp/slskd.zip /tmp/slskd_extracted
  echo "     ✓ slskd instalado en $SLSKD_BIN"
else
  echo "[2/4] slskd ya instalado: $SLSKD_BIN"
fi

# ─── 3. Configurar slskd.yml ─────────────────────────────────────────────────
mkdir -p "$CONFIG_DIR"
mkdir -p "$DOWNLOAD_DIR"

echo "[3/4] Generando $CONFIG_FILE..."
cat > "$CONFIG_FILE" <<EOF
soulseek:
  username: ${USER}
  password: ${PASS}
  listen_port: 50300
  description: "CORTEX Sovereign Music Agent"

directories:
  incomplete: ${DOWNLOAD_DIR}/incomplete
  downloads: ${DOWNLOAD_DIR}

shares:
  directories: []

web:
  port: 5030
  url_base: /
  content_path: wwwroot
  logging: false
  authentication:
    disabled: false
    username: cortex
    password: cortex2026
  api:
    keys:
      - ${API_KEY}

logger:
  disk:
    enabled: true
    path: ${CONFIG_DIR}/logs

flags:
  no_logo: true
  no_auth: false

options:
  diagnostic_level: "none"
EOF

echo "     ✓ Config generada"

# ─── 4. Arrancar daemon ──────────────────────────────────────────────────────
echo "[4/4] Arrancando slskd en background..."
export PATH="$INSTALL_DIR:$PATH"
nohup slskd --config "$CONFIG_FILE" > "$CONFIG_DIR/slskd.log" 2>&1 &
SLSKD_PID=$!
echo "     ✓ slskd PID=$SLSKD_PID"
echo "     Log: $CONFIG_DIR/slskd.log"

echo ""
echo "Esperando que el daemon arranque..."
sleep 6

# ─── Health check ────────────────────────────────────────────────────────────
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:5030/api/v0/application 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
  echo ""
  echo "✅ slskd OPERATIVO — http://localhost:5030"
  echo "   API Key: $API_KEY"
  echo ""
  echo "Lanzando GHOST_HUNT sobre 14 pistas..."
  cd "$(dirname "$0")"
  python3 soulseek_ghost_hunt.py --token "$API_KEY"
else
  echo ""
  echo "⚠️  slskd no responde aún (HTTP $HTTP_CODE). Comprueba el log:"
  echo "   tail -f $CONFIG_DIR/slskd.log"
  echo ""
  echo "Cuando esté activo, lanza manualmente:"
  echo "   python3 scripts/soulseek_ghost_hunt.py --token $API_KEY"
fi
