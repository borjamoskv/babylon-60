"""
CORTEX v6 — Sovereign Wallet / Key Vault Configuration.
Allows the user to safely inject private keys into the OS Keyring
without exposing them in plaintext or .env files.
"""

from __future__ import annotations

import re

import click
import keyring

from cortex.cli.common import console
from cortex.crypto.keyring import SERVICE_NAME

WALLET_KEY_NAME = "ouroboros_wallet_key"


@click.group(name="wallet")
def wallet_cmds() -> None:
    """Sovereign wallet and vault management."""
    pass


@wallet_cmds.command("set-ouroboros-key")
@click.option(
    "--key",
    prompt="Enter EVM Private Key",
    hide_input=True,
    help="The Ouroboros Capital EVM private key.",
)
def set_ouroboros_key(key: str) -> None:
    """Store the Ouroboros EVM private key securely in OS keyring."""
    key = key.strip()

    # Structural Guard (Ω₁)
    raw_key = key[2:] if key.lower().startswith("0x") else key
    if not re.match(r"^[0-9a-fA-F]{64}$", raw_key):
        console.print("[bold red]🛑 SOVEREIGN SECURITY GATE — INVALID KEY FORMAT[/bold red]")
        console.print(
            "[dim]The provided string is not a valid 64-character hexadecimal EVM private key.[/dim]"
        )
        raise click.Abort()

    normalized_key = "0x" + raw_key.lower()

    try:
        keyring.set_password(SERVICE_NAME, WALLET_KEY_NAME, normalized_key)
        console.print(
            f"[bold green]✔ Ouroboros wallet key securely vaulted in '{SERVICE_NAME}' "
            f"under '{WALLET_KEY_NAME}'.[/bold green]"
        )
        console.print(
            "[dim]This key will be automatically injected into the Ouroboros Engine "
            "during runtime.[/dim]"
        )
    except Exception as e:
        console.print(f"[bold red]❌ Failed to store key in OS Keychain:[/bold red] {e}")


@wallet_cmds.command("check-ouroboros-key")
def check_ouroboros_key() -> None:
    """Check if the Ouroboros key is currently vaulted."""
    try:
        key = keyring.get_password(SERVICE_NAME, WALLET_KEY_NAME)
        if key:
            console.print(
                f"[bold green]✔ Ouroboros wallet key is present in the vault ([dim]...{key[-4:]}[/dim]).[/bold green]"
            )
        else:
            console.print(
                "[bold yellow]⚠ No Ouroboros wallet key found in the vault.[/bold yellow]"
            )
    except Exception as e:
        console.print(f"[bold red]❌ Failed to access OS Keychain:[/bold red] {e}")


@wallet_cmds.command("delete-ouroboros-key")
def delete_ouroboros_key() -> None:
    """Delete the Ouroboros key from the vault."""
    try:
        keyring.delete_password(SERVICE_NAME, WALLET_KEY_NAME)
        console.print("[bold green]✔ Ouroboros wallet key removed from the vault.[/bold green]")
    except keyring.errors.PasswordDeleteError:
        console.print("[bold yellow]⚠ Key not found in vault.[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]❌ Failed to access OS Keychain:[/bold red] {e}")
