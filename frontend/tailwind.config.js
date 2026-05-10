/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        jarvis: {
          blue: '#00d4ff',
          purple: '#7c3aed',
          dark: '#0a0a0f',
          card: '#0f0f1a',
          border: '#1a1a2e',
          glow: 'rgba(0,212,255,0.15)',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        pulse_slow: 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        glow: 'glow 2s ease-in-out infinite alternate',
        scan: 'scan 3s linear infinite',
      },
      keyframes: {
        glow: {
          from: { boxShadow: '0 0 10px #00d4ff33' },
          to:   { boxShadow: '0 0 30px #00d4ff88, 0 0 60px #00d4ff33' },
        },
        scan: {
          '0%':   { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
      },
      backdropBlur: { xs: '2px' },
    },
  },
  plugins: [],
}
