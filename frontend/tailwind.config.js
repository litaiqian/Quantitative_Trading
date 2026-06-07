/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0a0a0f',
          800: '#12121a',
          700: '#1a1a2e',
          600: '#25253e',
        },
        brand: {
          blue: '#6366f1',
          purple: '#a855f7',
          cyan: '#06b6d4',
          green: '#10b981',
          red: '#ef4444',
        }
      }
    },
  },
  plugins: [],
}
