import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const NoirShaderMaterial = {
  uniforms: {
    uTime: { value: 0 },
    uColorBase: { value: new THREE.Color('#050505') },
    uColorAccent: { value: new THREE.Color('#2B3BE5') },
    uColorPulse: { value: new THREE.Color('#F59E0B') },
    uResolution: { value: new THREE.Vector2() }
  },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform float uTime;
    uniform vec3 uColorBase;
    uniform vec3 uColorAccent;
    uniform vec3 uColorPulse;
    varying vec2 vUv;

    // Pseudo-random noise for grain
    float random(vec2 st) {
      return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
    }

    void main() {
      vec2 st = vUv;
      float noise = random(st * uTime * 0.1) * 0.05;
      
      // Compute radial gradient distance from center
      float dist = distance(st, vec2(0.5));
      
      // Breathing pulse (Sovereign Image-Life Engine)
      float pulse = (sin(uTime * 0.5) * 0.5 + 0.5) * 0.15;
      
      vec3 color = mix(uColorBase, uColorAccent, (1.0 - dist) * 0.1);
      
      // Add Kintsugi Gold micro-pulses
      if (dist < 0.3 + pulse && fract(uTime + st.x * 10.0) < 0.05) {
         color = mix(color, uColorPulse, 0.2);
      }
      
      // Add Grain
      color -= noise;

      gl_FragColor = vec4(color, 1.0);
    }
  `
};

const ShaderPlane = () => {
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = state.clock.elapsedTime;
    }
  });

  return (
    <mesh>
      <planeGeometry args={[10, 10, 32, 32]} />
      <shaderMaterial
        ref={materialRef}
        attach="material"
        args={[NoirShaderMaterial]}
        transparent={true}
      />
    </mesh>
  );
};

export default function CortexShaderCanvas() {
  return (
    <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: -1, pointerEvents: 'none' }}>
      <Canvas
        camera={{ position: [0, 0, 1], fov: 75 }}
        gl={{ powerPreference: "high-performance", alpha: false, antialias: false }}
        dpr={[1, 2]}
      >
        <color attach="background" args={['#050505']} />
        <ShaderPlane />
      </Canvas>
    </div>
  );
}
