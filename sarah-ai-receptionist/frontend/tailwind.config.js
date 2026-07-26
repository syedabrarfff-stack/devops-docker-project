/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          500: "#3568e8",
          600: "#2650c9",
          700: "#1e3fa3",
          900: "#152c73",
        },
      },
    },
  },
  plugins: [],
};
