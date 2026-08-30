import { JetBrains_Mono } from "next/font/google";
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import ThemeProvider from "@/components/ThemeProvider";
import "./globals.css";

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "DEX Liquidity Predictor",
  description:
    "Predictive liquidity & price impact analytics for Uniswap v3 pools",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#000000",
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en" className={jetbrains.variable}>
      <body className="font-mono">
        <script
          suppressHydrationWarning
          dangerouslySetInnerHTML={{
            __html:
              "try{var t=localStorage.getItem('noir-theme');if(t&&['amber','green','cyan','red','magenta','white'].indexOf(t)>-1)document.documentElement.setAttribute('data-theme',t)}catch(e){}",
          }}
        />
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
