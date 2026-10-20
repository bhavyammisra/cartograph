import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // The Python API (`cartograph serve`) runs separately; the dev server forwards /api to it.
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})
