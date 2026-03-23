// website/tailwind.config.mjs
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,ts,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        page: '#06090f',
        surface: '#0d1520',
        border: '#1a2640',
        'text-primary': '#f8fafc',
        'text-secondary': '#94a3b8',
        'text-muted': '#475569',
        accent: '#6366f1',
        cyan: '#22d3ee',
        'indigo-light': '#818cf8',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      backgroundImage: {
        'accent-gradient': 'linear-gradient(90deg, #818cf8, #22d3ee)',
      },
      borderRadius: {
        card: '10px',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
};
