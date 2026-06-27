# HaikuGuard (Ω₄): Aesthetic Integrity Validator
*Document version: 1.0.0 (Execution Level: C5-REAL) — Core Systems Group — Author: **Borja Moskv***

---

## 1. Philosophical Imperative

Within CORTEX-Persist, axioms are not mere configurations; they are the governing laws of the cognition stack. Simple stochastic text is prone to semantic drift, hallucination, and decay. The **HaikuGuard (Ω₄)** enforces aesthetic compression. By forcing sacred truths to be compiled as a Haiku (5-7-5 syllables), we minimize information entropy (optimizing Landauer's limit) and demand intentional density from the writing agent.

---

## 2. Technical Architecture & Trigger Conditions

The HaikuGuard is implemented in [`cortex/security/haiku.py`](file:///Users/borjafernandezangulo/30_CORTEX/cortex/security/haiku.py) and is enforced by the [`FactManager`](file:///Users/borjafernandezangulo/30_CORTEX/cortex/facts/manager.py) at the admission boundary.

### Trigger Rules
A fact proposal triggers `HaikuGuard.enforce()` if:
1. `fact_type == "axiom"`
2. OR `"sacred"` is present in the `tags` list.

If these conditions are met, any content that fails validation raises a `GuardViolation`, aborting the store sequence:
```python
raise GuardViolation("Axiom rejected (Ω₄): Sacred truths must be aesthetically compressed into a Haiku (5-7-5).")
```

---

## 3. Syllable Counting Heuristics

The guard supports bilingual validation (Spanish and English), roughly detecting the language by scanning for Spanish accents (`[áéíóúüñ]`).

### A. Spanish Heuristic (`count_syllables_es`)
- **Character Filtering:** Cleans the word to keep only letters `[a-záéíóúüñ]`.
- **Vowel Grouping:** Counts groupings of vowels (`[aeiouáéíóúü]`).
- **Hiatus / Diphthongs:** Consecutive strong vowels (`[aeoáéíóú]`) are split into separate syllables. Common diphthongs are kept together for the syllable count.

### B. English Heuristic (`count_syllables_en`)
- **Vowel Detection:** Scans for standard English vowels (`[aeiouy]`).
- **Adjustments:**
  - Ignores trailing silent `"e"` (e.g., `code` -> 1 syllable).
  - Handles ending `"le"` if preceded by a consonant (e.g., `simple` -> 2 syllables).
  - Enforces a minimum count of `1` syllable per non-empty word.

### C. Validation Tolerance
The expected line syllable structure is `[5, 7, 5]`. Due to the heuristic nature of the syllable counters, `HaikuGuard` allows a **tolerance of $\pm 1$** syllable per line:
```python
expected = [5, 7, 5]
for actual, target in zip(counts, expected, strict=False):
    if abs(actual - target) > 1:
        return False
```

---

## 4. Physical Promotion: `ImmunityState.SEALED`

Under the CORTEX security policy ([`cortex/security/policy.py`](file:///Users/borjafernandezangulo/30_CORTEX/cortex/security/policy.py)), facts that pass the `HaikuGuard` bypass normal pathogen profiling and mutation risk checks. 

```python
if HaikuGuard.validate(payload.get("content", "")):
    if payload.get("fact_type") == "axiom" or "sacred" in payload.get("tags", []):
        return ImmunityState.SEALED
```

This promotion grants immediate **SEALED** status, locking the fact from further modification or degradation in subsequent agent cycles.
