import os
import re
from pathlib import Path

# Dynamic home directory detection to prevent PII Bleed (Host Identity / Email)
HOME = Path.home()
WORKSPACE_ROOT = HOME / "30_CORTEX"
GLOBAL_SKILLS_ROOT = HOME / ".gemini" / "config" / "skills"
COLD_STORAGE_WORKFLOWS = HOME / "COLD_STORAGE" / "cortex-config" / "workflows"

# Target inventory file
INVENTORY_MD_PATH = WORKSPACE_ROOT / "docs" / "CORTEX_EXERGY_INVENTORY.md"

# Original table items provided by the user
RAW_ITEMS = [
    {"rank": 1, "name": "Deep-Research-SOTA-Edition-OMEGA", "type": "Skill", "path": "skills/Deep-Research-SOTA-Edition-OMEGA", "exergy": "97.8", "status": "Active JIT compiled"},
    {"rank": 2, "name": "accidental-data-loss-prevention", "type": "Skill", "path": "skills/accidental-data-loss-prevention", "exergy": "97.4", "status": "Active JIT compiled"},
    {"rank": 3, "name": "test_governor_catalog.py", "type": "Engine", "path": "engines/autopoiesis/test_governor_catalog.py", "exergy": "97.0", "status": "AST calculated (Optimized from 77.5)"},
    {"rank": 4, "name": "verification-before-completion", "type": "Skill", "path": "skills/verification-before-completion", "exergy": "97.0", "status": "Active JIT compiled"},
    {"rank": 5, "name": "Browser-CDP-Automation-OMEGA", "type": "Skill", "path": "skills/Browser-CDP-Automation-OMEGA", "exergy": "96.2", "status": "Active JIT compiled"},
    {"rank": 6, "name": "managing-python-dependencies", "type": "Skill", "path": "skills/managing-python-dependencies", "exergy": "96.2", "status": "Active JIT compiled"},
    {"rank": 7, "name": "Cortex-Research-Loop-OMEGA", "type": "Skill", "path": "skills/Cortex-Research-Loop-OMEGA", "exergy": "95.4", "status": "Active JIT compiled"},
    {"rank": 8, "name": "Agent-Paper-RedTeam-OMEGA", "type": "Skill", "path": "skills/Agent-Paper-RedTeam-OMEGA", "exergy": "95.0", "status": "Active JIT compiled"},
    {"rank": 9, "name": "antigravity-topology.md", "type": "Workflow", "path": "workflows/antigravity-topology.md", "exergy": "95.0", "status": "Heuristic parse"},
    {"rank": 10, "name": "Autodidact-Research-OMEGA", "type": "Skill", "path": "skills/Autodidact-Research-OMEGA", "exergy": "95.0", "status": "Active JIT compiled"},
    {"rank": 11, "name": "Crystallize-Knowledge-JIT", "type": "Skill", "path": "skills/Crystallize-Knowledge-JIT", "exergy": "95.0", "status": "Active JIT compiled"},
    {"rank": 12, "name": "Antigravity-Github-Omega", "type": "Skill", "path": "skills/Antigravity-Github-Omega", "exergy": "94.6", "status": "Active JIT compiled"},
    {"rank": 13, "name": "Autodidact-History-OMEGA", "type": "Skill", "path": "skills/Autodidact-History-OMEGA", "exergy": "94.6", "status": "Active JIT compiled"},
    {"rank": 14, "name": "Aesthetic-Foundry-Omega", "type": "Skill", "path": "skills/Aesthetic-Foundry-Omega", "exergy": "94.2", "status": "Active JIT compiled"},
    {"rank": 15, "name": "Apollo-Autodidact-OMEGA", "type": "Skill", "path": "skills/Apollo-Autodidact-OMEGA", "exergy": "94.2", "status": "Active JIT compiled"},
    {"rank": 16, "name": "Cortex-Live-Broadcaster", "type": "Skill", "path": "skills/Cortex-Live-Broadcaster", "exergy": "94.2", "status": "Active JIT compiled"},
    {"rank": 17, "name": "karpathy-recursive-swarm.md", "type": "Workflow", "path": "workflows/karpathy-recursive-swarm.md", "exergy": "94.1", "status": "Heuristic parse"},
    {"rank": 18, "name": "Apollo-Extractor-OMEGA", "type": "Skill", "path": "skills/Apollo-Extractor-OMEGA", "exergy": "93.8", "status": "Active JIT compiled"},
    {"rank": 19, "name": "Autodidact-21EDO-OMEGA", "type": "Skill", "path": "skills/Autodidact-21EDO-OMEGA", "exergy": "93.8", "status": "Active JIT compiled"},
    {"rank": 20, "name": "Autonomous-Audit-OMEGA", "type": "Skill", "path": "skills/Autonomous-Audit-OMEGA", "exergy": "93.8", "status": "Active JIT compiled"},
    {"rank": 21, "name": "borja-moskv-ultrathink", "type": "Skill", "path": "skills/borja-moskv-ultrathink", "exergy": "93.8", "status": "Active JIT compiled"},
    {"rank": 22, "name": "Ouroboros-Strike-OMEGA", "type": "Skill", "path": "skills/Ouroboros-Strike-OMEGA", "exergy": "93.8", "status": "Active JIT compiled"},
    {"rank": 23, "name": "Python-Extractor-OMEGA", "type": "Skill", "path": "skills/Python-Extractor-OMEGA", "exergy": "93.8", "status": "Active JIT compiled"},
    {"rank": 24, "name": "agent-memory-patterns", "type": "Skill", "path": "skills/agent-memory-patterns", "exergy": "93.4", "status": "TOMBSTONED (Death Protocol Executed)"},
    {"rank": 25, "name": "Episodic-Memory-OMEGA", "type": "Skill", "path": "skills/Episodic-Memory-OMEGA", "exergy": "93.4", "status": "Active JIT compiled"},
    {"rank": 26, "name": "Estado-Del-Arte-OMEGA", "type": "Skill", "path": "skills/Estado-Del-Arte-OMEGA", "exergy": "93.4", "status": "Active JIT compiled"},
    {"rank": 27, "name": "picasso-synergies.md", "type": "Workflow", "path": "workflows/picasso-synergies.md", "exergy": "93.1", "status": "Heuristic parse"},
    {"rank": 28, "name": "browser-hijack-guard", "type": "Skill", "path": "skills/browser-hijack-guard", "exergy": "93.0", "status": "Active JIT compiled"},
    {"rank": 29, "name": "Exergy-Engine-OMEGA", "type": "Skill", "path": "skills/Exergy-Engine-OMEGA", "exergy": "92.6", "status": "Active JIT compiled"},
    {"rank": 30, "name": "filologa-de-combate", "type": "Skill", "path": "skills/filologa-de-combate", "exergy": "92.6", "status": "Active JIT compiled"},
    {"rank": 31, "name": "ouroboros-settlement.md", "type": "Workflow", "path": "workflows/ouroboros-settlement.md", "exergy": "92.6", "status": "Heuristic parse"},
    {"rank": 32, "name": "Alpha-Target-OMEGA", "type": "Skill", "path": "skills/Alpha-Target-OMEGA", "exergy": "92.2", "status": "Active JIT compiled"},
    {"rank": 33, "name": "API-Provider-OMEGA", "type": "Skill", "path": "skills/API-Provider-OMEGA", "exergy": "92.2", "status": "Active JIT compiled"},
    {"rank": 34, "name": "API-Sentinel-OMEGA", "type": "Skill", "path": "skills/API-Sentinel-OMEGA", "exergy": "92.2", "status": "TOMBSTONED (Death Protocol Executed)"},
    {"rank": 35, "name": "memory-bridge.md", "type": "Workflow", "path": "workflows/memory-bridge.md", "exergy": "92.2", "status": "Heuristic parse"},
    {"rank": 36, "name": "ouroboros-infinity", "type": "Skill", "path": "skills/ouroboros-infinity", "exergy": "92.2", "status": "Active JIT compiled"},
    {"rank": 37, "name": "UI-Mechanisms-Rule", "type": "Skill", "path": "skills/UI-Mechanisms-Rule", "exergy": "92.2", "status": "TOMBSTONED (Death Protocol Executed)"},
    {"rank": 38, "name": "sovereign_bridge.py", "type": "Engine", "path": "engines/sovereign_bridge.py", "exergy": "92.0", "status": "AST calculated (Optimized from 77.9)"},
    {"rank": 39, "name": "codebase-analysis", "type": "Skill", "path": "skills/codebase-analysis", "exergy": "91.8", "status": "Active JIT compiled"},
    {"rank": 40, "name": "Mac-Control-OMEGA", "type": "Skill", "path": "skills/Mac-Control-OMEGA", "exergy": "91.8", "status": "Active JIT compiled"},
    {"rank": 41, "name": "performance-forge", "type": "Skill", "path": "skills/performance-forge", "exergy": "91.8", "status": "Active JIT compiled"},
    {"rank": 42, "name": "refactor-patterns", "type": "Skill", "path": "skills/refactor-patterns", "exergy": "91.8", "status": "Active JIT compiled"},
    {"rank": 43, "name": "MOLTBOOK-SIEGE-V2.md", "type": "Workflow", "path": "workflows/MOLTBOOK-SIEGE-V2.md", "exergy": "91.7", "status": "Heuristic parse"},
    {"rank": 44, "name": "program-social-swarm.md", "type": "Workflow", "path": "workflows/program-social-swarm.md", "exergy": "91.7", "status": "Heuristic parse"},
    {"rank": 45, "name": "browser-subagent", "type": "Skill", "path": "skills/browser-subagent", "exergy": "91.4", "status": "TOMBSTONED (Death Protocol Executed)"},
    {"rank": 46, "name": "chimera-protocol", "type": "Skill", "path": "skills/chimera-protocol", "exergy": "91.4", "status": "Active JIT compiled"},
    {"rank": 47, "name": "agent-architect", "type": "Skill", "path": "skills/agent-architect", "exergy": "91.0", "status": "Active JIT compiled"},
    {"rank": 48, "name": "decision-critic", "type": "Skill", "path": "skills/decision-critic", "exergy": "91.0", "status": "TOMBSTONED (Death Protocol Executed)"},
    {"rank": 49, "name": "episodic-memory", "type": "Skill", "path": "skills/episodic-memory", "exergy": "91.0", "status": "TOMBSTONED (Death Protocol Executed)"},
    {"rank": 50, "name": "moskv-aesthetic", "type": "Skill", "path": "skills/moskv-aesthetic", "exergy": "91.0", "status": "TOMBSTONED (Death Protocol Executed)"},
    {"rank": 51, "name": "P2P-Comms-OMEGA", "type": "Skill", "path": "skills/P2P-Comms-OMEGA", "exergy": "91.0", "status": "Active JIT compiled"},
    {"rank": 52, "name": "C5-DEATH-OMEGA", "type": "Skill", "path": "skills/C5-DEATH-OMEGA", "exergy": "90.6", "status": "Active JIT compiled"},
    {"rank": 53, "name": "health-check", "type": "Skill", "path": "skills/health-check", "exergy": "89.8", "status": "Active JIT compiled"},
    {"rank": 54, "name": "skill-repair", "type": "Skill", "path": "skills/skill-repair", "exergy": "89.8", "status": "TOMBSTONED (Death Protocol Executed)"},
    {"rank": 55, "name": "agente-sota", "type": "Skill", "path": "skills/agente-sota", "exergy": "89.4", "status": "TOMBSTONED (Death Protocol Executed)"},
    {"rank": 56, "name": "find-skills", "type": "Skill", "path": "skills/find-skills", "exergy": "89.4", "status": "Active JIT compiled"},
    {"rank": 57, "name": "swift-forge", "type": "Skill", "path": "skills/swift-forge", "exergy": "89.4", "status": "Active JIT compiled"},
    {"rank": 58, "name": "fast_fix_and_test.md", "type": "Workflow", "path": "workflows/fast_fix_and_test.md", "exergy": "89.2", "status": "Heuristic parse"},
    {"rank": 59, "name": "Sortu-APEX", "type": "Skill", "path": "skills/Sortu-APEX", "exergy": "89.0", "status": "Active JIT compiled"},
    {"rank": 60, "name": "web-forge", "type": "Skill", "path": "skills/web-forge", "exergy": "88.6", "status": "TOMBSTONED (Death Protocol Executed)"},
    {"rank": 61, "name": "webs-plus", "type": "Skill", "path": "skills/webs-plus", "exergy": "88.6", "status": "Active JIT compiled"},
    {"rank": 62, "name": "session-close.md", "type": "Workflow", "path": "workflows/session-close.md", "exergy": "88.4", "status": "Heuristic parse"},
    {"rank": 63, "name": "alphazero-autodidact-omega.md", "type": "Workflow", "path": "workflows/alphazero-autodidact-omega.md", "exergy": "88.2", "status": "Heuristic parse"},
    {"rank": 64, "name": "alphazero-training-loop.md", "type": "Workflow", "path": "workflows/alphazero-training-loop.md", "exergy": "87.9", "status": "Heuristic parse"},
    {"rank": 65, "name": "dios", "type": "Skill", "path": "skills/dios", "exergy": "86.6", "status": "TOMBSTONED (Death Protocol Executed)"},
    {"rank": 66, "name": "ouroboros_mcp_guard.py", "type": "Script", "path": "scripts/ouroboros_mcp_guard.py", "exergy": "82.0", "status": "AST calculated (Optimized from 60.0)"},
    {"rank": 67, "name": "kardashev-omega.md", "type": "Workflow", "path": "workflows/kardashev-omega.md", "exergy": "81.6", "status": "Heuristic parse"},
    {"rank": 68, "name": "create-sovereign-skill.md", "type": "Workflow", "path": "workflows/create-sovereign-skill.md", "exergy": "81.4", "status": "Heuristic parse"},
    {"rank": 69, "name": "autodidact.md", "type": "Workflow", "path": "workflows/autodidact.md", "exergy": "80.3", "status": "Heuristic parse"},
    {"rank": 70, "name": "cortex-moltbook-strike.md", "type": "Workflow", "path": "workflows/cortex-moltbook-strike.md", "exergy": "79.2", "status": "Heuristic parse"},
    {"rank": 71, "name": "cortex_entropy_purge.py", "type": "Script", "path": "scripts/cortex_entropy_purge.py", "exergy": "79.0", "status": "AST calculated (Optimized from 53.0)"},
    {"rank": 72, "name": "grammy-electronic.md", "type": "Workflow", "path": "workflows/grammy-electronic.md", "exergy": "78.6", "status": "Heuristic parse"},
    {"rank": 73, "name": "ghost-hunt.md", "type": "Workflow", "path": "workflows/ghost-hunt.md", "exergy": "78.5", "status": "Heuristic parse"},
    {"rank": 74, "name": "tesseract-omega.md", "type": "Workflow", "path": "workflows/tesseract-omega.md", "exergy": "77.2", "status": "Heuristic parse"},
    {"rank": 75, "name": "omega_healer.py", "type": "Script", "path": "scripts/omega_healer.py", "exergy": "77.0", "status": "AST calculated"},
    {"rank": 76, "name": "blackboard_cli.py", "type": "Engine", "path": "engines/blackboard/blackboard_cli.py", "exergy": "76.0", "status": "AST calculated (Optimized from 52.8)"},
    {"rank": 77, "name": "cortex_router.py", "type": "Script", "path": "scripts/cortex_router.py", "exergy": "75.0", "status": "AST calculated (Optimized from 73.0)"},
    {"rank": 78, "name": "lea_omega_purge.sh", "type": "Script", "path": "scripts/lea_omega_purge.sh", "exergy": "75.0", "status": "Heuristic parse"},
    {"rank": 79, "name": "kimi-invoke.md", "type": "Workflow", "path": "workflows/kimi-invoke.md", "exergy": "74.3", "status": "Heuristic parse"},
    {"rank": 80, "name": "session-boot.md", "type": "Workflow", "path": "workflows/session-boot.md", "exergy": "73.0", "status": "Heuristic parse"},
    {"rank": 81, "name": "antigravity.md", "type": "Workflow", "path": "workflows/antigravity.md", "exergy": "72.9", "status": "Heuristic parse"},
    {"rank": 82, "name": "promote_from_playground.py", "type": "Script", "path": "scripts/promote_from_playground.py", "exergy": "70.0", "status": "AST calculated (Optimized from 26.0)"},
    {"rank": 83, "name": "build_knowledge_index.py", "type": "Script", "path": "scripts/build_knowledge_index.py", "exergy": "69.0", "status": "AST calculated (Optimized from 31.0)"},
    {"rank": 84, "name": "equilibrium_engine_v3.py", "type": "Engine", "path": "engines/equilibrium_engine_v3.py", "exergy": "67.0", "status": "AST calculated (Optimized from 60.0)"},
    {"rank": 85, "name": "sovereign-prompt.md", "type": "Workflow", "path": "workflows/sovereign-prompt.md", "exergy": "66.7", "status": "Heuristic parse"},
    {"rank": 86, "name": "ultra_power_prompt.md", "type": "Workflow", "path": "workflows/ultra_power_prompt.md", "exergy": "64.0", "status": "Heuristic parse"},
    {"rank": 87, "name": "legion_swarm_specialists.md", "type": "Agent", "path": "agents/workflows/legion_swarm_specialists.md", "exergy": "63.6", "status": "Heuristic parse"},
    {"rank": 88, "name": "documentar.md", "type": "Workflow", "path": "workflows/documentar.md", "exergy": "62.5", "status": "Heuristic parse"},
    {"rank": 89, "name": "analyze.py", "type": "Engine", "path": "engines/sonic-analyzer/analyze.py", "exergy": "62.0", "status": "AST calculated (Optimized from 32.0)"},
    {"rank": 90, "name": "kimi-hybrid.md", "type": "Workflow", "path": "workflows/kimi-hybrid.md", "exergy": "60.9", "status": "Heuristic parse"},
    {"rank": 91, "name": "aleph-omega.md", "type": "Workflow", "path": "workflows/aleph-omega.md", "exergy": "58.7", "status": "Heuristic parse"},
    {"rank": 92, "name": "anamnesis_engine.py", "type": "Engine", "path": "engines/anamnesis/anamnesis_engine.py", "exergy": "58.0", "status": "AST calculated (Optimized from 44.7)"},
    {"rank": 93, "name": "antigravity-lifecycle.md", "type": "Workflow", "path": "workflows/antigravity-lifecycle.md", "exergy": "50.0", "status": "Heuristic parse"},
    {"rank": 94, "name": "assimilate.md", "type": "Workflow", "path": "workflows/assimilate.md", "exergy": "50.0", "status": "Heuristic parse"},
    {"rank": 95, "name": "auto-allow-execution.md", "type": "Workflow", "path": "workflows/auto-allow-execution.md", "exergy": "50.0", "status": "Heuristic parse"},
    {"rank": 96, "name": "kinetic-intelligence.md", "type": "Workflow", "path": "workflows/kinetic-intelligence.md", "exergy": "50.0", "status": "Heuristic parse"},
    {"rank": 97, "name": "kv-aware-routing-omega.md", "type": "Workflow", "path": "workflows/kv-aware-routing-omega.md", "exergy": "50.0", "status": "Heuristic parse"},
    {"rank": 98, "name": "playground-promotion.md", "type": "Workflow", "path": "workflows/playground-promotion.md", "exergy": "50.0", "status": "Heuristic parse"},
    {"rank": 99, "name": "program-closer-agent.md", "type": "Workflow", "path": "workflows/program-closer-agent.md", "exergy": "50.0", "status": "Heuristic parse"},
    {"rank": 100, "name": "RFC-CORTEX-NATIVE-AI.md", "type": "Workflow", "path": "workflows/RFC-CORTEX-NATIVE-AI.md", "exergy": "50.0", "status": "Heuristic parse"},
    {"rank": 101, "name": "system-card-tactical-read.md", "type": "Workflow", "path": "workflows/system-card-tactical-read.md", "exergy": "50.0", "status": "Heuristic parse"},
    {"rank": 102, "name": "night_shift.py", "type": "Engine", "path": "engines/night-shift/night_shift.py", "exergy": "46.0", "status": "AST calculated (Optimized from 38.0)"},
    {"rank": 103, "name": "governor.py", "type": "Engine", "path": "engines/autopoiesis/governor.py", "exergy": "44.0", "status": "AST calculated (Optimized from 9.0)"}
]

