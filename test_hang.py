import sys
import logging
from click.testing import CliRunner
from cortex.cli.main import cli

logging.basicConfig(level=logging.DEBUG)
db_path = "test_db.sqlite"
result = CliRunner().invoke(cli, ["init", "--db", db_path])
print("EXIT CODE:", result.exit_code)
print("OUTPUT:", result.output)
