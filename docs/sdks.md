# CORTEX SDK Directory

CORTEX provides native SDK bindings across major execution environments to ensure high-integrity, sovereign integration with zero manual friction.

## Native Python SDK

The primary SDK layer, featuring native integration with the Ouroboros Intercept Loop and `ArchiTrace` cryptographic validation.

```python
from cortex.sdk import CortexClient

client = CortexClient()
response = client.execute("run-arbitrage")
print(response.verify_level)  # "C5-REAL"
```

## TypeScript / Node.js SDK

High-performance asynchronous bindings for backend services and web applications.

```typescript
import { CortexClient } from '@cortex/sdk';

const client = new CortexClient();
const trace = await client.verifyExecution('tx-042');
```

## Rust SDK

Bare-metal verification primitives for real-time cryptographic execution guards.

```rust
use cortex_sdk::Client;

let client = Client::new()?;
let proof = client.generate_proof("strike-01")?;
```

---
*CORTEX-Persist — Sovereign Execution Primitives.*
