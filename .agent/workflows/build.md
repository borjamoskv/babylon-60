---
description: Build and run LiveNotch macOS app
---

# 🔨 Build LiveNotch

To use this workflow, set the `NOTCH_LIVE_DIR` environment variable to the path of your LiveNotch repository. If not set, it defaults to `~/notch-live`.

## Quick Build

// turbo
1. Build the project:
```bash
cd "${NOTCH_LIVE_DIR:-~/notch-live}" && swift build 2>&1 | tail -20
```

## Release Build

// turbo
2. Build with optimizations:
```bash
cd "${NOTCH_LIVE_DIR:-~/notch-live}" && swift build -c release 2>&1 | tail -20
```

## Run

// turbo
3. Run the application:
```bash
cd "${NOTCH_LIVE_DIR:-~/notch-live}" && swift run LiveNotch
```

## Clean Build

// turbo
4. Clean and rebuild from scratch:
```bash
cd "${NOTCH_LIVE_DIR:-~/notch-live}" && swift package clean && swift build 2>&1 | tail -30
```
