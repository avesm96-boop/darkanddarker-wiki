import type { Metadata } from "next";
import StubPage from "../components/StubPage";

export const metadata: Metadata = { title: "Quests" };

function ScrollIcon() {
  return (
    <svg viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: 72, height: 72, color: "var(--gold-700)" }}>
      <path d="M18 12h40a6 6 0 010 12H18V12z" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.08"/>
      <path d="M18 24v32a6 6 0 01-6-6V18a6 6 0 016 6z" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M18 56h40a6 6 0 100-12H18" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M28 32h24M28 40h18M28 48h12" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5"/>
    </svg>
  );
}

export default function QuestsPage() {
  return (
    <StubPage
      icon={<ScrollIcon />}
      subtitle="Objectives"
      title="Quest Tracker"
      description="All 553 quests across every merchant in Dark and Darker. Track your progress, find optimal completion order, and preview rewards before accepting."
      comingSoon
    />
  );
}
