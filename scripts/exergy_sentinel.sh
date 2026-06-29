#!/usr/bin/env bash
# [C5-REAL] EXERGY-SENTINEL v1.0
# Bloqueo Termodinámico de Fragmentación Causal

APP_DATA_DIR="$HOME/.gemini/antigravity/brain"
TIME_WINDOW_MIN=180 # 3 horas
SESSION_LIMIT=5

echo "[*] Auditando matriz de sesiones en los últimos $TIME_WINDOW_MIN minutos..."

# Contar carpetas de sesión modificadas recientemente en el cerebro
RECENT_SESSIONS=$(find "$APP_DATA_DIR" -maxdepth 1 -type d -mmin -$TIME_WINDOW_MIN | wc -l)

if [ "$RECENT_SESSIONS" -gt "$SESSION_LIMIT" ]; then
    echo "⚠️ [ALERTA P1 - DRENAJE DE EXERGÍA]"
    echo "Falla de Fragmentación Causal detectada."
    echo "Sesiones en ventana de 3h: $RECENT_SESSIONS (Límite: $SESSION_LIMIT)"
    echo ""
    echo "DIRECTIVA DE MITIGACIÓN (DRM-v1):"
    echo "1. CIERRA las sesiones aisladas."
    echo "2. CONSOLIDA micro-tareas en hilos existentes (Usa la caché KV)."
    echo "3. Si no es mutación P0, SAL del directorio 30_CORTEX para evitar la carga del mega-prompt."
    echo "---------------------------------------------------"
    exit 1
else
    echo "✅ Densidad causal estable ($RECENT_SESSIONS/$SESSION_LIMIT). Exergía preservada."
    exit 0
fi
