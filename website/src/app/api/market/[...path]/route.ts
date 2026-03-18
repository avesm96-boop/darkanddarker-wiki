import { NextRequest, NextResponse } from "next/server";

const UPSTREAM = process.env.MARKET_API_URL ?? "";

const ALLOWED_PATHS = new Set([
  "listings", "prices/history", "items", "trending", "stats",
  "market/activity",
  "rmt/stats", "rmt/listings", "rmt/sellers",
]);

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } },
) {
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
