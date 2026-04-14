# Official product demo

This is the single supported demo for CORTEX Persist.

It shows the core product value in 2–3 minutes:

1. Register one AI decision.
2. Verify ledger integrity.
3. Export JSON evidence.

## Demo story

An AI credit-risk agent approves loan application `#443`. CORTEX records the decision, proves the ledger is intact, and exports an audit artifact that can be shared with a reviewer.

## Run in a clean environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
PYTHONPATH=. python examples/demo_canonical.py
```

## What the demo generates

- `official-demo.db` — isolated SQLite database for the run
- `official-demo-audit.json` — exported evidence artifact

Both files are created in a temporary artifact directory printed by the script.
The script also bootstraps a process-local encryption key automatically when the environment does not already provide one.

## Expected outcome

- One decision is recorded for project `official-product-demo`
- Integrity verification returns `valid: true`
- The exported JSON report includes:
  - EU AI Act Article 12 score
  - integrity status
  - fact summary
  - the recorded decision

## Reuse rule

README, quickstart, commercial materials, and pilot materials should all point to this exact demo story and script.
