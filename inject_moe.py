#!/usr/bin/env python3
import os
import sys

# Ensure local imports work
sys.path.insert(0, os.path.abspath('.'))

from babylon60.storage.ledger import EnterpriseAuditLedger
from babylon60.engine.autodidact_hott_engine import AutodidactHottEngine

def run_moe_injection():
    # Parse CORTEX_LOG_PATH
    log_path = os.getenv("CORTEX_LOG_PATH", "security_audit_log.jsonl")
    
    # Initialize Engine & Ledger
    ledger = EnterpriseAuditLedger(log_path=log_path)
    engine = AutodidactHottEngine(ledger)
    
    manifest_path = "AUTODIDACT_MOE.md"
    
    print(f"[*] Starting MoE Primitives Injection from {manifest_path}")
    
    # Check if manifest exists
    if not os.path.exists(manifest_path):
        print(f"[!] Error: {manifest_path} not found.")
        sys.exit(1)
        
    try:
        # Phase 1: Parse the manifest to extract Epistemic Types and Theorems
        ast_nodes = engine.parse_manifest(manifest_path)
        print(f"[+] Successfully extracted {len(ast_nodes)} MoE nodes.")
        
        # Phase 2: Inject primitives into the Topological Substrate
        for node in ast_nodes:
            print(f"   -> Injecting Node: {node.get('name', 'Unknown')}")
            # The engine evaluates the Type (Axiom, Theorem) and applies the Homotopy Type Theory validation
            engine.assert_node(node)
            
        print("[*] MoE primitive injection completed successfully.")
        
    except Exception as e:
        print(f"[!] Injection failed due to topological error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_moe_injection()
