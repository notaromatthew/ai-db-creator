import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: true,
    css: true,
  },
  define: { 'process.env': {} },
  server: { port: 3000 },
  resolve: { alias: { '@': '/src' } }
})


