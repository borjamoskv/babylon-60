// @C5-REAL
import React from "react";
import styles from "../styles/GlassCard.module.css";

function cn(...classes: (string | undefined | null | boolean)[]) {
  return classes.filter(Boolean).join(" ");
}

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  glowColor?: string;
}

export default function GlassCard({ children, className, glowColor = "rgba(43,59,229,0.15)" }: GlassCardProps) {
  return (
    <div
      className={cn(
        styles.glassCard,
        className
      )}
    >
      {/* Dynamic Glow Effect */}
      <div 
        className={styles.glowEffect}
        style={{
          background: `radial-gradient(circle at 50% 0%, ${glowColor}, transparent 70%)`
        }}
      />
      
      {/* Noise Texture inside card */}
      <div className={cn(styles.noiseTexture, "noise-texture")} />

      <div className={styles.content}>
        {children}
      </div>
    </div>
  );
}
