import uuid
import time
import cortex_rs
import json

def test_crdt_merge_state():
    print("Creating state 1")
    s1 = cortex_rs.CRDTMergeState()
    
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    id3 = str(uuid.uuid4())
    id4 = str(uuid.uuid4())
    
    s1.add_model(id1, "agent_A", 100)
    s1.add_model(id2, "agent_B", 101)
    s1.remove_model(id2)
    
    print("Creating state 2")
    s2 = cortex_rs.CRDTMergeState()
    s2.add_model(id3, "agent_C", 102)
    s2.add_model(id4, "agent_D", 103)
    
    print("Merging states")
    s2_json = s2.get_state_json()
    s1.merge_with_json(s2_json)
    
    active = s1.get_active_models()
    assert id1 in active
    assert id3 in active
    assert id2 not in active
    
    print("Testing merkle hash...")
    merkle = s1.get_merkle_hash()
    assert len(merkle) == 64
    
    print("All assertions passed successfully!")

if __name__ == "__main__":
    test_crdt_merge_state()
