import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "DEX Liquidity Predictor",
  description:
    "Predictive liquidity & price impact analytics for Uniswap v3 pools",
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-950 antialiased">{children}</body>
    </html>
  );
}
