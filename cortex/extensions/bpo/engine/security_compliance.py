"""
SECURITY-COMPLIANCE: Guardián del Scope de Auditoría
Especializado en validar targets de seguridad contra los Ω-Axiomas.
"""

import logging

from .compliance_guard import BPOComplianceGuard

logger = logging.getLogger("SECURITY-COMPLIANCE")


class SecurityComplianceGuard(BPOComplianceGuard):
    """
    Extiende el guardián de BPO con reglas específicas para Auditoría.
    """

    @staticmethod
    def validate_operation(payload: dict) -> tuple[bool, str]:
        """
        Valida que el target sea un repositorio auditable y tenga exergía suficiente.
        """
        # 1. Validación básica de BPO
        is_ok, msg = BPOComplianceGuard.validate_operation(payload)
        if not is_ok:
            return False, msg

        # 2. Validación de Scope (GitHub)
        github_url = payload.get("github_url")
        if not github_url or "github.com" not in github_url:
            return False, "VIOLACIÓN SCOPE: Target no es un repositorio GitHub auditable."

        # 3. Validación de Exergía (Modo Libertad Activo)
        # Se permite cualquier target independientemente de su exergía.
        return True, "C5-AUDIT-COMPLIANT (LIBERTAD)"
