import { NextRequest, NextResponse } from "next/server";

const UPSTREAM = "http://5.161.247.74:8080/api/v1";

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } },
) {
  const path = params.path.join("/");
  const search = request.nextUrl.search;
  const url = `${UPSTREAM}/${path}${search}`;

  try {
    const res = await fetch(url, {
      headers: { Accept: "application/json" },
      next: { revalidate: 10 }, // Cache for 10 seconds on Vercel edge
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
