---
cat_id: naroa-file-safety
cat_type: workflow
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P1
description: "Naroa File Safety \u2014 Protecci\xF3n de archivos cr\xEDticos del ecosistema\
  \ Naroa."
---


# 🛡️ NAROA-FILE-SAFETY

## Protected Files
- `public/` — artwork images (NEVER delete)
- `src/data/` — curated content
- `.env.local` — API keys

## Before Any Change
```bash
cd ~/naroa && git stash
```

## After Changes
```bash
cd ~/naroa && npm run build && git diff --stat
```

> **Skills:** `BABYLON60-Guard-Omega`
