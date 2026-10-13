/** @type {import('tailwindcss').Config} */
// Tema TecnIA: la palette "blue/indigo" usata dai componenti esistenti viene
// rimappata sull'arancione del marchio, cosi' tutta l'app cambia aspetto in un colpo.
const orange = {
  50: '#fff4ec', 100: '#ffe4d1', 200: '#ffc8a3', 300: '#ffa468', 400: '#ff8433',
  500: '#ff6b00', 600: '#e65f00', 700: '#a04100', 800: '#823600', 900: '#6b2f00', 950: '#3a1700',
}
export default {
  darkMode: 'class',
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        blue: orange,
        indigo: { ...orange, 500: '#fe3ac6', 600: '#b20088', 700: '#8f006e' },
        tecnia: {
          primary: '#a04100', orange: '#ff6b00', magenta: '#fe3ac6', magentaDeep: '#b20088',
          bg: '#f8f9fa', ink: '#191c1d', muted: '#5a4136', line: '#e2bfb0', ok: '#1b7a43',
        },
      },
      fontFamily: {
        headline: ['Geist', 'Inter', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: { glass: '0 4px 20px rgba(26,34,51,.08)' },
    },
  },
  plugins: [],
}
