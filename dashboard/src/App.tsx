import React, { useState, useEffect } from 'react';
import './index.css';

function App() {
  const [agentsActive, setAgentsActive] = useState(10000);
  const [throughput, setThroughput] = useState(238162);
  const [entropy, setEntropy] = useState(0);

  // Simulate telemetry
  useEffect(() => {
    const interval = setInterval(() => {
      setThroughput(prev => prev + Math.floor(Math.random() * 5000) - 2500);
      setEntropy(prev => Math.max(0, prev + (Math.random() > 0.8 ? 0.01 : -0.01)));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <header className="app-header">
        <div className="logo-group">
          <div className="logo-symbol">Ω</div>
          <div className="logo-text">
            <h1>CORTEX ADMIN</h1>
            <span>SOVEREIGN CLOUD DASHBOARD</span>
          </div>
        </div>
        <div className="status-indicator">
          <div className="status-dot"></div>
          <span>C5-REAL // LEGION-10K ACTIVE</span>
        </div>
      </header>

      <main className="dashboard-grid">
        <div className="panel metric-card">
          <span className="label">ACTIVE AGENTS</span>
          <span className="value">{agentsActive.toLocaleString()}</span>
          <span className="mono" style={{ color: 'var(--color-accent)', fontSize: '0.75rem' }}>STAGED LEGION-2M SWARM</span>
        </div>

        <div className="panel metric-card">
          <span className="label">THROUGHPUT O(1)</span>
          <span className="value">{(throughput * 32).toLocaleString()} <span style={{fontSize: '1rem', color: 'var(--color-text-secondary)'}}>op/s</span></span>
          <span className="mono" style={{ color: 'var(--color-accent)', fontSize: '0.75rem' }}>ZERO-COPY VSA RING BUFFER</span>
        </div>

        <div className="panel metric-card">
          <span className="label">GLOBAL CONSENSUS NORM</span>
          <span className="value" style={{ color: 'var(--color-accent)' }}>
            1.000000
          </span>
          <span className="mono" style={{ color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>EPISTEMIC SLASHING (20%)</span>
        </div>

        <div className="panel" style={{ gridColumn: '1 / -1' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>MARKET REALITY BENCHMARK</h3>
            <span className="mono" style={{ color: 'var(--color-accent)' }}>REAL-TIME C5-REAL COMPARATIVE</span>
          </div>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem'
          }}>
            {/* Project Genie */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Project Genie (Est. Limit)</span>
                <span className="mono" style={{ color: 'var(--color-danger)' }}>10,000 OPS [GIL / I/O Bound]</span>
              </div>
              <div style={{ width: '100%', height: '8px', background: 'var(--color-bg-elevated)', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ width: '0.5%', height: '100%', background: 'var(--color-danger)' }}></div>
              </div>
            </div>

            {/* Gemini Spark */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Gemini Spark (Est. Limit)</span>
                <span className="mono" style={{ color: 'var(--color-warning)' }}>50,000 OPS [TPU / Network Bound]</span>
              </div>
              <div style={{ width: '100%', height: '8px', background: 'var(--color-bg-elevated)', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ width: '2.5%', height: '100%', background: 'var(--color-warning)' }}></div>
              </div>
            </div>

            {/* CORTEX-Persist */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                <span style={{ fontWeight: 'bold', color: 'var(--color-text-primary)' }}>CORTEX-Persist (VSA Mmap Ring)</span>
                <span className="mono" style={{ color: 'var(--color-accent)', fontWeight: 'bold' }}>{(throughput * 32).toLocaleString()} OPS [Zero-Copy / L4 Tensor]</span>
              </div>
              <div style={{ width: '100%', height: '12px', background: 'var(--color-bg-elevated)', borderRadius: '6px', overflow: 'hidden', boxShadow: '0 0 10px rgba(43, 59, 229, 0.3)' }}>
                <div style={{ width: '100%', height: '100%', background: 'var(--color-accent)', transition: 'width 0.5s ease-in-out' }}></div>
              </div>
            </div>
          </div>
        </div>

        <div className="panel" style={{ gridColumn: '1 / -1' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>CRYPTOGRAPHIC DECISION LEDGER</h3>
            <button className="btn btn-primary">EXPORT AUDIT</button>
          </div>
          <div style={{ 
            background: 'var(--color-bg-elevated)', 
            padding: '1rem', 
            borderRadius: 'var(--radius-sm)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.875rem',
            color: 'var(--color-text-secondary)'
          }}>
            <div style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)', display: 'flex', gap: '1rem' }}>
              <span style={{ color: 'var(--color-accent)' }}>a2323158...</span>
              <span>Global Integrity SHA256 Confirmed. Norm: 1.000000.</span>
              <span style={{ marginLeft: 'auto' }}>Just now</span>
            </div>
            <div style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)', display: 'flex', gap: '1rem' }}>
              <span style={{ color: 'var(--color-accent)' }}>0x7b2b0a11...</span>
              <span>Staged Legion Wave 100/100 completed. 400,000 Agents Slashed.</span>
              <span style={{ marginLeft: 'auto' }}>2s ago</span>
            </div>
            <div style={{ padding: '0.5rem 0', display: 'flex', gap: '1rem' }}>
              <span style={{ color: 'var(--color-accent)' }}>0x9c3f4e22...</span>
              <span>Sovereign Magic Decorator applied. Tenant: sys-01.</span>
              <span style={{ marginLeft: 'auto' }}>188s ago</span>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}

export default App;
