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
      proxy: {
        // General API namespace
        '/api': {
          target: backend,
          changeOrigin: true,
        },
        // IMPORTANT: Do not proxy '/ritual' so the SPA route can render
        // Use '/api/ritual' for API calls instead
        '/soulseed': {
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
        // New free-text choices endpoint
        '/choices': {
          target: backend,
          changeOrigin: true,
        },
        '/trust': {
          target: backend,
          changeOrigin: true,
        },
        '/memory': {
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
        '/v1': {
          target: backend,
          changeOrigin: true,
        },
        '/npc': {
          target: backend,
          changeOrigin: true,
        },
        '/flow': {
          target: backend,
          changeOrigin: true,
        },
      },
    },
  }
})
