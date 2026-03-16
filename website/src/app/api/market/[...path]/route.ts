import { NextRequest, NextResponse } from "next/server";

const UPSTREAM = "http://5.78.190.10:8080/api/v1";

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } },
) {
  const path = params.path.join("/");
  const search = request.nextUrl.search;
  const url = `${UPSTREAM}/${path}${search}`;

  try {
    // Skip cache for stats endpoint (needs real-time freshness indicator)
    const cacheOpts = path === "stats"
      ? { cache: "no-store" as const }
      : { next: { revalidate: 10 } };

    const res = await fetch(url, {
      headers: { Accept: "application/json" },
      ...cacheOpts,
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: `Upstream ${res.status}` },
        { status: res.status },
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      { error: "Marketplace API unavailable" },
      { status: 502 },
    );
  }
}
