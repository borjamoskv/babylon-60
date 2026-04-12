import asyncio
import hashlib
import json
import logging
import subprocess
import uuid
from datetime import datetime

from cortex.core.paths import resolve_native_binary

# Configuración de logging estilo CORTEX
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger("strike_orchestrator")

C = {
    "B": "\033[38;2;43;59;229m",
    "G": "\033[38;2;0;255;136m",
    "R": "\033[38;2;255;59;48m",
    "D": "\033[38;2;90;90;90m",
    "V": "\033[38;2;102;0;255m",
    "X": "\033[0m",
}

# --- NATIVE RECORDING BRIDGE ---
def record_native(role, content, url, exergy, is_conflict=False):
    """Direct record to native ledger via CLI to bypass Python DB lock issues."""
    try:
        subject_hash = hashlib.sha256(url.encode()).hexdigest()

        bin_path = resolve_native_binary("cortex-db", "CORTEX_NATIVE_DB_BIN", "CORTEX_DB_BIN")
        if bin_path is None:
            logger.error("Native binary cortex-db could not be resolved")
            return False

        event = {
            "id": f"evt_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "role": role,
            "content": content,
            "tenant_id": "cortex_default",
            "project_id": "bounty_hunting",
            "subject_hash": subject_hash,
            "is_conflict": is_conflict,
            "metadata_json": json.dumps({"bounty_url": url, "exergy": exergy})
        }
        
        subprocess.run([str(bin_path), "record", json.dumps(event)], check=True, capture_output=True)
        return True
    except (OSError, subprocess.SubprocessError, TypeError, ValueError) as e:
        logger.error("Native record failed: %s", e)
        return False

class StrikeOrchestrator:
    def __init__(self):
        self.rust_bin = resolve_native_binary(
            "cortex-strike",
            "CORTEX_NATIVE_STRIKE_BIN",
            "CORTEX_STRIKE_BIN",
        )

    async def execute_strike(self, source_name, title, html_url, exergy):
        """Orquesta la ejecución invocando cortex-strike (Nativo Rust)."""
        if self.rust_bin is None:
            logger.error("✗ cortex-strike NATIVE_BINARY_NOT_FOUND at %s", self.rust_bin)
            return {"decision": "ERROR"}

        try:
            # 1. Native VSA Collapse & Gate Decision (Silicon Truth)
            process = await asyncio.create_subprocess_exec(
                str(self.rust_bin), title, html_url, str(exergy),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            output = stdout.decode()
            report = {"decision": "ARCHIVE", "vsa_score": 0}
            
            # Print output up to the JSON line
            for line in output.split('\n'):
                if "STRIKE_REPORT_JSON:" in line:
                    json_str = line.split("STRIKE_REPORT_JSON:")[1].strip()
                    json_str = json_str.replace("\x1b[0m", "").strip()
                    report = json.loads(json_str)
                    break
                elif line.strip():
                    print(line)
            
            return report

        except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError) as e:
            logger.error("✗ NATIVE_CORE_ERROR: %s", e)
            return {"decision": "ERROR"}

async def run_scanner():
    logger.info("🚀 INITIALIZING NATIVE-STRIKE HUNTER (C5-REAL)...")
    
    targets = [
        {"source": "Immunefi", "title": "Arbitrary code execution in frontend utils", "url": "https://github.com/org/repo1/issues/10", "exergy": 2.5},
        {"source": "HackerOne", "title": "Reentrancy attack possible in withdraw() leading to drain", "url": "https://github.com/org/repo2/issues/45", "exergy": 9.8},
        {"source": "Bugcrowd", "title": "CSS overflow issue on mobile devices", "url": "https://github.com/org/repo3/issues/99", "exergy": 0.5},
        {"source": "Immunefi", "title": "Flash loan manipulation via unchecked oracle price", "url": "https://github.com/org/repo4/issues/102", "exergy": 8.5},
    ]

    orchestrator = StrikeOrchestrator()
    
    for t in targets:
        logger.info("\n📡 PROBING: %s", t["title"])
        report = await orchestrator.execute_strike(t['source'], t['title'], t['url'], t['exergy'])
        
        # RECORD TO NATIVE LEDGER (P0 PATH)
        role = "bounty" if report.get("decision") != "HOUND_ACTIVATE" else "intelligence"
        # Force some to be "intelligence" for UI visibility
        if t["exergy"] > 7.0:
            role = "intelligence"
        
        success = record_native(role, t['title'], t['url'], t['exergy'])
        if success:
            logger.info("✅ RECORDED to Native Ledger (Role: %s)", role)
        
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(run_scanner())
