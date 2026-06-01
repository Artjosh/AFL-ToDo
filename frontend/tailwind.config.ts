import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta escura inspirada no projeto ats-example (acentos roxos).
        bg: "#0c0e14",
        surface: "#1a1c2e",
        "surface-2": "#23263b",
        border: "#2a2c3e",
        accent: "#6C5CE7",
        "accent-hover": "#7c6ef7",
        "accent-soft": "#aca3ff",
        muted: "#aaaab3",
        foreground: "#e5e4ed",
        success: "#22c55e",
        danger: "#ef4444",
        warning: "#f59e0b",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      keyframes: {
        "toast-in": {
          "0%": { opacity: "0", transform: "translateX(120%)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "toast-out": {
          "0%": { opacity: "1", transform: "translateX(0)" },
          "100%": { opacity: "0", transform: "translateX(120%)" },
        },
      },
      animation: {
        "toast-in": "toast-in 0.25s ease-out",
        "toast-out": "toast-out 0.2s ease-in forwards",
      },
    },
  },
  plugins: [],
};

export default config;
