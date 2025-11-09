import { fontFamily } from 'tailwindcss/defaultTheme';

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#300A55',
        secondary: '#EBEDFA'
      },
      fontFamily: {
        sans: ['Inter', ...fontFamily.sans],
        serif: ['Cormorant Garamond', ...fontFamily.serif]
      },
      boxShadow: {
        brand: '0 10px 30px rgba(48, 10, 85, 0.08)'
      }
    }
  },
  plugins: []
};
