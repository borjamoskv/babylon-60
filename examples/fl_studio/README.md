# FL Studio MCP Bridge Stub

This scaffold lets the existing CORTEX MCP server expose a minimal FL Studio
control surface through a local bridge command.

## What it does

- Adds read-only MCP tools for bridge status, transport status, and channel listing
- Adds gated mutation tools for play, stop, and tempo changes
- Provides a deterministic stub bridge you can run without a real FL Studio instance

## Configure the stub

```bash
export CORTEX_FL_STUDIO_BRIDGE_CMD="python3 /Users/borjafernandezangulo/30_CORTEX/examples/fl_studio/fl_studio_bridge_stub.py"
export CORTEX_FL_STUDIO_WRITE_ENABLE=1
python3 -m cortex.mcp
```

If you want the bridge to be read-only, omit `CORTEX_FL_STUDIO_WRITE_ENABLE`.

## Replace the stub with a real bridge

Your real bridge only needs to:

1. Read one JSON object from `stdin`
2. Execute the requested action against FL Studio
3. Write one JSON object to `stdout`

Expected request shape:

```json
{
  "action": "transport.play",
  "params": {}
}
```

Expected response shape:

```json
{
  "ok": true,
  "message": "FL Studio transport started.",
  "data": {
    "playing": true
  }
}
```

## Suggested real integration options

- FL Studio MIDI scripting plus a local Python bridge
- Virtual MIDI ports if transport and channel control is enough
- OSC if your FL Studio setup already exposes it

Keep destructive actions gated and require explicit operator enablement.
