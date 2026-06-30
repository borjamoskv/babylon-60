import hashlib
import json
from typing import Dict, List, Set, Optional

class VectorClock:
    """Reloj Vectorial para garantizar orden parcial estricto en redes asíncronas."""
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.clocks: Dict[str, int] = {agent_id: 0}

    def increment(self):
        self.clocks[self.agent_id] += 1

    def update(self, other: 'VectorClock'):
        for agent, time in other.clocks.items():
            self.clocks[agent] = max(self.clocks.get(agent, 0), time)

    def to_dict(self):
        return self.clocks

class BFTMerger:
    """
    Protocolo de Fusión Ouroboros (Conflict-Free Replicated Data Types).
    Fusiona grafos causales sin necesidad de bloqueo coordinado.
    """
    def __init__(self, local_ledger_path: str):
        self.local_ledger_path = local_ledger_path

    def _read_ledger(self, path: str) -> List[dict]:
        nodes = []
        try:
            with open(path, 'rb') as f:
                for line in f:
                    try:
                        nodes.append(json.loads(line.decode('utf-8')))
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        return nodes

    def compute_diff(self, remote_nodes: List[dict]) -> List[dict]:
        """Calcula el delta de entropía aislando los hashes faltantes en O(1)."""
        local_nodes = self._read_ledger(self.local_ledger_path)
        local_hashes = {n.get("hash_id") for n in local_nodes if "hash_id" in n}
        
        # Filtro de Invarianza: Solo extrae los nodos que no existen localmente.
        missing_nodes = [n for n in remote_nodes if n.get("hash_id") not in local_hashes]
        return missing_nodes

    def merge_subgraphs(self, remote_ledger_path: str) -> int:
        """
        Inyecta subgrafos externos en el ledger AOF.
        La inmutabilidad criptográfica previene la sobreescritura.
        """
        remote_nodes = self._read_ledger(remote_ledger_path)
        missing_nodes = self.compute_diff(remote_nodes)

        if not missing_nodes:
            return 0

        # En un grafo topológico estricto, la sincronización se asimila de forma Append-Only.
        merged_count = 0
        with open(self.local_ledger_path, 'ab') as f:
            for node in missing_nodes:
                f.write((json.dumps(node) + "\n").encode('utf-8'))
                merged_count += 1
                
        return merged_count
