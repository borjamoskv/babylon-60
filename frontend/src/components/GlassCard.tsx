// @C5-REAL
import React from 'react';
import { cn } from './AwwwardsFadeIn';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  glowColor?: string;
}

export default function GlassCard({ children, className, glowColor = 'rgba(43,59,229,0.15)' }: GlassCardProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden border border-white/5 bg-[#050505]/80 backdrop-blur-md p-8 group transition-colors duration-200 hover:border-[#2B3BE5] hover:bg-[#0a0a0a]",
        className
      )}
    >
      {/* Kintsugi Gold micro-border glow on hover */}
      <div 
        className="absolute bottom-0 left-0 h-[1px] w-0 bg-[#F59E0B] group-hover:w-full transition-all duration-300 ease-out"
      />
      
      {/* Noise Texture inside card */}
      <div className="absolute inset-0 z-0 opacity-[0.05] mix-blend-screen pointer-events-none" 
           style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.85%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E")' }} 
      />

      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
}
