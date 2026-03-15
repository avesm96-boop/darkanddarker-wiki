import Link from "next/link";
import Image from "next/image";
import ScrollReveal from "./components/ScrollReveal";
import AnimatedCounter from "./components/AnimatedCounter";

/* ─── SVG Icons ─────────────────────────────────────────────────────────── */

function MapIcon() {
  return (
    <svg className="tool-card-icon" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M26 6L6 14v26l14-6 12 6 14-6V8L32 14z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" fill="none"/>
      <path d="M20 8v24M32 14v24" stroke="currentColor" strokeWidth="1.5"/>
      <circle cx="26" cy="26" r="3" fill="currentColor" opacity="0.5"/>
      <path d="M26 14v4M26 34v4M14 26h4M34 26h4" stroke="currentColor" strokeWidth="1" opacity="0.4"/>
    </svg>
  );
}

function SwordIcon() {
  return (
    <svg className="tool-card-icon" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M38 8L44 14 20 38l-6-6z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" fill="currentColor" fillOpacity="0.15"/>
      <path d="M14 38L8 44M8 44l6-2M8 44l2-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M36 10l6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.5"/>
      <path d="M22 20l10 10" stroke="currentColor" strokeWidth="1" opacity="0.3" strokeLinecap="round"/>
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg className="tool-card-icon" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M26 6L8 13v14c0 10 8 18 18 18s18-8 18-18V13L26 6z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" fill="currentColor" fillOpacity="0.08"/>
      <path d="M26 14v16M18 22h16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.6"/>
      <path d="M26 6v8M8 13l8 3M44 13l-8 3" stroke="currentColor" strokeWidth="1" opacity="0.3" strokeLinecap="round"/>
    </svg>
  );
}

function ScrollIcon() {
  return (
    <svg className="tool-card-icon" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 8h28a4 4 0 010 8H12V8z" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.08"/>
      <path d="M12 16v24a4 4 0 01-4-4V12a4 4 0 014 4z" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M12 40h28a4 4 0 100-8H12" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M20 22h16M20 28h12M20 34h8" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5"/>
    </svg>
  );
}

function CoinsIcon() {
  return (
    <svg className="tool-card-icon" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="30" cy="30" r="14" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.08"/>
      <circle cx="22" cy="22" r="14" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.12"/>
      <path d="M22 16v3M22 25v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M18 19h6a2 2 0 010 4h-4a2 2 0 000 4h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

function ChestIcon() {
  return (
    <svg className="tool-card-icon" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="6" y="20" width="40" height="24" rx="2" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.08"/>
      <path d="M6 28h40" stroke="currentColor" strokeWidth="1.5"/>
      <rect x="14" y="8" width="24" height="12" rx="2" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.12"/>
      <rect x="22" y="25" width="8" height="6" rx="1" stroke="currentColor" strokeWidth="1.5"/>
      <circle cx="26" cy="28" r="1.5" fill="currentColor" opacity="0.5"/>
    </svg>
  );
}

function ArrowRightIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <path d="M5 12h14M12 5l7 7-7 7"/>
    </svg>
  );
}

/* ─── Data ───────────────────────────────────────────────────────────────── */

const TOOLS = [
  {
    href: "/maps",
    label: "Exploration",
    title: "Maps",
    desc: "Interactive dungeon maps with loot locations, monster spawns, extraction points and trap placements.",
    Icon: MapIcon,
    status: "live" as const,
    count: "8 dungeons",
  },
  {
    href: "/items",
    label: "Arsenal",
    title: "Items",
    desc: "Complete weapon, armor and gear database with stats, rarity tiers, and synergy breakdowns.",
    Icon: SwordIcon,
    status: "live" as const,
    count: "2,847 items",
  },
  {
    href: "/classes",
    label: "Roster",
    title: "Classes",
    desc: "Every class with full perk trees, skill breakdowns, best-in-slot gear recommendations and tier ratings.",
    Icon: ShieldIcon,
    status: "live" as const,
    count: "12 classes",
  },
  {
    href: "/quests",
    label: "Objectives",
    title: "Quests",
    desc: "Quest tracker with merchant unlock requirements, reward previews, and optimal completion order.",
    Icon: ScrollIcon,
    status: "live" as const,
    count: "553 quests",
  },
  {
    href: "/market",
    label: "Economy",
    title: "Market",
    desc: "Live marketplace prices, trading post valuations, and merchant inventory with affinity requirements.",
    Icon: CoinsIcon,
    status: "soon" as const,
    count: "Coming soon",
  },
  {
    href: "#",
    label: "Discover",
    title: "More",
    desc: "Leaderboards, achievements, season tracking and additional tools arriving in future updates.",
    Icon: ChestIcon,
    status: "soon" as const,
    count: "In progress",
  },
];

