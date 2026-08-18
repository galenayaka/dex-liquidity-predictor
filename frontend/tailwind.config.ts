import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        noir: {
          bg: "#000000",
          panel: "var(--noir-panel)",
          panel2: "var(--noir-panel2)",
          line: "var(--noir-line)",
          line2: "var(--noir-line2)",
          amber: "var(--noir-accent)",
          orange: "var(--noir-accent2)",
          text: "var(--noir-text)",
          muted: "var(--noir-muted)",
          dim: "var(--noir-dim)",
          blood: "var(--noir-danger)",
        },
      },
      fontFamily: {
        mono: [
          "var(--font-jetbrains)",
          "'JetBrains Mono'",
          "'Roboto Mono'",
          "'SF Mono'",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
