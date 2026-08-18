export type ThemeId = "amber" | "green" | "cyan" | "red" | "magenta" | "white";

export interface ThemeOption {
  id: ThemeId;
  label: string;
  /** Preview swatch shown in the theme picker (not a themed element). */
  swatch: string;
}

export const THEMES: ThemeOption[] = [
  { id: "amber", label: "Amber", swatch: "#ffb000" },
  { id: "green", label: "Green", swatch: "#00ff66" },
  { id: "cyan", label: "Cyan", swatch: "#00e5ff" },
  { id: "red", label: "Red", swatch: "#ff4d4d" },
  { id: "magenta", label: "Magenta", swatch: "#ff2e97" },
  { id: "white", label: "White", swatch: "#e8e8e8" },
];
