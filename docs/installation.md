# Installation

For the recommended product boundary, start with the core package and add extras only when you
need a specific integration surface. See [Public Product Surface](product-surface.md).

## Requirements

- **Python 3.10** or later
- **macOS**, **Linux**, or **Windows**
- SQLite 3.42+ (included with Python 3.11+; for 3.10, `pysqlite3` is auto-loaded if available)

---

## Install from PyPI

```bash
pip install cortex-persist
```

### Optional Extras

=== "API Server"
    ```bash
    pip install "cortex-persist[api]"
    ```
    Includes FastAPI, Uvicorn, and HTTPX for the REST API.

=== "MCP Server"
    ```bash
    pip install "cortex-persist[mcp]"
    ```
    Installs the Python MCP SDK needed for `python -m cortex.mcp` and `cortex-mcp`.

=== "Development"
    ```bash
    pip install "cortex-persist[dev]"
    ```
    Includes pytest, pytest-cov, pytest-asyncio, and HTTPX for testing.

=== "Google ADK"
    ```bash
    pip install "cortex-persist[adk]"
    ```
    Adds Google Agent Developer Kit integration.

=== "Billing"
    ```bash
    pip install "cortex-persist[billing]"
    ```
    Stripe integration for SaaS subscription management.

=== "Everything"
    ```bash
    pip install "cortex-persist[all]"
    ```
    Installs all optional dependencies.

---

## Install from Source

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Add extras only if needed:

```bash
pip install -e ".[api,mcp]"
```

---

## Verify Installation

```bash
cortex --version
cortex init
cortex status
```

---

## First Steps

```bash
# Initialize the database
cortex init

# Store your first fact
cortex store my-project "Redis uses skip lists for sorted sets" --tags "redis,data-structures"

# Verify the ledger
cortex verify 1
cortex trust-ledger verify
```

This creates the database at `~/.cortex/cortex.db` with the full schema (facts, transactions, embeddings, consensus, and more).

---

## Platform-Specific Notes

### macOS

- Notifications use `osascript` (Notification Center)
- `moskv-daemon install` installs the background daemon as a `launchd` agent (`~/Library/LaunchAgents/`)
- Native Keychain integration via `pyobjc`

### Linux

- Notifications use `notify-send` (libnotify)
- `moskv-daemon install` installs the background daemon as a `systemd` user service (`~/.config/systemd/user/`)
- No root/sudo required

### Windows

- Notifications use PowerShell Toast
- `moskv-daemon install` installs the background daemon as a Task Scheduler job (triggered at logon)
- Compatible with WSL2 for development

See [Cross-Platform Guide](cross_platform_guide.md) for full architecture details.

---

## Next Steps

- **[Public Product Surface](product-surface.md)** — Recommended boundary for adoption
- **[Quickstart](quickstart.md)** — Store, search, verify in 5 minutes
- **[CLI Reference](cli.md)** — Core commands documented
- **[Architecture](architecture.md)** — How it works under the hood
