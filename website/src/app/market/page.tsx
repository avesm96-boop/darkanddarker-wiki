import type { Metadata } from "next";
import MarketPage from "./MarketPage";

export const metadata: Metadata = {
  title: "Market — Dark and Darker Wiki",
  description:
    "Live marketplace prices, trending items, and active trade listings for Dark and Darker.",
};

export default function Page() {
  return <MarketPage />;
}
