from __future__ import annotations

# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
import asyncio
import logging
import re
import subprocess

logger = logging.getLogger("cortex.extensions.daemon.loops.peripherals")


async def _scan_peripherals_once(state, *, command_timeout: float = 5.0) -> None:
    proc = await asyncio.create_subprocess_shell(
        'system_profiler SPBluetoothDataType | grep -A 10 "Connected:"',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=command_timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        logger.warning("Peripheral scan timed out after %.1fs", command_timeout)
        return

    output = stdout.decode(errors="replace")
    devices = {}
    if "AirPods" in output:
        match = re.search(r"Battery Level: (\d+)%", output)
        devices["AirPods"] = {
            "battery": int(match.group(1)) if match else "??",
            "connected": True,
        }
    state.daemons["peripherals"]["devices"] = devices


async def peripheral_loop(state):
    while True:
        try:
            await _scan_peripherals_once(state)
        except OSError as exc:
            logger.debug("Peripheral scan error: %s", exc)
        await asyncio.sleep(10)