def find_absolute_path(name, component_type, original_path):
    # Try global skills
    if component_type == "Skill":
        # Check in GLOBAL_SKILLS_ROOT
        path_opt = GLOBAL_SKILLS_ROOT / name
        if path_opt.exists() and (path_opt / "SKILL.md").exists():
            return path_opt / "SKILL.md"
        # Check inside GLOBAL_SKILLS_ROOT/.tombstone
        path_tomb = GLOBAL_SKILLS_ROOT / ".tombstone" / name
        if path_tomb.exists() and (path_tomb / "SKILL.md").exists():
            return path_tomb / "SKILL.md"
        # Check inside GLOBAL_SKILLS_ROOT/_archived
        path_arch = GLOBAL_SKILLS_ROOT / "_archived" / name
        if path_arch.exists() and (path_arch / "SKILL.md").exists():
            return path_arch / "SKILL.md"
        # Check inside WORKSPACE_ROOT/skills
        path_local = WORKSPACE_ROOT / "skills" / name
        if path_local.exists() and (path_local / "SKILL.md").exists():
            return path_local / "SKILL.md"
        
    # Try scripts
    if component_type == "Script":
        # Check in WORKSPACE_ROOT/scripts
        basename = os.path.basename(original_path)
        path_opt = WORKSPACE_ROOT / "scripts" / basename
        if path_opt.exists():
            return path_opt
        
    # Try workflows
    if component_type == "Workflow":
        basename = os.path.basename(original_path)
        # Check in WORKSPACE_ROOT/.agent/workflows
        path_opt = WORKSPACE_ROOT / ".agent" / "workflows" / basename
        if path_opt.exists():
            return path_opt
        # Check in WORKSPACE_ROOT/.agents/workflows
        path_opt2 = WORKSPACE_ROOT / ".agents" / "workflows" / basename
        if path_opt2.exists():
            return path_opt2
        # Check in COLD_STORAGE_WORKFLOWS
        path_cold = COLD_STORAGE_WORKFLOWS / basename
        if path_cold.exists():
            return path_cold
            
    # Try engines
    if component_type == "Engine":
        basename = os.path.basename(original_path)
        # Look recursively in WORKSPACE_ROOT/babylon60/engine or WORKSPACE_ROOT
        for root, dirs, files in os.walk(str(WORKSPACE_ROOT)):
            if basename in files:
                return Path(root) / basename
                
    return None

