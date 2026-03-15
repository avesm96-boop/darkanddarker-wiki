import type { Metadata } from "next";
import ItemSearch from "./ItemSearch";

export const metadata: Metadata = {
  title: "Items Database — Dark & Darker Wiki",
  description: "Every item in Dark and Darker with drop rates, dungeon locations, difficulty breakdowns, and source information.",
};

export default function ItemsPage() {
  return <ItemSearch />;
}
