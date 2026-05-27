import sys
import logging
from click.testing import CliRunner
from cortex.cli.main import cli
from cortex.migrations.core import get_all_schema

logging.basicConfig(level=logging.DEBUG)
db_path = "test_db_verbose.sqlite"

import cortex.migrations.core

original_apply = cortex.migrations.core._apply_base_schema_async


async def verbose_apply(conn):
    print("Verbose apply starts")
    for stmt in get_all_schema():
        print(f"Applying statement: {stmt[:50]}...")
        try:
            await conn.executescript(stmt)
            print("Done")
        except Exception as e:
            print(f"Failed: {e}")
    print("Done all")


cortex.migrations.core._apply_base_schema_async = verbose_apply

result = CliRunner().invoke(cli, ["init", "--db", db_path])
print("EXIT CODE:", result.exit_code)
print("OUTPUT:", result.output)
