// @C5-REAL
import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

import CortexAuditLedger from '../CortexAuditLedger';

export default function AwwwardsHero() {
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Create a scroll trigger range over 250vh
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end start']
  });

  // Glitchy transition for Hero Copy
  const opacityHero = useTransform(scrollYProgress, [0, 0.25], [1, 0]);
  const yHero = useTransform(scrollYProgress, [0, 0.25], [0, -100]);

  // Ledger snaps in sharply (No soft fades)
  const opacityLedger = useTransform(scrollYProgress, [0.3, 0.4], [0, 1]);
  const yLedger = useTransform(scrollYProgress, [0.3, 0.4], [50, 0]);
  const zIndexLedger = useTransform(scrollYProgress, [0, 0.3, 0.31], [0, 0, 20]);

  return (
    <div ref={containerRef} style={{ height: '250vh', position: 'relative', width: '100%', zIndex: 10 }}>
      {/* Sticky Container */}
      <div style={{ position: 'sticky', top: 0, height: '100vh', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        
        {/* Hero Content */}
        <motion.div 
          style={{ 
            opacity: opacityHero, 
            y: yHero, 
            position: 'absolute', 
            zIndex: 10, 
            width: '100%', 
            maxWidth: '1200px', 
            padding: '0 2rem' 
          }}
        >
          <div className="hero-copy" style={{ textAlign: 'center', alignItems: 'center', margin: '0 auto', maxWidth: '800px' }}>
            <p className="eyebrow" style={{ marginBottom: '1.5rem', display: 'inline-block', padding: '0.5rem 1rem', background: '#0a0a0a', border: '1px solid #2B3BE5', color: '#f3f4f6' }}>
              PROTOCOL C5-REAL / SOVEREIGN TRACE
            </p>
            <h1 style={{ fontSize: 'clamp(3.5rem, 8vw, 6.5rem)', lineHeight: 0.95, marginBottom: '2rem', textWrap: 'balance', fontFamily: '"Orbitron", sans-serif', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.02em', textShadow: '0 0 35px rgba(43, 59, 229, 0.25)' }}>
              KNOW EXACTLY WHAT YOUR <span style={{ color: '#F59E0B', textShadow: '0 0 25px rgba(245, 158, 11, 0.3)' }}>AI AGENTS</span> DID.
            </h1>
            <p className="hero-text" style={{ fontSize: '1.15rem', maxWidth: '640px', margin: '0 auto 2.5rem', color: '#8892b0', fontFamily: '"IBM Plex Mono", monospace' }}>
              Track every decision, prove integrity, and replay failures without relying on logs, screenshots, or human memory.
            </p>
            <div className="action-row" style={{ justifyContent: 'center' }}>
              <a className="button-primary" href="/activation" style={{ padding: '1rem 2.5rem', fontSize: '1.1rem', borderRadius: 0, border: '1px solid #2B3BE5', background: 'linear-gradient(135deg, #2B3BE5, #00e5a3)', color: '#050505', fontWeight: 700, letterSpacing: '0.05em', transition: 'all 0.3s ease', boxShadow: '0 0 20px rgba(43, 59, 229, 0.4)' }}>START LOGGING</a>
              <a className="button-secondary" href="https://github.com/borjamoskv/Cortex-Persist" target="_blank" rel="noreferrer" style={{ padding: '1rem 2.5rem', fontSize: '1.1rem', borderRadius: 0, border: '1px solid #333', color: '#fff', fontWeight: 600, letterSpacing: '0.05em', background: 'rgba(255,255,255,0.02)', transition: 'all 0.3s ease' }}>
                VIEW DOCS
              </a>
            </div>
            
            <div style={{ marginTop: '3.5rem', opacity: 0.9 }}>
              <p className="eyebrow" style={{ marginBottom: '1rem', fontSize: '0.75rem', color: '#F59E0B', letterSpacing: '0.2em' }}>SCROLL TO INITIATE LEDGER</p>
              <div style={{ width: '1px', height: '60px', background: 'linear-gradient(180deg, #2B3BE5, transparent)', margin: '0 auto' }} />
            </div>
          </div>
        </motion.div>

        {/* Live Demo Ledger */}
        <motion.div 
          style={{ 
            opacity: opacityLedger, 
            y: yLedger, 
            zIndex: zIndexLedger,
            position: 'absolute', 
            width: '100%', 
            maxWidth: '1080px', 
            padding: '0 2rem' 
          }}
        >
          <div className="surface-sunken" style={{ padding: '0.5rem', borderRadius: 0, border: '1px solid #2B3BE5', background: 'rgba(5,5,5,0.9)', boxShadow: 'none' }}>
            <CortexAuditLedger />
          </div>
        </motion.div>

      </div>
    </div>
  );
}
