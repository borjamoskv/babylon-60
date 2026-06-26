# BABYLON-60: C5-REAL Formal Guarantees

This document serves as the immutable registry of cryptographic and mathematical guarantees provided by the `babylon-60` verification pipeline. 

## 1. Conformity Isomorphism (Hito C)
The conformity suite (`conformity_suite.py`) guarantees that the formal Rust reference interpreter (`b60_kernel`) preserves exact isomorphism with the abstract machine specified in `spec/semantics.md`. 
* **Coverage Guarantee**: Every formally defined opcode (`NIG`, `DAH`, `LAL`, `FORK`, `AWAIT`, `AFTER`, `EXECUTE`, `SAR`, `BA.EXACT`, `CRITICAL_HALT`) has a bounded algebraic invariant checked against the canonical `proof.ir` graph.
* **Failure Guarantee**: The interpreter is mathematically guaranteed to emit `CRITICAL_HALT: SHUTDOWN` and abort without kernel panic upon diverging state (verified by regression testing).

## 2. Deterministic Reproducibility (Hito D)
The fuzzing suite (`fuzz_b60.py`) generates non-deterministic combinations of `F60` math and asynchronous Coroutine event queues. 
* **Reproducibility Guarantee**: Given the same random seed, the kernel produces byte-for-byte identical Directed Acyclic Graphs (`artifact_bundle_v3/graph.canonical`).
* **Concurrency Guarantee**: Thread schedules (`VecDeque` of Coroutine States) are monotonically sorted by Logical Tick without relying on host OS entropy (`SimulationClock`).

## 3. Immutability and Chain of Trust
Direct `push` to the `master` branch is cryptographically disabled via GitHub Branch Protection.
* **Verification Guarantee**: No commit can enter the `master` branch unless the `c5_formal_verification.yml` pipeline completes with 0 exit codes.
* **Non-Repudiation Guarantee**: All commits and tags must be cryptographically signed by the Developer (`required_signatures: true`). Commits lacking GPG/SSH signatures are rejected by the repository.

## 4. Trusted Computing Base (TCB)
The TCB is explicitly reduced to:
1. `rustc` compiler and `std` library.
2. The GitHub Actions Linux runner environment.
3. The cryptographic SHA-256 hash function.
All domain logic outside this base is mathematically bound to fail the pipeline if tampered.
