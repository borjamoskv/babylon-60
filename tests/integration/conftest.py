import pytest
from cortex.integration.morph_registry import MorphRegistry
from cortex.integration.divergence_audit import DivergenceAuditor
from cortex.integration.verifier import IntegrationVerifier
from cortex.integration.jit_bridge import JITBridgeCompiler

@pytest.fixture
def registry():
    return MorphRegistry()

@pytest.fixture
def auditor():
    return DivergenceAuditor()

@pytest.fixture
def verifier():
    return IntegrationVerifier()

@pytest.fixture
def bridge_compiler(tmp_path):
    return JITBridgeCompiler(output_dir=tmp_path / "bridges")
