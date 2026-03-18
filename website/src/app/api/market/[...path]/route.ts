import { NextRequest, NextResponse } from "next/server";

const UPSTREAM = process.env.MARKET_API_URL ?? "";

const ALLOWED_PATHS = new Set([
  "listings", "prices/history", "items", "trending", "stats",
  "market/activity",
  "rmt/stats", "rmt/listings", "rmt/sellers",
]);

// Allowed origins for same-site verification
const ALLOWED_ORIGINS = new Set([
  "https://dnd-community-tools.vercel.app",
  "https://www.dnd-community-tools.vercel.app",
  "http://localhost:3000",
]);

function isAllowedRequest(request: NextRequest): boolean {
  // Sec-Fetch-Site is set by the browser and CANNOT be spoofed by JavaScript.
  // "same-origin" means the request came from our own site's JS.
  const fetchSite = request.headers.get("sec-fetch-site");
  if (fetchSite === "same-origin") return true;

  // Fallback: check Origin header (also browser-controlled)
  const origin = request.headers.get("origin");
  if (origin && ALLOWED_ORIGINS.has(origin)) return true;

  // Fallback: check Referer for older browsers
  const referer = request.headers.get("referer");
  if (referer) {
    for (const allowed of ALLOWED_ORIGINS) {
      if (referer.startsWith(allowed)) return true;
    }
  }

  return false;
}

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } },
) {
  if (!isAllowedRequest(request)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const path = params.path.join("/");

  if (!ALLOWED_PATHS.has(path)) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  if (!UPSTREAM) {
    return NextResponse.json({ error: "Service unavailable" }, { status: 503 });
  }

  const search = request.nextUrl.search;
  const url = `${UPSTREAM}/${path}${search}`;

  try {
    const cacheOpts = path === "stats"
      ? { cache: "no-store" as const }
      : { next: { revalidate: 10 } };

    const res = await fetch(url, {
      headers: { Accept: "application/json" },
      ...cacheOpts,
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: "Service error" },
        { status: res.status },
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { error: "Service unavailable" },
      { status: 502 },
    );
  }
}
