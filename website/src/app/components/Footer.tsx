import Link from "next/link";

const TOOL_LINKS = [
  { href: "/maps",    label: "Maps" },
  { href: "/items",   label: "Items Database" },
  { href: "/classes", label: "Classes & Builds" },
  { href: "/quests",  label: "Quests" },
  { href: "/market",  label: "Market Prices" },
];

const RESOURCE_LINKS = [
  { href: "/classes", label: "Tier Lists" },
  { href: "/items",   label: "Best In Slot" },
  { href: "/quests",  label: "Quest Guides" },
  { href: "/maps",    label: "Dungeon Maps" },
];

const COMMUNITY_LINKS = [
  { href: "https://discord.gg/darkanddarker", label: "Discord", external: true },
  { href: "https://reddit.com/r/DarkAndDarker", label: "Reddit", external: true },
  { href: "#", label: "Contribute Data" },
  { href: "#", label: "Report a Bug" },
];

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-grid">
          {/* Brand */}
          <div>
            <div className="footer-brand-name">Dark &amp; Darker Tools</div>
            <p className="footer-brand-desc">
              A community-built database and toolset for Dark and Darker.
              Browse items, plan builds, track quests, and explore every dungeon.
            </p>
            <p className="footer-brand-disclaimer">
              This site is not affiliated with IRONMACE Co., Ltd.
              All game content and assets are property of their respective owners.
              Dark and Darker™ is a trademark of IRONMACE Co., Ltd.
            </p>
          </div>

          {/* Tools */}
          <div>
            <div className="footer-col-title">Tools</div>
            <ul className="footer-links">
              {TOOL_LINKS.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="footer-link">{l.label}</Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources */}
          <div>
            <div className="footer-col-title">Resources</div>
            <ul className="footer-links">
              {RESOURCE_LINKS.map((l) => (
                <li key={l.label}>
                  <Link href={l.href} className="footer-link">{l.label}</Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Community */}
          <div>
            <div className="footer-col-title">Community</div>
            <ul className="footer-links">
              {COMMUNITY_LINKS.map((l) => (
                <li key={l.label}>
                  {l.external ? (
                    <a
                      href={l.href}
                      className="footer-link"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {l.label}
                    </a>
                  ) : (
                    <Link href={l.href} className="footer-link">{l.label}</Link>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <span className="footer-copy">
            © {year} Dark &amp; Darker Tools — Community Project
          </span>
          <div className="footer-social">
            <a href="https://discord.gg/darkanddarker" className="navbar-icon-btn" aria-label="Discord" target="_blank" rel="noopener noreferrer">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057c.001.022.01.043.027.055a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/>
              </svg>
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
