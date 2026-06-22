import React from 'react';

/**
 * CORTEX MVP Shader Canvas (CSS-only)
 * 
 * We killed the over-engineered React Three Fiber GLSL implementation.
 * Pure CSS grain and radial gradient mapping. 0 Javascript overhead.
 */
export default function CortexShaderCanvas() {
  return (
    <div style={{ 
      position: 'fixed', 
      top: 0, 
      left: 0, 
      width: '100vw', 
      height: '100vh', 
      zIndex: -1, 
      pointerEvents: 'none',
      background: 'radial-gradient(circle at 50% 50%, rgba(43, 59, 229, 0.05) 0%, #050505 80%)',
    }}>
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        opacity: 0.04,
        backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 200 200\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noiseFilter\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.65\' numOctaves=\'3\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noiseFilter)\'/%3E%3C/svg%3E")',
      }} />
    </div>
  );
}
