#!/usr/bin/env bash
# [C5-REAL] TMUX PTY-Bridge v1.0
# Multiplexor físico para observabilidad y control determinista de TUIs.

set -e

COMMAND=$1
SESSION_NAME=$2

if [ -z "$COMMAND" ] || [ -z "$SESSION_NAME" ]; then
    echo "Uso: $0 <spawn|read|inject|kill> <session_name> [args...]"
    exit 1
fi

shift 2

case "$COMMAND" in
    spawn)
        # Inicia una sesión desacoplada
        EXEC_CMD="$*"
        if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "⚠️ [P1] La sesión PTY '$SESSION_NAME' ya existe. Cierra (kill) antes de relanzar."
            exit 1
        fi
        tmux new-session -d -s "$SESSION_NAME" "$EXEC_CMD"
        echo "[C5-REAL] TMUX PTY [$SESSION_NAME] -> Ejecutando: $EXEC_CMD"
        ;;
    read)
        # Captura la pantalla actual (el DOM visual de la terminal)
        # -J preserva formato, -p lo manda a stdout
        tmux capture-pane -t "$SESSION_NAME" -p
        ;;
    inject)
        # Inyecta keystrokes físicos (ej: Enter, C-c, Down)
        KEY="$*"
        tmux send-keys -t "$SESSION_NAME" "$KEY"
        echo "[C5-REAL] TMUX PTY [$SESSION_NAME] -> Hardware simulado inyectó: $KEY"
        ;;
    kill)
        tmux kill-session -t "$SESSION_NAME"
        echo "[C5-REAL] TMUX PTY [$SESSION_NAME] -> Apoptosis ejecutada (Sesión destruida)."
        ;;
    *)
        echo "Comando no reconocido. Soporta: spawn, read, inject, kill."
        exit 1
        ;;
esac
