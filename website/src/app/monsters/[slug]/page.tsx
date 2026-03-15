import fs from "fs";
import path from "path";
import MonsterDetail from "./MonsterDetail";

interface MonstersData {
  monsters: { slug: string }[];
}

export async function generateStaticParams() {
  const filePath = path.join(process.cwd(), "public", "data", "monsters.json");
  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    const data: MonstersData = JSON.parse(raw);
    return data.monsters.map((m) => ({ slug: m.slug }));
  } catch {
    return [];
  }
}

export default async function MonsterPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <MonsterDetail slug={slug} />;
}
