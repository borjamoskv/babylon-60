# [C5-REAL] Exergy-Maximized
import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Callable, Dict

logger = logging.getLogger(__name__)


@dataclass
class NodeLivenessState:
    node_id: str
    status: str  # "RED" or "GREEN"
    last_seen: float


class LivenessGossipProtocol(asyncio.DatagramProtocol):
    def __init__(self, node_id: str, on_node_red: Callable[[str], None]):
        self.node_id = node_id
        self.on_node_red = on_node_red
        self.peers: Dict[str, NodeLivenessState] = {}
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"[LivenessGossip] Bound protocol for node {self.node_id}")

    def datagram_received(self, data: bytes, addr):
        try:
            payload = json.loads(data.decode("utf-8"))
            peer_id = payload.get("node_id")
            status = payload.get("status")
            
            if not peer_id or not status:
                return

            if status == "RED":
                if peer_id not in self.peers or self.peers[peer_id].status != "RED":
                    logger.warning(f"[LivenessGossip] Peer {peer_id} reported RED. Triggering bypass.")
                    self.on_node_red(peer_id)
            
            self.peers[peer_id] = NodeLivenessState(
                node_id=peer_id,
                status=status,
                last_seen=asyncio.get_event_loop().time()
            )
        except Exception:
            pass


class LivenessGossipLayer:
    """
    Layer 1 Telemetry: UDP Gossip < 100ms.
    Immediately bypasses RED nodes without locking execution flows.
    """
    def __init__(self, node_id: str, port: int = 9999):
        self.node_id = node_id
        self.port = port
        self._running = False
        self._task = None
        self.transport = None
        self.protocol = None

    def _on_peer_red(self, peer_id: str):
        # Implementation for routing bypass.
        # This will be picked up by the cascade_router or similar bypass layer.
        pass

    async def _gossip_loop(self):
        loop = asyncio.get_event_loop()
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: LivenessGossipProtocol(self.node_id, self._on_peer_red),
            local_addr=("0.0.0.0", self.port)
        )
        logger.info(f"[LivenessGossipLayer] Listening on port {self.port}")

        while self._running:
            try:
                # Broadcast heartbeat to local subnet (or known peers)
                payload = json.dumps({"node_id": self.node_id, "status": "GREEN"}).encode("utf-8")
                # For demonstration, broadcasting. In production, send to specific peer IPs or multicast.
                if self.transport:
                    # self.transport.sendto(payload, ("255.255.255.255", self.port)) 
                    pass
                await asyncio.sleep(0.05)  # < 100ms
                
                # Check for dead peers
                now = loop.time()
                for peer_id, state in list(self.protocol.peers.items()):
                    elapsed = now - state.last_seen
                    if state.status == "GREEN" and elapsed > 0.1:
                        logger.warning(f"[LivenessGossipLayer] Peer {peer_id} timed out. Marking RED.")
                        state.status = "RED"
                        self._on_peer_red(peer_id)
                    if state.status == "RED" and elapsed > 0.3:
                        logger.info(f"[LivenessGossipLayer] Evicting stale peer {peer_id} (TTL exceeded).")
                        del self.protocol.peers[peer_id]
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[LivenessGossipLayer] Loop error: {e}")

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._gossip_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except Exception:
                pass
        if self.transport:
            self.transport.close()
