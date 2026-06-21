# [C5-REAL] Exergy-Maximized
import logging
import threading
from collections.abc import Callable
from typing import Any, Protocol

logger = logging.getLogger(__name__)

class RegistryLockError(Exception):
    """Raised when attempting to modify a frozen registry."""
    pass

class SkillResolutionError(Exception):
    """Raised when a skill cannot be resolved deterministically."""
    pass

class SkillProtocol(Protocol):
    """C5-REAL strict IO contract for any sovereign skill."""
    def execute(self, event: Any) -> dict[str, Any]: ...

_REGISTRY: dict[str, type[SkillProtocol]] = {}
_REGISTRY_LOCK = threading.RLock()
_FROZEN = False

def freeze_registry() -> None:
    """Seal the registry (Immutable Runtime)."""
    global _FROZEN
    with _REGISTRY_LOCK:
        _FROZEN = True
        logger.info("Skill Registry frozen. Further mutations rejected.")

def register(skill_id: str, trigger_type: str = "command_received") -> Callable:
    def decorator(cls: type[SkillProtocol]) -> type[SkillProtocol]:
        with _REGISTRY_LOCK:
            if _FROZEN:
                raise RegistryLockError(f"Cannot register '{skill_id}': registry is frozen.")
            if skill_id in _REGISTRY:
                logger.warning("Overwriting existing skill registration for '%s'", skill_id)
            _REGISTRY[skill_id] = cls
            logger.debug("Registered skill '%s' (trigger=%s)", skill_id, trigger_type)
        return cls
    return decorator

def list_skills() -> list[str]:
    with _REGISTRY_LOCK:
        return sorted(_REGISTRY.keys())

def resolve(event: Any) -> type[SkillProtocol]:
    with _REGISTRY_LOCK:
        skill_class = _REGISTRY.get(event.skill_id)
        if not skill_class:
            raise SkillResolutionError(f"Skill '{event.skill_id}' not found in registry.")
        return skill_class
