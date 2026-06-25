import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function MTKBoundaryVisual() {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mountRef.current) return;

    // ThreeJS setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, mountRef.current.clientWidth / mountRef.current.clientHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    mountRef.current.appendChild(renderer.domElement);

    // Geometry: Cryptographic Core
    const geometry = new THREE.IcosahedronGeometry(2, 2);
    
    // Shader Material for Industrial Noir MTK Core
    const material = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uColor: { value: new THREE.Color("#2B3BE5") }, // Cobalt
        uSecondary: { value: new THREE.Color("#F59E0B") } // Kintsugi Gold
      },
      vertexShader: `
        uniform float uTime;
        varying vec2 vUv;
        varying vec3 vNormal;
        
        // Simplex noise function for organic breathing
        vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
        vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
        vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
        vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
        float snoise(vec3 v) {
          const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
          const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
          vec3 i  = floor(v + dot(v, C.yyy) );
          vec3 x0 = v - i + dot(i, C.xxx) ;
          vec3 g = step(x0.yzx, x0.xyz);
          vec3 l = 1.0 - g;
          vec3 i1 = min( g.xyz, l.zxy );
          vec3 i2 = max( g.xyz, l.zxy );
          vec3 x1 = x0 - i1 + C.xxx;
          vec3 x2 = x0 - i2 + C.yyy; // 2.0*C.x = 1/3 = C.y
          vec3 x3 = x0 - D.yyy;      // -1.0+3.0*C.x = -0.5 = -D.y
          i = mod289(i);
          vec4 p = permute( permute( permute(
                     i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
                   + i.y + vec4(0.0, i1.y, i2.y, 1.0 ))
                   + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
          float n_ = 0.142857142857; // 1.0/7.0
          vec3  ns = n_ * D.wyz - D.xzx;
          vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
          vec4 x_ = floor(j * ns.z);
          vec4 y_ = floor(j - 7.0 * x_ );
          vec4 x = x_ *ns.x + ns.yyyy;
          vec4 y = y_ *ns.x + ns.yyyy;
          vec4 h = 1.0 - abs(x) - abs(y);
          vec4 b0 = vec4( x.xy, y.xy );
          vec4 b1 = vec4( x.zw, y.zw );
          vec4 s0 = floor(b0)*2.0 + 1.0;
          vec4 s1 = floor(b1)*2.0 + 1.0;
          vec4 sh = -step(h, vec4(0.0));
          vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
          vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;
          vec3 p0 = vec3(a0.xy,h.x);
          vec3 p1 = vec3(a0.zw,h.y);
          vec3 p2 = vec3(a1.xy,h.z);
          vec3 p3 = vec3(a1.zw,h.w);
          vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
          p0 *= norm.x;
          p1 *= norm.y;
          p2 *= norm.z;
          p3 *= norm.w;
          vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
          m = m * m;
          return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3) ) );
        }

        void main() {
          vUv = uv;
          vNormal = normal;
          
          float noise = snoise(position * 2.0 + uTime * 0.5);
          vec3 newPosition = position + normal * noise * 0.2;
          
          gl_Position = projectionMatrix * modelViewMatrix * vec4(newPosition, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uTime;
        uniform vec3 uColor;
        uniform vec3 uSecondary;
        varying vec2 vUv;
        varying vec3 vNormal;

        void main() {
          // Inner core energy
          float intensity = pow(0.65 - dot(vNormal, vec3(0, 0, 1.0)), 2.0);
          
          // Kintsugi fracture lines
          float fracture = sin(vUv.y * 50.0 + uTime) * cos(vUv.x * 50.0 - uTime);
          vec3 finalColor = mix(uColor, uSecondary, smoothstep(0.8, 1.0, fracture));
          
          gl_FragColor = vec4(finalColor * intensity * 2.0, 0.9);
        }
      `,
      wireframe: true,
      transparent: true,
    });

    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    // Orbit rings
    const ringGeo = new THREE.TorusGeometry(3, 0.02, 16, 100);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x2B3BE5, transparent: true, opacity: 0.5 });
    const ring1 = new THREE.Mesh(ringGeo, ringMat);
    const ring2 = new THREE.Mesh(ringGeo, ringMat);
    ring1.rotation.x = Math.PI / 2;
    ring2.rotation.y = Math.PI / 2;
    scene.add(ring1);
    scene.add(ring2);

    camera.position.z = 6;

    // Animation loop
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const render = () => {
      const elapsedTime = clock.getElapsedTime();
      
      material.uniforms.uTime.value = elapsedTime;
      mesh.rotation.y = elapsedTime * 0.2;
      mesh.rotation.x = elapsedTime * 0.1;
      
      ring1.rotation.x = (Math.PI / 2) + elapsedTime * 0.5;
      ring1.rotation.y = elapsedTime * 0.3;
      ring2.rotation.y = (Math.PI / 2) + elapsedTime * 0.4;
      ring2.rotation.z = elapsedTime * 0.2;

      renderer.render(scene, camera);
      animationFrameId = window.requestAnimationFrame(render);
    };
    render();

    // Handle resize
    const handleResize = () => {
      if (!mountRef.current) return;
      camera.aspect = mountRef.current.clientWidth / mountRef.current.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.cancelAnimationFrame(animationFrameId);
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
      geometry.dispose();
      material.dispose();
      ringGeo.dispose();
      ringMat.dispose();
    };
  }, []);

  return (
    <div 
      ref={mountRef} 
      style={{ width: '100%', height: '100%', minHeight: '400px', borderRadius: '8px', overflow: 'hidden' }}
      aria-label="Interactive 3D representation of the MTK Boundary"
    />
  );
}
