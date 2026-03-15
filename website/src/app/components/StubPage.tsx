import Link from "next/link";

interface StubPageProps {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  description: string;
  comingSoon?: boolean;
}

function ArrowLeftIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <path d="M19 12H5M12 5l-7 7 7 7"/>
    </svg>
  );
}

export default function StubPage({ icon, title, subtitle, description, comingSoon }: StubPageProps) {
  return (
    <div className="stub-page">
      <div style={{ maxWidth: 520, textAlign: "center", padding: "0 24px" }}>
        <div className="stub-icon">{icon}</div>
        <div style={{
          fontFamily: "var(--font-heading)",
          fontSize: "0.6875rem",
          letterSpacing: "0.35em",
          textTransform: "uppercase",
          color: "var(--gold-700)",
          marginBottom: 16,
        }}>
          {subtitle}
        </div>
        <h1 className="stub-title">{title}</h1>
        <p className="stub-desc">{description}</p>

        {comingSoon && (
          <div style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 10,
            padding: "10px 24px",
            border: "1px solid var(--border-dim)",
            borderRadius: 2,
            fontFamily: "var(--font-heading)",
            fontSize: "0.6875rem",
            letterSpacing: "0.22em",
            textTransform: "uppercase",
            color: "var(--gold-700)",
            marginBottom: 40,
          }}>
            <span style={{
              width: 6, height: 6,
              background: "var(--gold-700)",
              borderRadius: "50%",
              animation: "pulse-glow 2s ease-in-out infinite",
            }} />
            Work in Progress
          </div>
        )}

        <Link href="/" className="btn btn-outline" style={{ marginTop: comingSoon ? 0 : 0 }}>
          <ArrowLeftIcon />
          Back to Home
        </Link>
      </div>
    </div>
  );
}