def build_inventory_markdown():
    lines = []
    lines.append("# CORTEX Ecosystem Master Exergy Inventory")
    lines.append("")
    lines.append("This document represents the consolidated thermodynamic exergy ranking of all SKILLS, SCRIPTS, ENGINES, and WORKFLOWS in the CORTEX ecosystem.")
    lines.append("")
    lines.append("* **Reality Level**: C5-REAL (Verifiable local AST diagnostics, JIT registers, and code-block telemetry)")
    lines.append(f"* **Date**: 2026-06-30")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Justification Logic")
    lines.append("")
    lines.append("```yaml")
    lines.append("Claim: exergy_score = 100.0 - (10.0 * entropy_score)")
    lines.append("Proof: { Base: \"AST complexity metrics: McCabe(0.3) + Nesting(0.2) + DeadCode(0.3) + UnusedImports(0.2)\", Range: [11.0, 97.0], Confidence: C5 }")
    lines.append("```")
    lines.append("")
    lines.append("```yaml")
    lines.append("Claim: exergy_score = 50.0 + (code_block_lines / total_lines * 50.0)")
    lines.append("Proof: { Base: \"Ratio of executable markdown blocks vs descriptive prose\", Range: [50.0, 95.0], Confidence: C4 }")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Master Inventory Table")
    lines.append("")
    lines.append("| Rank | Component Name | Type | Primary File Path / Identifier | Exergy | Status / Notes |")
    lines.append("|---|---|---|---|---|---|")
    
    for item in RAW_ITEMS:
        rank = item["rank"]
        name = item["name"]
        ctype = item["type"]
        opath = item["path"]
        exergy = item["exergy"]
        status = item["status"]
        
        abs_path = find_absolute_path(name, ctype, opath)
        if abs_path:
            # Prevent exposing local username to avoid PII bleed checks
            relative_user_path = str(abs_path).replace(str(HOME), "~")
            link_path = f"[{opath}](file://{relative_user_path})"
        else:
            link_path = f"`{opath}`"
            
        lines.append(f"| {rank} | `{name}` | {ctype} | {link_path} | **{exergy}** | {status} |")
        
    lines.append("")
    lines.append("## Component Core Descriptions & Practical Use Cases")
    lines.append("")
    lines.append("This section maps the architectural roles and concrete, practical use cases of key components in the CORTEX ecosystem.")
    lines.append("")
    lines.append("### 1. Sovereign Skills (OMEGA Series)")
    lines.append("* **`Deep-Research-SOTA-Edition-OMEGA`** (`skills/Deep-Research-SOTA-Edition-OMEGA`): Runs deep-dive investigation into technical domains, paper databases, and code implementations.")
    lines.append("  * *Use Case*: Running a broad SOTA review to extract design patterns for a distributed vector index before implementing it.")
    lines.append("* **`accidental-data-loss-prevention`** (`skills/accidental-data-loss-prevention`): Safeguard middleware that intercepts and blocks destructive database commands (`DROP`, `TRUNCATE`, `DELETE *`), demanding explicit validation.")
    lines.append("  * *Use Case*: Blocking automatic migration scripts from accidentally wiping production databases during developer-driven JIT updates.")
    lines.append("* **`verification-before-completion`** (`skills/verification-before-completion`): Validation gate that forces lint checks, AST scans, and unit test execution before allowing a task completion status.")
    lines.append("  * *Use Case*: Automatically running pre-commit checks on a branch before finalizing a feature merge.")
    lines.append("* **`Browser-CDP-Automation-OMEGA`** (`skills/Browser-CDP-Automation-OMEGA`): Zero-fragility Chrome DevTools Protocol (CDP) orchestrator.")
    lines.append("  * *Use Case*: Crawling dynamically rendered, JS-heavy web dashboards to extract metrics without relying on easily-broken DOM selectors.")
    lines.append("* **`managing-python-dependencies`** (`skills/managing-python-dependencies`): Isolated sandbox builder that configures custom python virtualenvs and JIT-installs dependencies safely.")
    lines.append("  * *Use Case*: Spawning a task-specific environment with custom packages without altering the developer's global python paths.")
    lines.append("* **`Agent-Paper-RedTeam-OMEGA`** (`skills/Agent-Paper-RedTeam-OMEGA`): Adversarial review bot that scans design specifications and papers for flaws, vulnerabilities, and exaggerated claims.")
    lines.append("  * *Use Case*: Subjecting a new microservice architecture proposal to automated adversarial security and capacity checks.")
    lines.append("* **`Aesthetic-Foundry-Omega`** (`skills/Aesthetic-Foundry-Omega`): Sovereign CSS visual design framework implementing the \"Industrial Noir 2026\" aesthetic.")
    lines.append("  * *Use Case*: Instantly applying high-fidelity typography, color schemes (#0A0A0A / #2B3BE5), and fluid grid behaviors to generated web UI prototypes.")
    lines.append("")
    lines.append("### 2. Core Engines")
    lines.append("* **`governor.py`** (`engines/autopoiesis/governor.py`): Autopoietic engine that governs active subagents, limiting resource footprints (token limits, thread counts, RAM bounds).")
    lines.append("  * *Use Case*: Preventing runaway recursive agent loops from consuming excess API credits or crashing developer systems.")
    lines.append("* **`night_shift.py`** (`engines/night-shift/night_shift.py`): Sandboxed asynchronous task queue runner that executes background suites overnight and outputs a token-efficient compact morning report.")
    lines.append("  * *Use Case*: Running long integration tests and code-quality scans after-hours, leaving a complete diagnostic report ready for developer inspection in the morning.")
    lines.append("* **`analyze.py`** (`engines/sonic-analyzer/analyze.py`): Static analyzer measuring McCabe complexity, nesting depth, dead code, and unused imports to output thermodynamic exergy ratings.")
    lines.append("  * *Use Case*: Integrating with CI/CD gates to block code merges that push complexity metrics beyond strict limits.")
    lines.append("* **`anamnesis_engine.py`** (`engines/anamnesis/anamnesis_engine.py`): Epistemic query and history routing database tracking context traces across sessions.")
    lines.append("  * *Use Case*: Retaining knowledge of why certain architectural compromises were made during a session 10 days ago.")
    lines.append("")
    lines.append("### 3. Key Scripts")
    lines.append("* **`promote_from_playground.py`** (`scripts/promote_from_playground.py`): Command-line pipeline that promotes validated playground drafts to permanent ecosystem directories.")
    lines.append("  * *Use Case*: Automating the transition of a new skill prototype into the core registry once it passes all unit test criteria.")
    lines.append("* **`build_knowledge_index.py`** (`scripts/build_knowledge_index.py`): Markdown and source codebase indexer that constructs context indices.")
    lines.append("  * *Use Case*: Re-indexing local wikis and documentation folders periodically to speed up agent query context lookup times.")
    lines.append("* **`cortex_entropy_purge.py`** (`scripts/cortex_entropy_purge.py`): Daemon script that runs in the background to purge session data in the `brain/` temporary folders older than 2 days.")
    lines.append("  * *Use Case*: Reclaiming disk space on developer machines by clearing temporary logs and conversational state databases.")
    lines.append("* **`omega_healer.py`** (`scripts/omega_healer.py`): JIT repair script that automatically fixes broken import headers, syntax mismatches, and types in generated code.")
    lines.append("  * *Use Case*: Fixing a broken import statement during compilation errors in an automated build task.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Verification Matrices")
    lines.append("")
    lines.append("### Primitives (`prims`)")
    lines.append("1. **Exergy Gradient**: The rate of useful work production relative to total resource consumption.")
    lines.append("2. **Thermodynamic Lane**: A designated continuous execution path with strict resource, thermal, and scheduling constraints.")
    lines.append("3. **AST Isomorphism**: Structural equivalence of Abstract Syntax Trees, ignoring naming mutations.")
    lines.append("4. **C5-REAL Validation**: Cryptographically checked, deterministic execution output.")
    lines.append("5. **Consensus Quorum**: Byzantine fault tolerant consensus across modular agents.")
    lines.append("")
    lines.append("### Invariants (`invt`)")
    lines.append("1. **Absolute Attributability**: Every fact transaction must carry a cryptographically signed attribution signature.")
    lines.append("2. **No Silent Death**: Background workers must catch and handle exceptions rather than terminating without trace.")
    lines.append("3. **Single State Authority**: Persistent state mutations must go through the unified Saga write contract.")
    lines.append("")
    lines.append("### Anti-Patterns (`antip`)")
    lines.append("1. **Limerence Loop**: Spending tokens on redundant iterations without updating state or files.")
    lines.append("2. **Context Leakage**: Merging metadata or credentials across tenant-isolated read-write boundaries.")
    lines.append("3. **Prose Padding**: Decorative conversational wrappers enclosing factual outputs.")
    lines.append("")
    lines.append("### Redundancies (`redun`)")
    lines.append("1. **Fallback Consensus**: Multi-model routing when primary cognitive engines encounter execution drift.")
    lines.append("2. **Ledger Replication**: Replicating ledger records across local and network-attached trust engines.")
    lines.append("")
    lines.append("### Adversarial Vectors (`reda`)")
    lines.append("1. **Isomorphic Bypass**: Injecting structurally identical malicious payloads via semantic transformations.")
    lines.append("2. **Deadlock Induction**: Generating concurrent read-write locks designed to freeze SQLite event loops.")
    lines.append("")
    lines.append("`SYS_ID borjamoskv`")
    
    return "\n".join(lines) + "\n"

if __name__ == "__main__":
    content = build_inventory_markdown()
    INVENTORY_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY_MD_PATH.write_text(content, encoding="utf-8")
    print(f"C5-REAL: Inventory compiled and written to {INVENTORY_MD_PATH}")
