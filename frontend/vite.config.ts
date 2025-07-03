// frontend/vite.config.ts
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env     = loadEnv(mode, process.cwd(), '')
  const backend = env.VITE_BACKEND || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      ey: {
        '/soulseed': {
          target: backend,
          changeOrigin: true,
        },
        '/ritual': {
          target: backend,
          changeOrigin: true,
        },
        '/start': {
          target: backend,
          changeOrigin: true,
        },
        '/choose': {
          target: backend,
          changeOrigin: true,
        },
        '/choice': {
          target: backend,
          changeOrigin: true,
        },
        '/trust': {
          target: backend,
          changeOrigin: true,
        },
        '/reset': {
          target: backend,
          changeOrigin: true,
        },

        // Only upload needs to be proxied under /avatar:
        '/avatar/upload': {
          target: backend,
          changeOrigin: true,
        },

        '/soulmap': {
          target: backend,
          changeOrigin: true,
        },
      },
    },
  }
})
