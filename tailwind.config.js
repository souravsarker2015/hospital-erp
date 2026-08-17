/** @type {import('tailwindcss').Config} */
// Same design tokens as templates/components/design_tokens.html (marketing's
// CDN-based Tailwind config) — kept in sync by hand since marketing stays on
// the CDN build and the authenticated app uses this CLI build.
module.exports = {
  content: ["./templates/**/*.html", "./apps/**/templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#EDF6F5", 100: "#D3E8E6", 200: "#A8D1CC", 300: "#78B7AF",
          400: "#4B9A91", 500: "#2C7C73", 600: "#1C645C", 700: "#144F49",
          800: "#0F3D38", 900: "#0A2B28", 950: "#061A18",
        },
        accent: {
          50: "#FFF4EA", 100: "#FFE3C7", 200: "#FFC98C", 300: "#FFAA52",
          400: "#FB8B2B", 500: "#ED6F14", 600: "#C8560D", 700: "#A1420D",
          800: "#7C3310", 900: "#5E280F",
        },
        paper: "#FAF7F1",
        ink: "#10201E",
      },
      fontFamily: {
        display: ['"Manrope"', "sans-serif"],
        sans: ['"Inter"', "sans-serif"],
      },
    },
  },
  plugins: [],
};
