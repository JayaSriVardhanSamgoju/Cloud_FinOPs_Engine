/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          0: "#0A0B0D",
          1: "#111318",
          2: "#171A21",
          3: "#1E222B",
        },
        border: {
          DEFAULT: "rgba(255,255,255,0.06)",
          hover: "rgba(255,255,255,0.12)",
          accent: "rgba(94,255,176,0.3)",
        },
        text: {
          primary: "#EDEEF0",
          secondary: "#9498A3",
          tertiary: "#5A5E6B",
        },
        pulse: {
          DEFAULT: "#5EFFB0",
          dim: "#2D5C44",
        },
        status: {
          healthy: "#5EFFB0",
          warning: "#FFB84D",
          critical: "#FF5C5C",
          info: "#5CB8FF",
        },
      },
      fontFamily: {
        sans: ["Geist", "Space Grotesk", "sans-serif"],
        mono: ["JetBrains Mono", "IBM Plex Mono", "monospace"],
      },
      fontSize: {
        "data-xl": ["2.5rem", { lineHeight: "1", fontWeight: "600", letterSpacing: "-0.02em" }],
        "data-lg": ["1.75rem", { lineHeight: "1.1", fontWeight: "600" }],
        "data-md": ["1.125rem", { lineHeight: "1.2", fontWeight: "500" }],
        label: ["0.75rem", { lineHeight: "1", fontWeight: "500", letterSpacing: "0.08em" }],
      },
      borderRadius: {
        DEFAULT: "6px",
        lg: "8px",
      },
      keyframes: {
        "pulse-dot": {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.4", transform: "scale(0.85)" },
        },
        "draw-line": {
          from: { strokeDashoffset: "1000" },
          to: { strokeDashoffset: "0" },
        },
        "slide-up-fade": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "scan-line": {
          from: { transform: "translateY(-100%)" },
          to: { transform: "translateY(100%)" },
        },
      },
      animation: {
        "pulse-dot": "pulse-dot 1.6s ease-in-out infinite",
        "draw-line": "draw-line 1.2s ease-out forwards",
        "slide-up-fade": "slide-up-fade 0.4s ease-out forwards",
        "scan-line": "scan-line 3s linear infinite",
      },
    },
  },
  plugins: [],
};
