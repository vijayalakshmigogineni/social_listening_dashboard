import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        // SLD_API_URL points the dev server at another backend (default: local API).
        target: process.env.SLD_API_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
