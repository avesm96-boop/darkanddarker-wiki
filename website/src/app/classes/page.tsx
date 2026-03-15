import type { Metadata } from "next";
import StubPage from "../components/StubPage";

export const metadata: Metadata = { title: "Classes" };

function ShieldIcon() {
  return (
    <svg viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: 72, height: 72, color: "var(--gold-700)" }}>
      <path d="M36 8L12 17v20c0 14 10 24 24 24s24-10 24-24V17L36 8z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" fill="currentColor" fillOpacity="0.07"/>
      <path d="M36 20v20M26 30h20" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.6"/>
    </svg>
  );
}

export default function ClassesPage() {
  return (
    <StubPage
      icon={<ShieldIcon />}
      subtitle="Roster"
      title="Classes & Builds"
      description="Complete breakdown of all 10 classes with full perk trees, skill descriptions, recommended builds, and best-in-slot gear for each playstyle."
      comingSoon
    />
  );
}
