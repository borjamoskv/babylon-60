import os
import json
import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("cortex.remotion")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class UESSRemotionBridge:
    """
    C5-REAL Remotion Integration Bridge.
    Projects the CORTEX Event DAG into a deterministic Scene Graph.
    Output is a Remotion-ready JSON sequence where:
    - History = Replay of events
    - Visuals = Projection of the graph
    - Music = State function (derived from entropy/DVF)
    """
    def __init__(self, log_path: str = "cortex_event_aof.jsonl", out_path: str = "remotion_scene_graph.json"):
        self.log_path = log_path
        self.out_path = out_path
        self.frames: List[Dict[str, Any]] = []
        self.current_frame = 0
        self.last_processed_line = 0

    def event_to_frame_mutation(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Maps an internal UESS Event into a Visual Scene Graph mutation."""
        event_type = event.get("type", "UNKNOWN")
        payload = event.get("payload", {})
        
        mutation = {
            "frame": self.current_frame,
            "hlc": event.get("hlc"),
            "event_type": event_type,
            "visuals": {},
            "audio": {}
        }
        
        if event_type == "SWARM_TICK":
            entropy = payload.get("global_entropy", 0.0)
            nodes = payload.get("active_nodes", 1)
            # Visuals: Particle density scales with active nodes. Glow scales with entropy.
            mutation["visuals"] = {
                "particle_density": nodes * 10,
                "ambient_glow": min(1.0, entropy * 1.5),
                "camera_shake": 0.0
            }
            # Audio: Drone pitch follows entropy
            mutation["audio"] = {
                "drone_pitch": 40 + (entropy * 100),
                "beat_interval": 120
            }
            
        elif event_type == "AST_MUTATE":
            agent = event.get("agent_id", 0)
            mutation["visuals"] = {
                "pulse_node_id": agent,
                "edge_color": "#2B3BE5", # Industrial Noir 2026 Blue
                "camera_shake": 0.2
            }
            mutation["audio"] = {
                "sfx": "sharp_synth_hit",
                "volume": 0.8
            }
            
        elif event_type == "SPEC_REWRITE":
            mutation["visuals"] = {
                "global_glitch": True,
                "invert_colors": True,
                "camera_shake": 1.0
            }
            mutation["audio"] = {
                "sfx": "ouroboros_bass_drop",
                "volume": 1.0
            }
            
        return mutation

    def process_aof(self):
        """Tails the Event AOF and builds the Scene Graph Sequence."""
        if not os.path.exists(self.log_path):
            logger.warning(f"Event Log {self.log_path} not found.")
            return

        new_lines = 0
        with open(self.log_path, "r") as f:
            for i, line in enumerate(f):
                if i < self.last_processed_line:
                    continue
                try:
                    event = json.loads(line)
                    frame_mutation = self.event_to_frame_mutation(event)
                    self.frames.append(frame_mutation)
                    self.current_frame += 10 # 10 frames spacing per event
                    new_lines += 1
                except json.JSONDecodeError:
                    continue
            self.last_processed_line += new_lines
            
        if new_lines > 0:
            self._flush_scene_graph()
            logger.info(f"Remotion Scene Graph updated. +{new_lines} frames.")

    def _flush_scene_graph(self):
        with open(self.out_path, "w") as f:
            json.dump({
                "fps": 30,
                "total_frames": self.current_frame,
                "mutations": self.frames
            }, f, indent=2)

if __name__ == "__main__":
    bridge = UESSRemotionBridge()
    logger.info("Initializing Remotion Bridge. Scanning Event Log...")
    bridge.process_aof()
    logger.info(f"Bridge Execution Complete. Remotion manifest written to {bridge.out_path}")
