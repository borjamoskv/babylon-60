use crate::{event::Event, state::State, crypto::hash, verify::verify_event};

pub fn apply_event(state: State, event: Event) -> Result<State, String> {
    // 1. VERIFY PRECONDITIONS
    if !verify_event(&event, &state.last_hash) {
        return Err("INVALID_EVENT".into());
    }

    // Trust-as-a-Service: CRITICAL actions require reputation >= 10
    if event.payload.starts_with(b"CRITICAL:") {
        let rep = state.reputation.get(&event.agent_id).unwrap_or(&0);
        if *rep < 10 {
            return Err("INSUFFICIENT_TRUST".into());
        }
    }

    // 2. DETERMINE NEW STATE HASH
    let new_hash = hash(&event.payload);
    
    // 3. APPLY STATE TRANSITION
    let mut new_state = state.clone();
    new_state.last_hash = new_hash;
    new_state.memory.insert(event.id.clone(), event.payload.clone());

    // Trust-as-a-Service: Minting reputation
    if event.payload.starts_with(b"TRUST_MINT:") {
        // e.g., TRUST_MINT:agent_0001:5
        let payload_str = String::from_utf8_lossy(&event.payload);
        let parts: Vec<&str> = payload_str.split(':').collect();
        if parts.len() == 3 {
            let target_agent = parts[1].to_string();
            let amount: u32 = parts[2].parse().unwrap_or(0);
            let current = *new_state.reputation.get(&target_agent).unwrap_or(&0);
            new_state.reputation.insert(target_agent, current + amount);
        }
    }
    
    Ok(new_state)
}
