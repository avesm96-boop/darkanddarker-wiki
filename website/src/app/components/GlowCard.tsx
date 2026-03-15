"use client";

import { useRef, useCallback, type ReactNode, type MouseEvent } from "react";

interface GlowCardProps {
  children: ReactNode;
  className?: string;
  glowColor?: string;
  tiltDeg?: number;
  as?: "div" | "a";
  href?: string;
  onClick?: () => void;
}

export default function GlowCard({
  children,
  className = "",
  glowColor = "rgba(201, 168, 76, 0.15)",
  tiltDeg = 4,
  as = "div",
  href,
  onClick,
}: GlowCardProps) {
  const cardRef = useRef<HTMLDivElement | HTMLAnchorElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);

  const handleMove = useCallback(
    (e: MouseEvent) => {
      const el = cardRef.current;
      const glow = glowRef.current;
      if (!el || !glow) return;

      const rect = el.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const cx = rect.width / 2;
      const cy = rect.height / 2;

      const rotateX = ((y - cy) / cy) * -tiltDeg;
      const rotateY = ((x - cx) / cx) * tiltDeg;

      el.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
      glow.style.background = `radial-gradient(600px circle at ${x}px ${y}px, ${glowColor}, transparent 40%)`;
    },
    [tiltDeg, glowColor]
  );

  const handleLeave = useCallback(() => {
    const el = cardRef.current;
    const glow = glowRef.current;
    if (!el || !glow) return;
    el.style.transform = "perspective(800px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)";
    glow.style.background = "transparent";
  }, []);

  const Tag = as as any;
  const extra = as === "a" ? { href } : {};

  return (
    <Tag
      ref={cardRef}
      className={className}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      onClick={onClick}
      style={{ transition: "transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)", willChange: "transform" }}
      {...extra}
    >
      <div
        ref={glowRef}
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "inherit",
          pointerEvents: "none",
          transition: "background 0.3s ease",
          zIndex: 0,
        }}
      />
      {children}
    </Tag>
  );
}
