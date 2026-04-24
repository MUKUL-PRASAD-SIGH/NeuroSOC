export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        soc: {
          bg: "#0a0e1a",
          panel: "#0f1528",
          panelSoft: "#121c33",
          border: "#233252",
          text: "#e7f1ff",
          muted: "#8ca1c8",
          electric: "#19e6ff",
          red: "#ff4d5a",
          amber: "#ffbe3d",
          green: "#34e7a1",
        },
      },
      fontFamily: {
        sans: ["'Space Grotesk'", "'IBM Plex Sans'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
        display: ["'Orbitron'", "'Space Grotesk'", "sans-serif"],
      },
    },
  },
  plugins: [],
};
