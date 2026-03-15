import type { Metadata } from "next";
import QuestsPage from "./QuestsPage";

export const metadata: Metadata = {
  title: "Quests — Dark and Darker Wiki",
  description:
    "All 553 quests across every merchant in Dark and Darker. Browse quest chains, prerequisites, and rewards for every NPC.",
};

export default function Page() {
  return <QuestsPage />;
}
