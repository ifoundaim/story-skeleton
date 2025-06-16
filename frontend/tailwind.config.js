/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        meadow: '#ccff99',
        forest: '#006600',
      },
    },
  },
  plugins: [],
};
