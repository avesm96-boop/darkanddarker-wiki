import fs from "fs";
import path from "path";
import ClassDetail from "./ClassDetail";

interface ClassesData {
  version: string;
  generated_at: string;
  data: {
    classes: { slug: string }[];
  };
}

export async function generateStaticParams() {
  const filePath = path.join(process.cwd(), "public", "data", "classes.json");
  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    const data: ClassesData = JSON.parse(raw);
    return data.data.classes.map((c) => ({ slug: c.slug }));
  } catch {
    return [];
  }
}

export default async function ClassPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <ClassDetail slug={slug} />;
}
