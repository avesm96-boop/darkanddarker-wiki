import Link from "next/link";

const NAV_LINKS = [
  { href: "/",       label: "Home" },
  { href: "/maps",   label: "Maps" },
  { href: "/items",    label: "Item Finder" },
  { href: "/monsters", label: "Monsters" },
  { href: "/classes",  label: "Classes" },
  { href: "/stats",   label: "Stats" },
  { href: "/quests", label: "Quests" },
  { href: "/market", label: "Market" },
];

function SkullIcon() {
  return (
    <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="navbar-logo-icon">
      {/* Skull shape */}
      <path
        d="M20 4C12.268 4 6 10.268 6 18c0 4.418 1.93 8.386 5 11.09V30a1 1 0 001 1h16a1 1 0 001-1v-.91C32.07 26.386 34 22.418 34 18c0-7.732-6.268-14-14-14z"
        fill="currentColor"
        fillOpacity="0.85"
      />
      {/* Eyes */}
      <circle cx="14.5" cy="17" r="3.5" fill="var(--bg-void)" />
      <circle cx="25.5" cy="17" r="3.5" fill="var(--bg-void)" />
      {/* Teeth */}
      <path d="M14 32h3v3h-3zM20 32h3v3h-3z" fill="currentColor" fillOpacity="0.6" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8"/>
      <path d="m21 21-4.35-4.35"/>
    </svg>
  );
}

function DiscordIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057c.001.022.01.043.027.055a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/>
    </svg>
  );
}

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="container navbar-inner">
        <Link href="/" className="navbar-logo">
          <SkullIcon />
          <div className="navbar-logo-text">
            <span className="navbar-logo-name">D&amp;D Tools</span>
            <span className="navbar-logo-sub">Community Database</span>
          </div>
        </Link>

        <ul className="navbar-links">
          {NAV_LINKS.map((link, i) => (
            <>
              {i > 0 && <li key={`sep-${i}`} className="navbar-sep" aria-hidden />}
              <li key={link.href}>
                <Link href={link.href} className="navbar-link">
                  {link.label}
                </Link>
              </li>
            </>
          ))}
        </ul>

        <div className="navbar-right">
          <a
            href="https://discord.gg/2k8JXHvhzE"
            className="navbar-icon-btn"
            aria-label="Discord"
            target="_blank"
            rel="noopener noreferrer"
          >
            <DiscordIcon />
          </a>
        </div>
      </div>
    </nav>
  );
}
