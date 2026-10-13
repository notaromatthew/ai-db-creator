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
        // I colori che cambiano con il tema leggono le variabili CSS di src/index.css
        // (chiaro in :root, scuro in .dark); arancione e magenta di marca restano fissi.
        tecnia: {
          primary: 'rgb(var(--tecnia-primary) / <alpha-value>)',
          orange: '#ff6b00', magenta: '#fe3ac6',
          magentaDeep: 'rgb(var(--tecnia-magenta-deep) / <alpha-value>)',
          bg: 'rgb(var(--tecnia-bg) / <alpha-value>)',
          ink: 'rgb(var(--tecnia-ink) / <alpha-value>)',
          muted: 'rgb(var(--tecnia-muted) / <alpha-value>)',
          line: 'rgb(var(--tecnia-line) / <alpha-value>)',
          ok: 'rgb(var(--tecnia-ok) / <alpha-value>)',
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
