from __future__ import annotations

import importlib.util


def test_legacy_shims_removed() -> None:
    assert importlib.util.find_spec("cortex.daemon_cli") is None
    assert importlib.util.find_spec("cortex.nexus_v8") is None


def test_new_supported_import_paths() -> None:
    assert importlib.util.find_spec("cortex.extensions.daemon.cli") is not None
    assert importlib.util.find_spec("cortex.extensions.nexus") is not None
    assert importlib.util.find_spec("cortex.migrations.migrate") is not None


def test_experimental_module_import_paths() -> None:
    assert importlib.util.find_spec("cortex.experimental.darknet.agents") is not None
    assert importlib.util.find_spec("cortex.experimental.mac_maestro.oracle") is not None
    assert importlib.util.find_spec("cortex.experimental.mcts.tree") is not None
    assert importlib.util.find_spec("cortex.experimental.shannon.entropy") is not None