const STATS = [
  { value: "2,847",  label: "Items" },
  { value: "553",    label: "Quests" },
  { value: "12",     label: "Classes" },
  { value: "8",      label: "Dungeons" },
];

const CLASSES = [
  { id: "fighter",   name: "Fighter",   role: "Frontline warrior",  img: "/portraits/fighter.png" },
  { id: "barbarian", name: "Barbarian", role: "Berserker",          img: "/portraits/barbarian.png" },
  { id: "rogue",     name: "Rogue",     role: "Stealth specialist", img: "/portraits/rogue.png" },
  { id: "ranger",    name: "Ranger",    role: "Ranged marksman",    img: "/portraits/ranger.png" },
  { id: "wizard",    name: "Wizard",    role: "Arcane caster",      img: "/portraits/wizard.png" },
  { id: "cleric",    name: "Cleric",    role: "Holy support",       img: "/portraits/cleric.png" },
  { id: "bard",      name: "Bard",      role: "Support & utility",  img: "/portraits/bard.png" },
  { id: "warlock",   name: "Warlock",   role: "Dark mage",          img: "/portraits/warlock.png" },
  { id: "druid",     name: "Druid",     role: "Shapeshifter",       img: "/portraits/druid.png" },
  { id: "sorcerer",  name: "Sorcerer",  role: "Chaos caster",       img: "/portraits/sorcerer.png" },
];

const FEATURES = [
  {
    title: "Always Up To Date",
    desc: "Data pipeline extracts directly from game files. Every patch is reflected within hours.",
    icon: (
      <svg className="feature-icon" viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M20 8v8l6 3" strokeLinecap="round"/>
        <circle cx="20" cy="24" r="12"/>
        <path d="M8 8l4 4M32 8l-4 4" strokeLinecap="round" opacity="0.4"/>
      </svg>
    ),
  },
  {
    title: "Community Driven",
    desc: "Built by players, for players. All data is open source and contributions are welcome.",
    icon: (
      <svg className="feature-icon" viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="14" cy="14" r="5"/>
        <circle cx="26" cy="14" r="5"/>
        <path d="M6 32c0-5.523 3.582-10 8-10h12c4.418 0 8 4.477 8 10"/>
      </svg>
    ),
  },
  {
    title: "No Ads, No Bloat",
    desc: "Fast, clean, and focused. Find what you need without fighting through paywalls or popups.",
    icon: (
      <svg className="feature-icon" viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M8 20L16 28 32 12" strokeLinecap="round" strokeLinejoin="round"/>
        <circle cx="20" cy="20" r="14"/>
      </svg>
    ),
  },
];

/* ─── Page ───────────────────────────────────────────────────────────────── */

