/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: '#1e293b',
        'navy-light': '#334155',
        'navy-dark': '#0f172a',
        'status-green': '#22c55e',
        'status-yellow': '#eab308',
        'status-red': '#ef4444',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
