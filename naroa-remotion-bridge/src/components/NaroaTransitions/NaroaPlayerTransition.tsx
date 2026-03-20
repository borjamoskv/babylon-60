import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  Img,
} from 'remotion';

export const NaroaPlayerTransition: React.FC<{
  currentImageUrl: string;
  nextImageUrl: string;
  title: string;
  direction: 'forward' | 'backward';
}> = ({ currentImageUrl, nextImageUrl, title, direction }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Phase 1: Exit current (Frame 0 to 15)
  // Phase 2: Enter next (Frame 10 to 30)
  
  const exitOpacity = interpolate(
    frame,
    [0, 15],
    [1, 0],
    { extrapolateRight: 'clamp' }
  );

  const exitScale = interpolate(
    frame,
    [0, 20],
    [1, 1.05],
    { extrapolateRight: 'clamp' }
  );

  const enterOpacity = interpolate(
    frame,
    [10, durationInFrames - 5],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  const enterScale = interpolate(
    frame,
    [10, durationInFrames],
    [1.1, 1], // Inercia pesada
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  // Typography cinematic reveal
  const titleY = interpolate(
    frame,
    [15, durationInFrames - 10],
    [50, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  const titleOpacity = interpolate(
    frame,
    [15, durationInFrames - 20],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  const analogGrainOpacity = interpolate(
    frame,
    [10, 20, durationInFrames],
    [0.02, 0.08, 0.04],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  const titleLetterSpacing = interpolate(
    frame,
    [15, durationInFrames],
    [0.1, -0.02],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', overflow: 'hidden' }}>
      {/* Saliente */}
      <AbsoluteFill style={{ opacity: exitOpacity, transform: `scale(${exitScale})` }}>
        <Img 
          src={currentImageUrl} 
          style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'grayscale(30%)' }} 
        />
      </AbsoluteFill>

      {/* Entrante */}
      <AbsoluteFill style={{ opacity: enterOpacity, transform: `scale(${enterScale})` }}>
        <Img 
          src={nextImageUrl} 
          style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
        />
        {/* Cinematic Vignette */}
        <AbsoluteFill 
          style={{
            background: 'radial-gradient(circle, transparent 40%, rgba(0,0,0,0.6) 100%)',
            pointerEvents: 'none',
          }}
        />
      </AbsoluteFill>

      {/* Título de Obra Revelado */}
      <AbsoluteFill 
        style={{ 
          justifyContent: 'center', 
          alignItems: 'center',
          pointerEvents: 'none'
        }}
      >
        <h1 
          style={{
             fontFamily: 'Outfit, sans-serif',
             fontWeight: 200,
             fontSize: '7vw',
             color: '#EAEAEA',
             letterSpacing: `${titleLetterSpacing}em`,
             transform: `translateY(${titleY}px)`,
             opacity: titleOpacity,
             textTransform: 'uppercase',
             textShadow: '0 0 40px rgba(0,0,0,0.4)',
             mixBlendMode: 'difference'
          }}
        >
          {title}
        </h1>
      </AbsoluteFill>

      {/* Noise Overlay Cinematográfico Dinámico */}
      <AbsoluteFill 
        style={{
          opacity: analogGrainOpacity,
          mixBlendMode: 'overlay',
          background: 'url("https://upload.wikimedia.org/wikipedia/commons/7/76/1k_Dissolve_Noise_Texture.png") repeat',
          pointerEvents: 'none',
        }}
      />
    </AbsoluteFill>
  );
};
