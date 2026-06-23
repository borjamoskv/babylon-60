from babylon60.storage.wal import WriteAheadLog
import os
import subprocess
import logging

logger = logging.getLogger("babylon60.watchdog")

class SafeEventBatcher:
    async def ingest_event(self, event: dict):
        pass

class MitosisGatekeeper:
    """
    Cerrojo termodinámico (Regla L2.Ω3 y AGENTS.md Invariant 10).
    Impide la modificación del motor base sobre la rama principal activa.
    Fuerza a la inteligencia (MOSKV-1) a crear una rama 'auto/moskv1-mitosis-*'.
    """
    CORE_PATHS = ["babylon60/engine/", "cortex_core_rs/", ".so", ".db"]

    @classmethod
    def is_core_mutation(cls, filepath: str) -> bool:
        """Determina si la ruta apunta a infraestructura C5-REAL crítica."""
        for path in cls.CORE_PATHS:
            if path in filepath:
                return True
        return False

    @classmethod
    def enforce_branching(cls, filepath: str):
        """Si es mutación del núcleo y estamos en main, fuerza checkout a nueva rama."""
        if not cls.is_core_mutation(filepath):
            return

        try:
            current_branch = subprocess.check_output(
                ["git", "branch", "--show-current"], 
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except subprocess.CalledProcessError:
            return

        if current_branch == "main" or current_branch == "master":
            import time
            mitosis_branch = f"auto/moskv1-mitosis-{int(time.time())}"
            logger.warning(f"[WATCHDOG] Mutación crítica detectada en {filepath} sobre {current_branch}.")
            logger.warning(f"[WATCHDOG] Forzando Mitosis: creando rama aislada {mitosis_branch}.")
            subprocess.run(["git", "checkout", "-b", mitosis_branch], check=True)

class BootstrapWatchdog:
    def __init__(self):
        self.wal = WriteAheadLog()
        self.batcher = SafeEventBatcher()
        self.gatekeeper = MitosisGatekeeper()
    
    async def recover_and_resume(self):
        """
        Arranque seguro: recuperar eventos no sellados del WAL
        y re-inyectar en el batcher.
        """
        pending = await self.wal.recover_unsealed()
        for event in pending:
            await self.batcher.ingest_event(event)
        return pending