export default function HomePage() {
  return (
    <>
      {/* ── Notice ─────────────────────────────────────────────────────── */}
      <div className="notice-bar">
        <div className="container notice-inner">
          <span className="notice-icon">&#9878;</span>
          <p className="notice-text">
            This website and its tools are <strong>not to be shared or promoted</strong> in the
            Dark and Darker Knights Discord server, now or in the future.
          </p>
        </div>
      </div>

      {/* ── Hero ───────────────────────────────────────────────────────── */}
      <section className="hero">
        <div className="hero-bg" />
        <div className="hero-bg-img" />
        <div className="hero-grain" />
        <div className="hero-grid" aria-hidden />

        {/* Floating embers — more particles */}
        <div className="hero-embers" aria-hidden>
          {Array.from({ length: 12 }).map((_, n) => (
            <span key={n} className="hero-ember" />
          ))}
        </div>

        <div className="hero-content">
          <div className="hero-eyebrow">
            <span className="hero-eyebrow-dot" />
            Community Tools &amp; Database
            <span className="hero-eyebrow-dot" />
          </div>

          <h1 className="hero-title">
            Dark
            <span className="hero-title-amp">&amp;</span>
            Darker
          </h1>

          <p className="hero-tagline">
            The Complete Tools &amp; Database for the Dungeon
          </p>

          <div className="hero-actions">
            <Link href="/items" className="btn btn-primary">
              Browse Items
              <ArrowRightIcon />
            </Link>
            <Link href="/maps" className="btn btn-outline">
              Explore Maps
            </Link>
          </div>
        </div>

        <div className="hero-scroll" aria-hidden>
          <div className="hero-scroll-line" />
          <span>Scroll</span>
        </div>
      </section>

      {/* ── Stats Bar ──────────────────────────────────────────────────── */}
      <div className="stats-bar">
        <div className="stats-inner">
          {STATS.map((s) => (
            <div key={s.label} className="stat-item">
              <AnimatedCounter value={s.value} className="stat-value" />
              <span className="stat-label">{s.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Tools Grid — Bento Layout ─────────────────────────────────── */}
      <section className="tools-section">
        <div className="container">
          <ScrollReveal>
            <div className="section-head">
              <span className="section-label">Choose Your Path</span>
              <h2 className="section-title">The Arsenal</h2>
              <p className="section-desc">
                Everything you need to survive the darkness. From dungeon maps to full item databases,
                your edge starts here.
              </p>
            </div>
          </ScrollReveal>

          <div className="tools-grid">
            {TOOLS.map((tool, i) => (
              <ScrollReveal key={tool.title} delay={i * 80}>
                <Link href={tool.href} className="tool-card">
                  <tool.Icon />
                  <div className="tool-card-label">{tool.label}</div>
                  <div className="tool-card-title">{tool.title}</div>
                  <p className="tool-card-desc">{tool.desc}</p>
                  <div className="tool-card-footer">
                    <span className="tool-card-cta">
                      Explore
                      <ArrowRightIcon />
                    </span>
                    <span className={`tool-card-status tool-card-status--${tool.status}`}>
                      {tool.count}
                    </span>
                  </div>
                </Link>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Announcement ───────────────────────────────────────────────── */}
      <ScrollReveal>
        <div className="announce-section">
          <div className="container announce-inner">
            <span className="announce-badge">Update</span>
            <p className="announce-text">
              <strong>Season data refreshed.</strong> New items, quests, and dungeon changes from the latest patch are now live.
            </p>
            <a href="/items" className="announce-link">
              See what&apos;s new <ArrowRightIcon />
            </a>
          </div>
        </div>
      </ScrollReveal>

      {/* ── Classes Showcase ────────────────────────────────────────────── */}
      <section className="classes-section">
        <div className="container">
          <ScrollReveal>
            <div className="section-head">
              <span className="section-label">Choose Your Fighter</span>
              <h2 className="section-title">The Adventurers</h2>
              <p className="section-desc">
                Ten classes. Each with unique perks, skills, and playstyles.
                Find the one that fits your dungeon strategy.
              </p>
            </div>
          </ScrollReveal>
        </div>

        <ScrollReveal direction="left" distance={60}>
          <div className="classes-scroll-wrapper">
            <div className="classes-track">
              {CLASSES.map((cls) => (
                <Link key={cls.id} href={`/classes#${cls.id}`} className="class-card">
                  <Image
                    src={cls.img}
                    alt={cls.name}
                    width={190}
                    height={220}
                    className="class-portrait"
                  />
                  <div className="class-info">
                    <div className="class-name">{cls.name}</div>
                    <div className="class-role">{cls.role}</div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </ScrollReveal>
      </section>

      {/* ── Features ───────────────────────────────────────────────────── */}
      <section className="features-section">
        <div className="container">
          <div className="features-grid">
            {FEATURES.map((f, i) => (
              <ScrollReveal key={f.title} delay={i * 120}>
                <div className="feature-item">
                  {f.icon}
                  <div className="feature-title">{f.title}</div>
                  <p className="feature-desc">{f.desc}</p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
