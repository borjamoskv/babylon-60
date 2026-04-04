#!/usr/bin/env bash
# CORTEX V6: Zero-Entropy Thermodynamic Purge
# Eliminates specific hanging processes (du -sh and python3 loops)

echo "∴ Initiating CORTEX Zero-Entropy Purge (Ω2)"

# Kill the target orphan processes causing I/O hang
pkill -f "du -sh /* 2>/dev/null"
pkill -f 'python3 -c "    width: 100%'

echo "◈ Thermal Noise Eliminated. Yield Restored."
