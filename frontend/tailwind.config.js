/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#D4A843',
          light: '#E8C36A',
          dark: '#B8912E',
          50: '#FBF5E8',
          100: '#F5E8CC',
          200: '#ECDA9E',
          300: '#E2C36A',
          400: '#D4A843',
          500: '#C49A2E',
          600: '#A47E24',
          700: '#7D601B',
          800: '#574313',
          900: '#30250A',
        },
        dark: {
          DEFAULT: '#0A0A0A',
          50: '#1A1A1A',
          100: '#151515',
          200: '#121212',
        },
        surface: {
          DEFAULT: '#1A1A1A',
          light: '#222222',
          dark: '#111111',
        },
        border: {
          DEFAULT: '#2A2A2A',
          light: '#333333',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        display: ['var(--font-playfair)', 'Georgia', 'serif'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'hero-pattern': 'linear-gradient(135deg, #0A0A0A 0%, #1A1A1A 50%, #0A0A0A 100%)',
      },
    },
  },
  plugins: [],
};
