"""
BOUNTY-SCOUT: Explorador de Recompensas
Especializado en la adquisición de targets desde Immunefi (Unofficial) y GitHub.
"""

import asyncio
import logging
from collections.abc import Sequence

import httpx

from cortex.engine.shared_bus import SovereignSharedBus

from .scout_agent import BPOScoutAgent, Opportunity

logger = logging.getLogger("BOUNTY-SCOUT")

IMMUNEFI_PROJECTS_URL = "https://raw.githubusercontent.com/infosec-us-team/Immunefi-Bug-Bounty-Programs-Unofficial/main/projects.json"


class BountyScoutAgent(BPOScoutAgent):
    """
    Scout especializado en detectar programas de Bug Bounty y activos en scope.
    """

    async def run(self, targets: Sequence[str] | None = None):
        """
        Sobrescribe el loop principal para usar el feed dinámico de Immunefi.
        """
        logger.info("🔭 BOUNTY-SCOUT [%s] INICIALIZADO. Monitoreando Immunefi...", self.id)

        while self.active:
            try:
                programs = await self._fetch_immunefi_programs()
                opportunities = self._extract_opportunities(programs)

                high_exergy = [o for o in opportunities if o.exergy_potential > 0.7]
                logger.info(
                    "📡 Scan completo. Hallazgos: %d totales, %d High-Exergy.",
                    len(opportunities),
                    len(high_exergy),
                )

                for opp in high_exergy:
                    await self._report_alpha(opp)

            except Exception as e:
                logger.error("❌ Fallo en ciclo de adquisición: %s", e)

            # Ciclo de refresco (Ω₃: Ley del Ciclo)
            await asyncio.sleep(3600)  # Scan cada hora

    async def _fetch_immunefi_programs(self) -> list[dict]:
        """Adquisición O(1) del feed de proyectos."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(IMMUNEFI_PROJECTS_URL)
            response.raise_for_status()
            return response.json()

    def _extract_opportunities(self, programs: list[dict]) -> list[Opportunity]:
        """Transforma proyectos en oportunidades auditables."""
        opps = []
        for p in programs:
            # Filtrar activos con GitHub (Auditoría de código)
            github_urls = self._find_github_assets(p.get("assets", []))
            if not github_urls:
                # Reintentar con githubUrl del proyecto principal
                g_url = p.get("githubUrl")
                if g_url:
                    github_urls = [g_url]
                else:
                    continue

            # Heurística de Exergía basada en recompensas
            # El schema tiene 'rewards' como una lista de dicts con 'maxReward'
            rewards_list = p.get("rewards", [])
            max_r = 0
            if isinstance(rewards_list, list) and rewards_list:
                try:
                    max_r = max(
                        [r.get("maxReward", 0) for r in rewards_list if isinstance(r, dict)]
                    )
                except (ValueError, TypeError):
                    max_r = 0

            exergy = 0.5
            if max_r > 100000:
                exergy = 0.95
            elif max_r > 50000:
                exergy = 0.85
            elif max_r > 10000:
                exergy = 0.75

            for url in github_urls:
                opps.append(
                    Opportunity(
                        id=f"BOUNTY-{p.get('id', 'UNK')}",
                        source=f"Immunefi::{p.get('name', 'UNK')}",
                        exergy_potential=exergy,
                        payload={
                            "project_name": p.get("name"),
                            "github_url": url,
                            "max_reward": max_r,
                            "type": "SECURITY_AUDIT",
                        },
                    )
                )
        return opps

    def _find_github_assets(self, assets: list[dict]) -> list[str]:
        """Identifica URLs de GitHub en la lista de activos."""
        urls = []
        if not isinstance(assets, list):
            return urls

        for asset in assets:
            if not isinstance(asset, dict):
                continue
            url = asset.get("url") or asset.get("target") or ""
            if "github.com" in url:
                urls.append(url)
        return urls


if __name__ == "__main__":
    # Test local bypass
    async def test():
        class DummyManager:
            def __init__(self, bus: SovereignSharedBus):
                self.bus = bus

        bus = SovereignSharedBus(name="bounty_scout_test", create=True)
        scout = BountyScoutAgent("bounty-scout-test", DummyManager(bus))
        # Solo ejecutar una vez para test
        programs = await scout._fetch_immunefi_programs()
        opps = scout._extract_opportunities(programs)
        print(f"Sample Alpha: {opps[0] if opps else 'None'}")
        bus.close()
        bus.unlink()

    asyncio.run(test())
