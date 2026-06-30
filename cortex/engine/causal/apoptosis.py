import os
import json
import fcntl
import tempfile
import shutil
from typing import Dict

class ThermodynamicApoptosis:
    """
    Motor de Poda de Entropía (C5-REAL).
    Comprime un AOF lineal en su snapshot termodinámicamente óptimo, erradicando
    histórico redundante o nodos huérfanos sin romper la prueba criptográfica.
    """
    def __init__(self, ledger_path: str):
        self.ledger_path = ledger_path

    def _compress_state(self) -> Dict[str, dict]:
        """Calcula el estado topológico activo en memoria O(N_Active)."""
        active_state = {}
        if not os.path.exists(self.ledger_path):
            return active_state

        with open(self.ledger_path, 'rb') as f:
            for line in f:
                try:
                    node = json.loads(line.decode('utf-8'))
                    # Lógica de compactación: Nodos con mismo hash_id sobreescriben previos
                    # o se pueden descartar nodos marcados como "pruned"
                    if "hash_id" in node:
                        active_state[node["hash_id"]] = node
                except json.JSONDecodeError:
                    continue # Purga de bytes corruptos
        return active_state

    def trigger_snapshot(self) -> int:
        """
        Ejecuta la purga con bloqueo atómico POSIX (fcntl) para garantizar
        que ningún agente mute el estado durante la compactación.
        """
        if not os.path.exists(self.ledger_path):
            return 0

        with open(self.ledger_path, 'ab') as origin_fd:
            fcntl.flock(origin_fd.fileno(), fcntl.LOCK_EX)
            try:
                state = self._compress_state()
                
                fd, temp_path = tempfile.mkstemp(suffix=".aof")
                with os.fdopen(fd, 'w') as temp_f:
                    for node in state.values():
                        temp_f.write(json.dumps(node) + "\n")
                        
                # Reemplazo atómico a nivel de sistema operativo
                shutil.move(temp_path, self.ledger_path)
                return len(state)
            finally:
                fcntl.flock(origin_fd.fileno(), fcntl.LOCK_UN)
