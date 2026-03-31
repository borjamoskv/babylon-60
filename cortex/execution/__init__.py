"""
cortex.execution — Docker Sandbox + Risk-Tiered Auto-Allow
==========================================================
G2 Autonomous Execution substrate.
"""
from .risk import RiskTier, classify_command
from .sandbox import DockerSandbox, SandboxResult

__all__ = ["DockerSandbox", "SandboxResult", "RiskTier", "classify_command"]
