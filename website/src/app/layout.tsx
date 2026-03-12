import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dark and Darker Wiki",
  description:
    "Community wiki for Dark and Darker — items, classes, monsters, maps, and more.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
