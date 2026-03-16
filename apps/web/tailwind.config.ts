import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-space-grotesk)"],
        mono: ["var(--font-ibm-plex-mono)"]
      },
      colors: {
        ink: "#07111f",
        panel: "#0d1b2f",
        line: "#1e3555",
        mist: "#d8e4f5",
        accent: "#48b3a7",
        amber: "#e8b65d",
        rose: "#da6b7f"
      },
      boxShadow: {
        panel: "0 30px 80px rgba(5, 12, 22, 0.38)"
      }
    }
  },
  plugins: []
};

export default config;

