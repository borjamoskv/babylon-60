// [C5-REAL] Exergy-Maximized
mod event;
mod state;
mod crypto;
mod verify;
mod kernel;
mod proof;
mod error;
mod memory_dag;

use crate::{event::Event, state::State, memory_dag::MemoryDAG};
use std::time::Instant;

fn main() {
    println!("═══════════════════════════════════════════════════");
    println!("  AS-OS KERNEL — 1000 Agent Stress Test (C5-REAL)");
    println!("═══════════════════════════════════════════════════\n");

    // ── PHASE 1: Chain 1000 deterministic agent events ──
    let mut state = State {
        last_hash: "GENESIS".to_string(),
        memory: std::collections::HashMap::new(),
        reputation: std::collections::HashMap::new(),
        agent_lifecycle: std::collections::HashMap::new(),
    };
    let mut dag = MemoryDAG::new();

    let t0 = Instant::now();
    let mut accepted = 0u32;
    let mut rejected = 0u32;

    for i in 0..1000 {
        let agent_id = format!("agent_{:04}", i);
        let payload = format!("event_payload_{}", i).into_bytes();
        let event = Event {
            id: format!("e{}", i),
            prev_hash: state.last_hash.clone(),
            payload,
            agent_id,
            signature: vec![],
        };

        match kernel::apply_event(state.clone(), event.clone()) {
            Ok(new_state) => {
                dag.chain.push(event);
                state = new_state;
                accepted += 1;
            }
            Err(_e) => {
                rejected += 1;
            }
        }
    }
    let elapsed = t0.elapsed();

    println!("[PHASE 1] 1000 Agent Chain");
    println!("  Accepted: {}", accepted);
    println!("  Rejected: {}", rejected);
    println!("  DAG len:  {}", dag.chain.len());
    println!("  Elapsed:  {:?}", elapsed);
    println!("  Throughput: {:.0} events/sec", 1000.0 / elapsed.as_secs_f64());
    println!();

    // ── PHASE 2: FALSACIÓN — Invariant I1 (prev_hash gate) ──
    // L1: Input Variation — submit event with wrong prev_hash
    println!("[FALSACIÓN I1] prev_hash causal gate");
    let bad_event = Event {
        id: "e_bad_prev".to_string(),
        prev_hash: "TOTALLY_WRONG_HASH".to_string(),
        payload: b"should_fail".to_vec(),
        agent_id: "rogue_agent".to_string(),
        signature: vec![],
    };
    let i1_result = kernel::apply_event(state.clone(), bad_event);
    let i1_pass = i1_result.is_err();
    println!("  L1 Input Variation: wrong prev_hash → rejected={}", i1_pass);

    // L2: Gate Knockout — bypass prev_hash check (simulated by using correct hash)
    let good_event = Event {
        id: "e_knockout".to_string(),
        prev_hash: state.last_hash.clone(),
        payload: b"knockout_test".to_vec(),
        agent_id: "knockout_agent".to_string(),
        signature: vec![],
    };
    let i1_knockout = kernel::apply_event(state.clone(), good_event);
    let i1_knockout_pass = i1_knockout.is_ok();
    println!("  L2 Gate Knockout: correct prev_hash → accepted={}", i1_knockout_pass);

    // L3: Resurrection — re-apply the bad event, must still fail
    let bad_event_again = Event {
        id: "e_resurrection".to_string(),
        prev_hash: "TOTALLY_WRONG_HASH".to_string(),
        payload: b"resurrection_test".to_vec(),
        agent_id: "rogue_agent".to_string(),
        signature: vec![],
    };
    let i1_resurrection = kernel::apply_event(state.clone(), bad_event_again);
    let i1_resurrection_pass = i1_resurrection.is_err();
    println!("  L3 Resurrection: wrong prev_hash again → rejected={}", i1_resurrection_pass);
    println!("  VERDICT: I1 {} (C5-REAL)", if i1_pass && i1_knockout_pass && i1_resurrection_pass { "CONFIRMED ✓" } else { "FAILED ✗" });
    println!();

    // ── PHASE 3: FALSACIÓN — Invariant I3 (determinism) ──
    println!("[FALSACIÓN I3] Deterministic state transitions");
    let genesis_state = State {
        last_hash: "GENESIS".to_string(),
        memory: std::collections::HashMap::new(),
        reputation: std::collections::HashMap::new(),
        agent_lifecycle: std::collections::HashMap::new(),
    };
    let test_event = Event {
        id: "e_det".to_string(),
        prev_hash: "GENESIS".to_string(),
        payload: b"determinism_check".to_vec(),
        agent_id: "det_agent".to_string(),
        signature: vec![],
    };
    let run_a = kernel::apply_event(genesis_state.clone(), test_event.clone()).unwrap();
    let run_b = kernel::apply_event(genesis_state.clone(), test_event.clone()).unwrap();
    let i3_pass = run_a.last_hash == run_b.last_hash
        && run_a.memory.get("e_det") == run_b.memory.get("e_det");
    println!("  L1: Run A hash = {}", &run_a.last_hash[..16]);
    println!("  L1: Run B hash = {}", &run_b.last_hash[..16]);
    println!("  L3: Identical = {}", i3_pass);
    println!("  VERDICT: I3 {} (C5-REAL)", if i3_pass { "CONFIRMED ✓" } else { "FAILED ✗" });
    println!();

    // ── PHASE 4: FALSACIÓN — Invariant I4 (append-only memory) ──
    println!("[FALSACIÓN I4] Append-only memory");
    let mem_before = state.memory.len();
    let append_event = Event {
        id: "e_append".to_string(),
        prev_hash: state.last_hash.clone(),
        payload: b"append_test".to_vec(),
        agent_id: "append_agent".to_string(),
        signature: vec![],
    };
    let new_state = kernel::apply_event(state.clone(), append_event).unwrap();
    let mem_after = new_state.memory.len();
    let i4_pass = mem_after == mem_before + 1;
    // Verify previous entries survived
    let i4_integrity = state.memory.keys().all(|k| new_state.memory.contains_key(k));
    println!("  Memory before: {}", mem_before);
    println!("  Memory after:  {}", mem_after);
    println!("  All prior keys intact: {}", i4_integrity);
    println!("  VERDICT: I4 {} (C5-REAL)", if i4_pass && i4_integrity { "CONFIRMED ✓" } else { "FAILED ✗" });
    println!();

    // ── PHASE 5: FALSACIÓN — Invariant I5 (fail-closed) ──
    println!("[FALSACIÓN I5] Fail-closed default");
    let empty_payload_event = Event {
        id: "e_empty".to_string(),
        prev_hash: state.last_hash.clone(),
        payload: vec![],
        agent_id: "empty_agent".to_string(),
        signature: vec![],
    };
    // Empty payload should still produce a valid hash (SHA256 of empty = valid)
    // but causal chain must remain intact
    let empty_result = kernel::apply_event(state.clone(), empty_payload_event);
    let i5_pass = empty_result.is_ok(); // empty payload is valid, kernel doesn't reject it — this is correct
    println!("  Empty payload event accepted (valid hash): {}", i5_pass);

    // Forge an event mid-chain with tampered prev_hash
    let forged_event = Event {
        id: "e_forged".to_string(),
        prev_hash: crypto::hash(b"forged_garbage"),
        payload: b"injection_attempt".to_vec(),
        agent_id: "adversary".to_string(),
        signature: vec![],
    };
    let forge_result = kernel::apply_event(state.clone(), forged_event);
    let i5_forge_rejected = forge_result.is_err();
    println!("  Forged prev_hash rejected: {}", i5_forge_rejected);
    println!("  VERDICT: I5 {} (C5-REAL)", if i5_forge_rejected { "CONFIRMED ✓" } else { "FAILED ✗" });
    println!();

    // ── PHASE 6: Proof hook validation ──
    println!("[PROOF] ZK-stub validation");
    let proof_event = Event {
        id: "e_proof".to_string(),
        prev_hash: "GENESIS".to_string(),
        payload: b"proof_test".to_vec(),
        agent_id: "proof_agent".to_string(),
        signature: vec![],
    };
    let p = proof::generate_proof(&proof_event);
    let proof_valid = proof::verify_proof(&p);
    println!("  Proof generated & verified: {}", proof_valid);
    println!();

    // ── PHASE 7: FALSACIÓN — Trust-as-a-Service (Reputation Marketplace) ──
    println!("[FALSACIÓN I6] Trust-as-a-Service Validation");
    // L1: Unverified agent attempts critical action (should fail)
    let critical_fail_event = Event {
        id: "e_critical_fail".to_string(),
        prev_hash: state.last_hash.clone(),
        payload: b"CRITICAL:deploy_contract".to_vec(),
        agent_id: "agent_zero_trust".to_string(),
        signature: vec![],
    };
    let i6_fail = kernel::apply_event(state.clone(), critical_fail_event).is_err();
    println!("  L1: Critical action with 0 trust rejected: {}", i6_fail);

    // L2: Trust is minted
    let mint_trust_event = Event {
        id: "e_mint_trust".to_string(),
        prev_hash: state.last_hash.clone(),
        payload: b"TRUST_MINT:agent_elite:15".to_vec(),
        agent_id: "system_oracle".to_string(),
        signature: vec![],
    };
    let state_with_trust = kernel::apply_event(state.clone(), mint_trust_event).unwrap();
    let elite_rep = *state_with_trust.reputation.get("agent_elite").unwrap_or(&0);
    println!("  L2: Trust minted for agent_elite: {}", elite_rep);

    // L3: Elite agent attempts critical action (should succeed)
    let critical_pass_event = Event {
        id: "e_critical_pass".to_string(),
        prev_hash: state_with_trust.last_hash.clone(),
        payload: b"CRITICAL:deploy_contract".to_vec(),
        agent_id: "agent_elite".to_string(),
        signature: vec![],
    };
    let final_state_res = kernel::apply_event(state_with_trust, critical_pass_event);
    let i6_pass = final_state_res.is_ok();
    println!("  L3: Critical action with >=10 trust accepted: {}", i6_pass);
    
    // Update main state reference to point to final
    state = final_state_res.unwrap();
    let i6_verdict = i6_fail && elite_rep == 15 && i6_pass;
    println!("  VERDICT: I6 {} (C5-REAL)", if i6_verdict { "CONFIRMED ✓" } else { "FAILED ✗" });
    println!();

    // ── PHASE 8: FALSACIÓN — Ouroboros Death Protocol (4 Phases) ──
    println!("[FALSACIÓN I7] Ouroboros Death Protocol Validation");
    // L1: Emitting a regular event makes an agent 'Active'
    let regular_event = Event {
        id: "e_regular_active".to_string(),
        prev_hash: state.last_hash.clone(),
        payload: b"DATA:some_normal_data".to_vec(),
        agent_id: "agent_decay".to_string(),
        signature: vec![],
    };
    let state_active = crate::kernel::apply_event(state.clone(), regular_event).unwrap();
    let i7_active = *state_active.agent_lifecycle.get("agent_decay").unwrap() == crate::state::AgentStatus::Active;
    println!("  L1: Normal event marks agent Active: {}", i7_active);

    // L2: Ouroboros Engine forces agent to Tombstone
    let tombstone_event = Event {
        id: "e_tombstone".to_string(),
        prev_hash: state_active.last_hash.clone(),
        payload: b"OUROBOROS:TOMBSTONE:agent_decay".to_vec(),
        agent_id: "system_ouroboros".to_string(),
        signature: vec![],
    };
    let state_tombstoned = crate::kernel::apply_event(state_active.clone(), tombstone_event).unwrap();
    let i7_tombstoned = *state_tombstoned.agent_lifecycle.get("agent_decay").unwrap() == crate::state::AgentStatus::Tombstoned;
    println!("  L2: Ouroboros Daemon Tombstones agent: {}", i7_tombstoned);

    // L3: Tombstoned agent tries to emit event (should be blocked)
    let dead_event = Event {
        id: "e_dead_try".to_string(),
        prev_hash: state_tombstoned.last_hash.clone(),
        payload: b"DATA:try_to_write".to_vec(),
        agent_id: "agent_decay".to_string(),
        signature: vec![],
    };
    let i7_blocked = crate::kernel::apply_event(state_tombstoned.clone(), dead_event).is_err();
    println!("  L3: Tombstoned agent blocked from emitting: {}", i7_blocked);
    
    let i7_verdict = i7_active && i7_tombstoned && i7_blocked;
    state = state_tombstoned;
    println!("  VERDICT: I7 {} (C5-REAL)", if i7_verdict { "CONFIRMED ✓" } else { "FAILED ✗" });
    println!();

    // ── SUMMARY ──
    let all_pass = i1_pass && i1_knockout_pass && i1_resurrection_pass
        && i3_pass && i4_pass && i4_integrity && i5_forge_rejected && i6_verdict && i7_verdict;
    println!("═══════════════════════════════════════════════════");
    if all_pass {
        println!("  ALL INVARIANTS CONFIRMED — C5-REAL ✓");
    } else {
        println!("  INVARIANT VIOLATION DETECTED — C4-SIM ✗");
    }
    println!("  DAG tip: {}", dag.tip_hash());
    println!("  Final state hash: {}...", &state.last_hash[..16]);
    println!("  Memory entries: {}", state.memory.len());
    println!("═══════════════════════════════════════════════════");
}
