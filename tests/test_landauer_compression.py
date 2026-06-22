import pytest
from cortex.engine.ingest.landauer_compression import LandauerCompressor

def test_landauer_ast_pruning_removes_docstrings():
    source = '''
"""
Module level docstring. Should be purged.
"""
def hello_world():
    """Function docstring. Should be purged."""
    print("Hello")

class SovereignAgent:
    """Class docstring. Purge."""
    pass
'''
    compressed = LandauerCompressor.apply_compression(source, modality="python_code")
    
    assert 'Module level docstring' not in compressed
    assert 'Function docstring' not in compressed
    assert 'Class docstring' not in compressed
    assert 'def hello_world():' in compressed
    assert 'print(\'Hello\')' in compressed
    assert 'class SovereignAgent:' in compressed

def test_landauer_invalid_syntax_fallback():
    source = "def broken_code(:"
    compressed = LandauerCompressor.apply_compression(source, modality="python_code")
    assert compressed == source
