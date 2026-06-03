/** @type {import('tailwindcss').Config} */
// Single light theme ("Paper"). Semantic colours map to CSS custom properties so
// every utility stays token-driven — no dark mode, by design.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        "surface-1": "var(--surface-1)",
        "surface-2": "var(--surface-2)",
        "surface-3": "var(--surface-3)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        text: "var(--text)",
        "text-muted": "var(--text-muted)",
        "text-faint": "var(--text-faint)",
        primary: "var(--primary)",
        "primary-hover": "var(--primary-hover)",
        "primary-tint": "var(--primary-tint)",
        hazard: "var(--hazard)",
        "hazard-tint": "var(--hazard-tint)",
        success: "var(--success)",
        "success-tint": "var(--success-tint)",
        warning: "var(--warning)",
        "warning-tint": "var(--warning-tint)",
        info: "var(--info)",
        "info-tint": "var(--info-tint)",
      },
      fontFamily: {
        // Display / brand voice.
        display: ['"Space Grotesk Variable"', "Space Grotesk", "Georgia", "serif"],
        // UI, body and data.
        sans: ['"Inter Variable"', "Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono Variable"', "JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: { card: "14px", control: "10px", modal: "18px", pill: "999px" },
      boxShadow: {
        soft: "var(--shadow-soft)",
        card: "var(--shadow-card)",
        lift: "var(--shadow-lift)",
        pop: "var(--shadow-pop)",
      },
      keyframes: {
        "fade-in": { from: { opacity: 0 }, to: { opacity: 1 } },
        "slide-up": {
          from: { opacity: 0, transform: "translateY(6px)" },
          to: { opacity: 1, transform: "translateY(0)" },
        },
        "scale-in": {
          from: { opacity: 0, transform: "scale(0.97)" },
          to: { opacity: 1, transform: "scale(1)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.2s ease both",
        "slide-up": "slide-up 0.24s cubic-bezier(0.16,1,0.3,1) both",
        "scale-in": "scale-in 0.18s cubic-bezier(0.16,1,0.3,1) both",
      },
    },
  },
  plugins: [],
};
