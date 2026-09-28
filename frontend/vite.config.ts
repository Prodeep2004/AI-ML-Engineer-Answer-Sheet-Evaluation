import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Dev: the React app on :5173 proxies API + page images to FastAPI on :8000 (no CORS, one origin).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/files': 'http://127.0.0.1:8000',
    },
  },
})
