// cortex_ui/src/App.tsx
import { useEffect, useState, useRef } from 'react';
import './index.css';

interface CausalNode {
  hash_id: string;
  parent_hash: string;
  type?: string;
  x?: number;
  y?: number;
}

function App() {
  const [nodes, setNodes] = useState<Map<string, CausalNode>>(new Map());
  const [status, setStatus] = useState<string>('DISCONNECTED');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setStatus('CONNECTING...');
    // Endpoint C5-REAL SSE
    const es = new EventSource('http://localhost:8000/observability/fsm/stream');

    es.onmessage = (event) => {
      // Not expected on default message, we listen to 'state_mutation'
    };

    es.addEventListener('state_mutation', (e) => {
      setStatus('C5-REAL SYNCED');
      try {
        const data = JSON.parse((e as MessageEvent).data);
        
        setNodes(prev => {
          const next = new Map(prev);
          if (!next.has(data.hash_id)) {
            // Asignación topológica determinista pseudo-aleatoria
            const seed = parseInt(data.hash_id.slice(0, 8), 16);
            const w = containerRef.current?.clientWidth || 800;
            const h = containerRef.current?.clientHeight || 600;
            
            let x = (seed % (w - 200)) + 100;
            let y = ((seed >> 4) % (h - 100)) + 50;

            if (data.parent_hash && next.has(data.parent_hash)) {
               const p = next.get(data.parent_hash)!;
               x = p.x! + (Math.random() * 200 - 100);
               y = p.y! + 80;
            }

            next.set(data.hash_id, {
              ...data,
              x: Math.max(50, Math.min(x, w - 150)),
              y: Math.max(50, Math.min(y, h - 50))
            });
          }
          return next;
        });
      } catch (err) {
        console.error("Entropy decode error", err);
      }
    });

    es.addEventListener('error', (e) => {
      setStatus('ENTROPY FAULT');
      console.error('SSE Error', e);
    });

    return () => es.close();
  }, []);

  return (
    <div className="cortex-dashboard">
      <aside className="sidebar">
        <div className="brand">MOSKV-1 APEX</div>
        
        <div className="metrics-box">
          <div className="metric-label">Swarm Connection</div>
          <div className="metric-value" style={{ color: status.includes('SYNCED') ? 'var(--accent-cyan)' : '#ff3366', fontSize: '1rem' }}>
            {status}
          </div>
        </div>

        <div className="metrics-box">
          <div className="metric-label">Causal Nodes</div>
          <div className="metric-value">{nodes.size}</div>
        </div>

        <div style={{ marginTop: 'auto', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          C5-REAL OBSERVABILITY<br/>
          O(1) BYTE-OFFSET WATCHER
        </div>
      </aside>

      <main className="canvas-container" ref={containerRef} style={{ position: 'relative' }}>
        <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 0 }}>
          {Array.from(nodes.values()).map(n => {
            if (n.parent_hash && nodes.has(n.parent_hash)) {
              const p = nodes.get(n.parent_hash)!;
              // Ajuste simple (+60, +30) asumiendo un nodo de 120x60 aprox para conectar los centros
              return (
                <line 
                  key={`edge-${n.hash_id}`}
                  x1={p.x! + 60} 
                  y1={p.y! + 30} 
                  x2={n.x! + 60} 
                  y2={n.y! + 30} 
                  stroke="var(--accent-cyan)" 
                  strokeWidth="2"
                  strokeOpacity="0.4"
                />
              );
            }
            return null;
          })}
        </svg>

        {Array.from(nodes.values()).map(n => (
          <div 
            key={n.hash_id} 
            className="node new-node"
            style={{ left: n.x, top: n.y, position: 'absolute', zIndex: 1 }}
            title={`Parent: ${n.parent_hash}`}
          >
            {n.hash_id.substring(0, 8)}...
            <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              {n.type || 'NODE'}
            </div>
          </div>
        ))}
      </main>
    </div>
  );
}

export default App;
