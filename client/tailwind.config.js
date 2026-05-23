/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Playfair Display'", "serif"],
        body: ["'DM Sans'", "sans-serif"]
      },
      colors: {
        charcoal: "#1e1a1d",
        lavender: "#d9ccff",
        blush: "#ffd9e7",
        cream: "#faf8f5",
        mist: "#d9f0ff",
        plum: "#8f4760",
        rose: "#c2697b",
        petal: "#f2ece8",
        stone: "#8c7e7a"
      },
      boxShadow: {
        glow: "0 24px 80px rgba(194, 105, 123, 0.16)",
        soft: "0 18px 50px rgba(30, 26, 29, 0.10)",
        boty: "rgba(14, 63, 126, 0.04) 0px 0px 0px 1px, rgba(42, 51, 69, 0.04) 0px 1px 1px -0.5px, rgba(42, 51, 70, 0.04) 0px 3px 3px -1.5px, rgba(42, 51, 70, 0.04) 0px 6px 6px -3px, rgba(14, 63, 126, 0.04) 0px 12px 12px -6px, rgba(14, 63, 126, 0.04) 0px 24px 24px -12px"
      },
      keyframes: {
        "blur-in": {
          "0%": { opacity: "0", filter: "blur(12px)", transform: "translateY(22px)" },
          "100%": { opacity: "1", filter: "blur(0)", transform: "translateY(0)" }
        },
        "scan-line": {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" }
        }
      },
      animation: {
        "blur-in": "blur-in 0.7s cubic-bezier(0.22, 1, 0.36, 1) both",
        "scan-line": "scan-line 2.4s ease-in-out infinite"
      }
    }
  },
  plugins: []
};
