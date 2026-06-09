/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Cormorant Garamond"', 'Georgia', 'serif'],
        sans:    ['"DM Sans"', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Core palette — used throughout components
        soil: {
          green:  '#1B4332',
          dgreen: '#0F2A1E',
          amber:  '#C4622D',
          red:    '#9B2335',
          gold:   '#D4A853',
          cream:  '#F4F1EC',
          earth:  '#6B6560',
        },
        forest: {
          950: '#0A1F14', 900: '#1B4332', 800: '#245c43',
          700: '#2D6A4F', 600: '#40916C', 500: '#52B788',
          400: '#74C69D', 300: '#95D5B2', 200: '#B7E4C7',
          100: '#D8F3DC', 50:  '#F0FFF4',
        },
        earth: {
          950: '#1C1714', 900: '#2C2320', 800: '#3D3229',
          700: '#4F4440', 600: '#6B6560', 500: '#8A8480',
          400: '#A89E97', 300: '#C5BFB8', 200: '#DDD8D0',
          100: '#EDE8E0', 50:  '#F4F1EC',
        },
        amber: {
          700: '#92400E', 600: '#B45309', 500: '#D4A853',
          400: '#FBBF24', 300: '#FDE68A', 100: '#FEF9E7',
        },
        crimson: {
          800: '#6B1226', 700: '#831929', 600: '#9B2335',
          400: '#C4314B', 200: '#F9B8C4', 100: '#FDE8EC',
        },
        terra: {
          700: '#9A3412', 600: '#B84C25', 500: '#C4622D',
          400: '#D97A47', 100: '#FEF0E8',
        },
      },
      boxShadow: {
        'card':    '0 1px 3px rgba(28,23,20,0.06), 0 4px 16px rgba(28,23,20,0.05)',
        'card-lg': '0 4px 8px rgba(28,23,20,0.06), 0 16px 40px rgba(28,23,20,0.08)',
        'inset-t': 'inset 0 2px 0 0 var(--tw-shadow-color)',
      },
      backgroundImage: {
        'grain': "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E\")",
      },
    },
  },
  plugins: [],
}
