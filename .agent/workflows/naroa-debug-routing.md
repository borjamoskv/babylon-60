---
cat_id: naroa-debug-routing
cat_type: workflow
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P1
description: "Naroa Debug Routing \u2014 Diagn\xF3stico de routing en el sitio de\
  \ Naroa."
---


# 🔧 NAROA-DEBUG-ROUTING

// turbo-all

## Check Routes
```bash
cd ~/naroa && grep -rn "path\|route" --include="*.js" --include="*.jsx" | head -20
```

## Verify 404 Handling
Test all known routes and check for dead links.

## Fix
Update router configuration as needed.

> **Skills:** `mac-control-omega`
