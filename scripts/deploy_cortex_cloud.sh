#!/bin/bash
# CORTEX CLOUD (Managed API + Stripe) Deployment
# Reality Level: C5-REAL
# Pre-requisites: Vercel CLI installed, Turso CLI installed, Stripe configured.

set -e

# Parse arguments
SKIP_DNS=false
for arg in "$@"; do
    case $arg in
        --skip-dns|--force)
            SKIP_DNS=true
            shift
            ;;
    esac
done

echo "============================================================"
echo "⚡ CORTEX CLOUD TOPOLOGY INIT (Managed API + Stripe)"
echo "============================================================"
echo "Reality Level: C5-REAL"
if [ "$SKIP_DNS" = true ]; then
    echo "Mode: DNS Binding Verification Bypass Enabled (--skip-dns/--force)"
fi

if ! command -v vercel &> /dev/null
then
    echo "[!] Error: vercel CLI could not be found. Install via 'npm i -g vercel'."
    exit 1
fi

echo "[1/4] Verifying Environment Configurations..."
if [ -z "$STRIPE_SECRET_KEY" ]; then
    echo "⚠️ Warning: STRIPE_SECRET_KEY is not set in environment."
fi

if [ -z "$TURSO_DATABASE_URL" ]; then
    echo "⚠️ Warning: TURSO_DATABASE_URL is not set. Cortex will default to local SQLite on serverless!"
fi

echo "[2/4] Validating Vercel Configuration..."
if [ ! -f "vercel.json" ]; then
    echo "[!] Error: vercel.json not found."
    exit 1
fi
echo "✓ vercel.json detected."

echo "[2.5/4] Validating Dynamic DNS Binding..."
DOMAINS=$(jq -r '.rewrites[].has[].value, .redirects[].has[].value' vercel.json 2>/dev/null | grep -v 'null' | sort -u || echo "cortexpersist.dev")

if [ -z "$DOMAINS" ]; then
    DOMAINS="cortexpersist.dev"
fi

for DOMAIN in $DOMAINS; do
    echo "  -> Inspecting $DOMAIN..."
    DOMAIN_STATUS=$(vercel domains inspect "$DOMAIN" 2>&1 || true)

    if echo "$DOMAIN_STATUS" | grep -q "WARN! This Domain is not configured properly"; then
        echo "[!] Anergy Detectada: El dominio $DOMAIN no está resolviendo hacia Vercel."
        
        # Extraer instrucciones dinámicas de Vercel (Registros A/CNAME requeridos)
        echo "$DOMAIN_STATUS" | grep -E "((Set the following record|Change your Domains's nameservers)|A |CNAME )" -A 1 | sed 's/^/    >> /'
        
        if [ "$SKIP_DNS" = true ]; then
            echo "  ⚠️ Warning: DNS config invalid, but continuing deployment due to --skip-dns/--force."
        else
            echo "[X] Abortando despliegue para evitar falsos positivos."
            exit 1
        fi
    else
        echo "  ✓ $DOMAIN validado."
    fi
done

echo "[3/4] Validating API Dependencies..."
if [ ! -f "api/requirements.txt" ]; then
    echo "[!] Error: api/requirements.txt not found."
    exit 1
fi
echo "✓ API requirements detected."

echo "[4/4] Deploying Cortex Cloud..."
echo "Executing: vercel --prod --archive=tgz"
vercel --prod --archive=tgz

echo "============================================================"
echo "✓ Cortex Cloud (Managed API) Deployment Initiated."
echo "============================================================"
