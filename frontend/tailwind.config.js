/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      borderWidth: {
        "3": "3px",
      },
      animation: {
        'spin-slow': 'spin 1s linear infinite',
        'pulse-slow': 'pulse 1.5s ease infinite',
      },
      colors: {
        'dark-bg': '#1a1a2e',
        'dark-secondary': '#16213e',
        'accent': '#ffd700',
        'accent-blue': '#4a90e2',
      },
      animation: {
        "spin-slow" : "spin 1s linear infinite",
        "pulse-slow" : "pulse 1.5s ease infinite"
      }
    },
  },
  plugins: [],
}