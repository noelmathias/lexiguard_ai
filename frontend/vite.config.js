import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // In local dev, proxy /api to localhost backend to avoid CORS
  // In production (Vercel), VITE_API_BASE_URL is set — proxy is unused
  const backendUrl = env.VITE_API_BASE_URL || 'http://localhost:8000'

  return {
    plugins: [react()],
    build: {
      outDir: 'dist',
      sourcemap: false,
    },
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
        }
      }
    }
  }
})