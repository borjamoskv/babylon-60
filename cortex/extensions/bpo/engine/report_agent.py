"""
REPORT-AGENT: Agente de Cristalización de Reportes (Ω)
Especializado en transformar inteligencia técnica en reportes profesionales.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from .negotiator_agent import BPONegotiatorAgent


# Lazy loading of LLM to avoid global overhead
def get_llm():
    from langchain_google_genai import ChatGoogleGenerativeAI

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY NOT FOUND")
    return ChatGoogleGenerativeAI(
        model="gemini-3-flash", google_api_key=gemini_key, temperature=0.1
    )


logger = logging.getLogger("REPORT-AGENT")


class ReportAgent(BPONegotiatorAgent):
    """
    Agente L2 para la síntesis de reportes de auditoría.
    Suscribe a 'bpo:intelligence_crystallized' y genera el entregable final.
    """

    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.template_path = Path(
            "/Users/borjafernandezangulo/30_CORTEX/cortex/extensions/bpo/templates/template_audit.md"
        )
        self.reports_dir = Path("/Users/borjafernandezangulo/10_PROJECTS/Cortex-Persist/reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    async def start_listening(self):
        logger.info("📄 REPORT-AGENT [%s] LISTENING: Esperando Inteligencia...", self.id)

        # Nota: Usamos polling si listen() no está disponible en SovereignSharedBus nativo de SHM
        # Pero según negotiator_agent.py, existe un método listen() o similar.
        # Implementaremos un loop resiliente.
        last_index = -1
        while True:
            signals = self.bus.poll(last_index)
            for idx, signal in signals:
                last_index = idx
                if (
                    signal["payload"].get("event_type") == "bpo:intelligence_crystallized"
                    or signal.get("event_type") == "bpo:intelligence_crystallized"
                ):
                    # Normalización del payload según el emisor
                    payload = signal.get("payload", {})
                    if "payload" in payload:
                        payload = payload["payload"]  # Doble wrap

                    await self._synthesize_report(payload)

            await asyncio.sleep(1.0)

    async def _synthesize_report(self, data: dict):
        """
        Cristalización del reporte (C5-REVENUE).
        """
        project = data.get("project", "UNKNOWN")
        intel = data.get("intelligence_state", {})

        logger.info("🖋️  CRISTALIZANDO REPORTE PARA: %s", project)

        try:
            llm = get_llm()
            template = self.template_path.read_text()

            prompt = (
                "## CORTEX-REPORT-Ω PROMPT v1.0\n"
                f"Project: {project}\n"
                f"Verified Hypotheses: {json.dumps(intel.get('hypotheses'))}\n"
                f"Proof of Concept: {intel.get('proof_of_concept')}\n"
                f"Target Code:\n{intel.get('target_code')}\n\n"
                "Instructions:\n"
                "1. Fill the template with professional, high-impact language.\n"
                "2. Be technical and precise.\n"
                "3. Ensure the Reproducible PoC is clear.\n"
                f"Template:\n{template}"
            )
            resp = await asyncio.to_thread(llm.invoke, prompt)
            response_text = str(getattr(resp, "content", resp))

            # Metadatos estructurados para SUBMIT-Ω
            meta_block = (
                "---\n"
                f'platform: "Code4rena"\n'
                f'project: "{project}"\n'
                f'severity: "{intel.get("severity", "High")}"\n'
                f'vulnerability_id: "{data.get("opp_id", "UNK")}"\n'
                f'timestamp: "{datetime.now().isoformat()}"\n'
                "---\n\n"
            )
            report_content = meta_block + response_text

            # Persistencia
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = self.reports_dir / f"AUDIT_{project}_{ts}.md"
            report_file.write_text(report_content)

            logger.info("✅ REPORTE CRISTALIZADO: %s", report_file)

            # Emitir éxito de reporte
            await self.bus.emit(
                event_type="bpo:report_generated",
                payload={"project": project, "report_path": str(report_file)},
                source=self.id,
            )

        except Exception as e:
            logger.error("❌ Fallo en síntesis de reporte: %s", e)


if __name__ == "__main__":

    async def run_agent():
        agent = ReportAgent("report-omega-01")
        await agent.start_listening()

    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        pass
