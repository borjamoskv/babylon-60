import uuid
import json
import logging
from cortex.storage.wal import WriteAheadLog
from cortex_rs import try_seal_fact, create_staging_fact, can_read_fact

logger = logging.getLogger(__name__)

class FactStore:
    def __init__(self):
        self.facts = {}
        
    async def get(self, fact_id):
        return self.facts.get(fact_id)
        
    async def insert(self, statement, evidence, epistemic_status, fact_json=None):
        fact_id = uuid.uuid4().hex
        class Fact:
            pass
        f = Fact()
        f.epistemic_status = epistemic_status
        f.statement = statement
        f.evidence = evidence
        f.fact_json = fact_json
        self.facts[fact_id] = f
        return fact_id
        
    async def update_status(self, fact_id, status, fact_json=None):
        if fact_id in self.facts:
            self.facts[fact_id].epistemic_status = status
            if fact_json:
                self.facts[fact_id].fact_json = fact_json
            
    async def remove(self, fact_id):
        if fact_id in self.facts:
            del self.facts[fact_id]

class ZKGuard:
    def __init__(self, fact_store, wal):
        self.fact_store = fact_store
        self.wal = wal
        
    async def validate_and_seal(self, fact_id, wal_event_hash, is_valid=True):
        fact = await self.fact_store.get(fact_id)
        if not fact:
            return False
            
        try:
            # Rust FFI call - demands WAL hash for provenance
            new_fact_json = try_seal_fact(fact.fact_json, wal_event_hash, is_valid)
            new_fact = json.loads(new_fact_json)
            
            if new_fact.get('epistemic_status') == 'rejected':
                raise ValueError("Fact rejected by Rust validation layer")
                
            await self.fact_store.update_status(fact_id, 'sealed', new_fact_json)
            self.wal.seal_batch([fact_id])
            return True
        except ValueError as e:
            # SAGA ROLLBACK: Fact rejected by Data Plane
            logger.warning(f"[SAGA ROLLBACK] ZK-Guard validation failed: {e}")
            await self.fact_store.update_status(fact_id, 'rejected')
            self.wal.mark_rejected([fact_id])
            return False

class EDG:
    def __init__(self):
        self.nodes = set()
        
    async def inject_node(self, fact_id):
        self.nodes.add(fact_id)
        
    async def get_node(self, fact_id):
        return fact_id if fact_id in self.nodes else None

class SagaOrchestrator:
    def __init__(self):
        self.wal = WriteAheadLog()
        self.fact_store = FactStore()
        self.zk_guard = ZKGuard(self.fact_store, self.wal)
        self.edg = EDG()
        
    async def generate_hypothesis(self, claim, evidence, agent_id="agent_1"):
        # 1. Rust generates staging JSON
        fact_json = create_staging_fact(agent_id, claim)
        
        # 2. Write to WAL first (Append-only state)
        event_payload = {"agent": agent_id, "claim": claim, "evidence": evidence}
        # Generates provenance hash
        wal_event_hash = self.wal.write_pending(event_id="tmp_id", payload=event_payload)
        
        # 3. Store in staging (Postgres/SQLite isolation in real deployment)
        fact_id = await self.fact_store.insert(
            statement=claim,
            evidence=evidence,
            epistemic_status='staging',
            fact_json=fact_json
        )
        
        # Actualizamos event_id de forma atómica
        self.wal.mark_rejected(["tmp_id"]) # Cleanup placeholder
        wal_event_hash = self.wal.write_pending(event_id=fact_id, payload=event_payload)
        
        return fact_id, wal_event_hash
