/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Legacy aliases (keep for compat)
        navy:           '#1e293b',
        'navy-light':   '#334155',
        'navy-dark':    '#0f172a',
        'status-green': '#22c55e',
        'status-yellow':'#eab308',
        'status-red':   '#ef4444',
        // Midnight palette
        mid: {
          950: '#050a14',
          900: '#080d1a',
          800: '#0d1526',
          750: '#0f1a2e',
          700: '#111e38',
          600: '#162445',
          500: '#1e3060',
          400: '#243870',
          border:        '#1a2a4a',
          'border-strong':'#223870',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        'glow-blue': '0 0 24px rgba(59,130,246,0.18), 0 0 0 1px rgba(59,130,246,0.12)',
        'glow-cyan': '0 0 24px rgba(6,182,212,0.15), 0 0 0 1px rgba(6,182,212,0.1)',
        'dark-sm':   '0 1px 4px rgba(0,0,0,0.5), 0 0 0 1px rgba(26,42,74,0.7)',
        'dark-md':   '0 4px 20px rgba(0,0,0,0.55), 0 0 0 1px rgba(26,42,74,0.7)',
        'dark-lg':   '0 8px 36px rgba(0,0,0,0.65), 0 0 0 1px rgba(26,42,74,0.7)',
        'dark-xl':   '0 16px 52px rgba(0,0,0,0.75), 0 0 0 1px rgba(26,42,74,0.7)',
      },
      backgroundImage: {
        'gradient-midnight': 'linear-gradient(135deg, #050a14 0%, #080d1a 50%, #0a1020 100%)',
        'gradient-card':     'linear-gradient(135deg, #0d1526 0%, #111e38 100%)',
        'gradient-accent':   'linear-gradient(135deg, #1d4ed8 0%, #0891b2 100%)',
      },
    },
  },
  plugins: [],
}
