import inspect

from cortex.engine.legacy_mixin import LegacyMixin


def test_legacy_mixin_only_exposes_consensus_aliases():
    async_methods = {
        name
        for name, value in LegacyMixin.__dict__.items()
        if inspect.iscoroutinefunction(value)
    }

    assert async_methods == {
        "get_votes",
        "verify_vote_ledger",
        "slash_vote_deviation",
    }
