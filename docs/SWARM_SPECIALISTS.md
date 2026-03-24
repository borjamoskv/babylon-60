# SWARM SPECIALISTS (Ω-Architecture)

> *We are many, yet we act as one. The swarm verifies, the ledger remembers.*

CORTEX-Persist provides an ultra-potent sovereign swarm of specialized agents, each integrated via `cortex/swarm/specialists.py`. These actuators tap into the highest-tier operational logic (CORTEX UPGRADED SKILLS) while strict compliance with `SwarmManager` privacy gates and ledger guarantees is enforced.

## 1. Top-Tier Specialists

The swarm is composed of ultra-potent P0 skills.

| Specialist Node | Provider ID | CORTEX Skill Link (Local Actuator) | Model (Ω₇ Compliant) |
| --- | --- | --- | --- |
| **Devin Autodidact (v3.0)** | `devin-autodidact-omega` | `~/.gemini/antigravity/skills/devin-autodidact-omega/SKILL.md` | Gemini 3.1 Pro / Claude 3.7 Sonnet |
| **Ouroboros Capital** | `ouroboros-capital-omega` | `~/.gemini/antigravity/skills/ouroboros-capital-omega/SKILL.md` | o3-pro |
| **Awwwards Deconstructor** | `awwwards-deconstructor` | `~/.gemini/antigravity/skills/awwwards-deconstructor/SKILL.md` | Gemini 3 Deep Think |
| **CrewAI Operator** | `crewai-omega` | `~/.gemini/antigravity/skills/crewai-omega/SKILL.md` | Claude 3.7 Sonnet |

## 2. Dispatch Example

```python
import asyncio
from cortex.ledger import SovereignLedger
from cortex.swarm.factory import create_sovereign_swarm

async def execute_p0_swarm_mission():
    ledger = SovereignLedger(db_path=":memory:")
    swarm = create_sovereign_swarm(ledger=ledger)

    # Task 1: Code evolution
    response_devin = await swarm.dispatch(
        actuator_name="devin",
        task="Optimize routing pipeline reducing allocations by 14% via zero-spread patterns."
    )

    # Task 2: Capital extraction based on market inefficiencies
    response_ouro = await swarm.dispatch(
        actuator_name="ouroboros",
        task="Scan Layer2 DEX pools for arbitrage > 1.2% with strict revert conditions."
    )

    print("Devin Execution:", response_devin)
    print("Ouroboros Execution:", response_ouro)

# Execute
asyncio.run(execute_p0_swarm_mission())
```

## 3. Epistemic Posture & Ledger Audit

Every call to `swarm.dispatch()` triggers:
1. **Privacy Gate (`privacy_gate.py`)**: Sanitizes outgoing context to prevent PII leakage.
2. **Pre-Dispatch Ledger Logging**: Records the hash of the task intention.
3. **Execution**: The specialized local actuator invokes the skill pipeline (e.g., Devin v3 API bypass).
4. **Post-Dispatch Ledger Logging**: Records the cryptographic hash of the execution artifact, marking it as verifiable evidence.

## Thermodynamic Justification

Claim: Integrating pre-compiled ultra-potent skills via `BaseSpecialistActuator` creates net exergy gain.
Justification:
 - Base: The overhead of prompt-engineering is moved to compile-time (inside `.gemini/antigravity/skills`).
 - Variables: `r = 0.9` (high reuse expected), `d = 1` (direct mapping).
 - Rango: [O(1) configuration, near zero hallucination during delegation].
 - Confianza: C5-Static (Structural limit enforced).
