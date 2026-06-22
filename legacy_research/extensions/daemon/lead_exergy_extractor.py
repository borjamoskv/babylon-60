# [C5-REAL] Exergy-Maximized
"""
Lead Exergy Extractor Daemon (C5-REAL)
Autómata físico diseñado para ejecutar cdp_agent.py de manera determinista,
respetando el protocolo Browser-CDP-Automation-OMEGA.
"""

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Lead-Exergy-Extractor")

class LeadExergyExtractor:
    """Motor C5-REAL para extracción determinista de leads invocando cdp_agent.py."""
    
    def __init__(self, target_match: str = "linkedin", payload_path: str = "legacy_research/extensions/daemon/extract_leads_payload.js"):
        self.target_match = target_match
        self.payload_path = Path(payload_path)
        self.extracted_leads: List[Dict] = []
        
    def _read_payload(self) -> str:
        """Lee el payload JS inmutable."""
        return self.payload_path.read_text(encoding="utf-8")

    def run_extraction(self) -> List[Dict]:
        """Ejecuta cdp_agent.py como subproceso bajo las reglas OMEGA."""
        logger.info(f"[C5-REAL] Iniciando extracción CDP apuntando a '{self.target_match}'...")
        js_payload = self._read_payload()
        
        # Path to cdp_agent.py in config config/skills/Browser-CDP-Automation-OMEGA/scripts/cdp_agent.py
        agent_path = Path.home() / ".gemini/config/skills/Browser-CDP-Automation-OMEGA/scripts/cdp_agent.py"
        
        if not agent_path.exists():
            logger.error(f"[C5-REAL] cdp_agent.py no encontrado en {agent_path}")
            return []
            
        cmd = [
            sys.executable,
            str(agent_path),
            "--url_match", self.target_match,
            "--js", js_payload
        ]
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = res.stdout.strip()
            if not output or output.startswith("ERR_"):
                logger.error(f"[C5-REAL] Error de ejecución en cdp_agent.py: {output or res.stderr}")
                return []
                
            # Parse leads JSON
            leads = json.loads(output)
            logger.info(f"[C5-REAL] Se recuperaron {len(leads)} leads desde cdp_agent.py.")
            return leads
        except Exception as e:
            logger.error(f"[C5-REAL] Fricción en subproceso: {e}")
            return []

    def persist_leads(self, leads: List[Dict]):
        """Persiste los leads extraídos en el Ledger o archivo de evidencia."""
        if not leads:
            return
            
        out_path = "legacy_research/extensions/daemon/extracted_leads_c5.jsonl"
        logger.info(f"[C5-REAL] Guardando {len(leads)} leads en {out_path}...")
        
        with open(out_path, "a", encoding="utf-8") as f:
            for lead in leads:
                f.write(json.dumps(lead) + "\n")
        logger.info("[C5-REAL] Consistencia y persistencia asegurada.")

    def run(self):
        """Ciclo principal."""
        leads = self.run_extraction()
        self.persist_leads(leads)

if __name__ == "__main__":
    extractor = LeadExergyExtractor()
    extractor.run()
