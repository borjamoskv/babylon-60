import hashlib
import json
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)


class CortexTaintEngine:
    """
    Motor de atribución criptográfica para el Write-Path (SAGA-2).
    Asegura que toda mutación tenga un origen trazable antes de ser persistida.
    """

    @staticmethod
    def generate_taint(agent_id: str, session_id: str, payload: Any) -> str:
        """
        Genera el token CORTEX-TAINT (SAGA-2).
        Formato: taint:{agent_id}:{session_id}:{timestamp_iso8601}:{sha3_256_of_payload}
        """
        # ISO-8601 format without colons to avoid split errors, or standard.
        # But wait, standard is with colons. We use UTC 'Z'.
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Serialización determinista del payload para el hash
        try:
            payload_str = json.dumps(payload, sort_keys=True).encode("utf-8")
        except TypeError:
            payload_str = str(payload).encode("utf-8")

        payload_hash = hashlib.sha3_256(payload_str).hexdigest()

        taint_token = f"taint:{agent_id}:{session_id}:{timestamp}:{payload_hash}"
        logger.debug(f"[TAINT_ENGINE] Generado taint token: {taint_token}")
        return taint_token

    @staticmethod
    def verify_taint_presence(fact: dict[str, Any]) -> bool:
        """
        Verifica que un hecho tenga su marca criptográfica (SAGA-1 / SAGA-3).
        Debe ser invocado por el Persist-Validator antes de la escritura.
        """
        taint = fact.get("_cortex_taint")
        if not taint or not isinstance(taint, str):
            return False

        if not taint.startswith("taint:"):
            logger.warning(
                "[TAINT_ENGINE] Violación detectada: Payload sin firma o con firma corrupta."
            )
            return False

        parts = taint.split(":")
        # taint : agent_id : session_id : YYYY-MM-DDTHH : MM : SSZ : hash -> 7 parts usually
        if len(parts) < 5:
            return False

        return True

    @staticmethod
    def revoke_taint(fact: dict[str, Any]) -> dict[str, Any]:
        """
        Revoca la marca en caso de aborto del Saga (SAGA-2 reverse).
        Devuelve una copia del diccionario para mantener pureza.
        """
        fact_copy = dict(fact)
        if "_cortex_taint" in fact_copy:
            del fact_copy["_cortex_taint"]
            logger.info("[TAINT_ENGINE] Taint revocado correctamente.")
        return fact_copy


class SovereignValidator:
    """
    Validador determinista C5-REAL. Actúa como gatekeeper antes del Ledger.
    """

    @staticmethod
    def validate_mutation(mutation: dict[str, Any], agent_signature: str) -> bool:
        if not mutation:
            logger.error("FAILURE_SIGNATURE:EMPTY_MUTATION")
            return False

        if not CortexTaintEngine.verify_taint_presence(mutation):
            logger.error("FAILURE_SIGNATURE:UNSIGNED")
            return False

        # Validación estructural o de esquemas iría aquí
        return True
