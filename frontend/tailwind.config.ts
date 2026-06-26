import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0A1628",
        foreground: "#E8EDF2",
        civic: {
          navy: "#0A1628",
          teal: "#0D7377",
          "teal-light": "#14BDBC",
          amber: "#F4A261",
          coral: "#E76F51",
          surface: "#0F1F35",
          "surface-2": "#162840",
          border: "rgba(255,255,255,0.08)",
          text: "#E8EDF2",
          "text-muted": "#7A8FA6",
        },
        severity: {
          critical: "#EF233C",
          high: "#F4831F",
          medium: "#F7C59F",
          low: "#52B788",
        }
      },
      fontFamily: {
        display: ["Plus Jakarta Sans", "sans-serif"],
        body: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      }
    },
  },
  plugins: [],
};
export default config;
