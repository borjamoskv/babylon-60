# [C5-REAL] Exergy-Maximized
import pytest

from cortex.utils.sql_identifiers import validate_sql_identifier


def test_valid_identifiers():
    valid = [
        "users",
        "facts_meta",
        "vec_facts_tenant1_proj2",
        "s0",
        "idx_void_mih_s15",
        "_",
        "A",
        "a1",
        "a" * 64,
    ]
    for identifier in valid:
        assert validate_sql_identifier(identifier) == identifier


def test_invalid_identifiers():
    invalid = [
        "",
        " ",
        "users table",
        "users; DROP TABLE facts_meta",
        "1facts_meta",
        "facts-meta",
        "tenant$id",
        "a" * 65,
        "users\n",
        "users\0",
    ]
    for identifier in invalid:
        with pytest.raises(ValueError):
            validate_sql_identifier(identifier)
