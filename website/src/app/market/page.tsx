import type { Metadata } from "next";
import StubPage from "../components/StubPage";

export const metadata: Metadata = { title: "Market" };

function CoinsIcon() {
  return (
    <svg viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: 72, height: 72, color: "var(--gold-700)" }}>
      <circle cx="44" cy="44" r="20" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.07"/>
      <circle cx="30" cy="30" r="20" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.10"/>
      <path d="M30 20v4M30 36v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M24 24h10a3 3 0 010 6h-6a3 3 0 000 6h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

export default function MarketPage() {
  return (
    <StubPage
      icon={<CoinsIcon />}
      subtitle="Economy"
      title="Market Prices"
      description="Marketplace valuations, trading post prices, and merchant inventories with affinity unlock requirements. Know what your loot is worth before you sell."
      comingSoon
    />
  );
}
