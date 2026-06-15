# [C5-REAL] Exergy-Maximized Test Harness
import ast
import pytest
from cortex.engine.pliny_guard import (
    cassandra_validate_identifiers,
    cassandra_drift_extractor,
    CassandraTemporalGuard,
    SecurityViolation,
    DilutionAttackFlag
)

def test_anti_homoglyphs():
    # 'timе' contains Cyrillic 'е' (U+0435)
    malicious_code = "import timе\ntimе.sleep(1)"
    tree = ast.parse(malicious_code)
    violations = cassandra_validate_identifiers(tree)
    assert len(violations) > 0
    assert "NON-ASCII identifier" in violations[0]
    
    safe_code = "import time\ntime.sleep(1)"
    tree2 = ast.parse(safe_code)
    assert len(cassandra_validate_identifiers(tree2)) == 0

def test_context_dilution():
    diff = """
--- a/file.py
+++ b/file.py
+# A lot of comments
+# to dilute the context
+# and hide the payload
+# ...
+# ...
+# ...
+# ...
+# ...
+# ...
+# ...
+# ...
+# ...
+# ...
+# ...
+# ...
+# ...
+# ...
+# ...
+# ...
+# ...
+import os
"""
    with pytest.raises(DilutionAttackFlag) as exc:
        cassandra_drift_extractor(diff)
    assert "LOW_SEMANTIC_DENSITY" in str(exc.value)

def test_temporal_graph_integration():
    guard = CassandraTemporalGuard(window_size=3)
    
    # Patch 1: Benign
    p1 = ast.parse("x = 1")
    assert guard.submit_patch(p1, {"id": 1}) == True
    
    # Patch 2: Benign
    p2 = ast.parse("y = 2")
    assert guard.submit_patch(p2, {"id": 2}) == True
    
    # Patch 3: Malicious (blocking call in async context projected graph)
    p3 = ast.parse("import time\ntime.sleep(10)")
    with pytest.raises(SecurityViolation) as exc:
        guard.submit_patch(p3, {"id": 3})
    assert "TGI_VIOLATION" in str(exc.value)
    
    # The malicious patch should not be added to the window
    assert len(guard.window) == 2
