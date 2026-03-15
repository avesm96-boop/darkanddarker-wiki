import type { Metadata } from "next";
import MapExplorer from "./MapExplorer";

export const metadata: Metadata = { title: "Dungeon Maps — Dark and Darker Wiki" };

export default function MapsPage() {
  return <MapExplorer />;
}
