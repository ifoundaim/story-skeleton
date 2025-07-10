// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react            from '@vitejs/plugin-react'

// shorthand for your backend target
const BACKEND = {
  target: 'http://localhost:8000',
  changeOrigin: true,
  secure: false,
}

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // proxy all of your FastAPI endpoints:
      // /soulseed, /avatar, /avatar/upload, /ritual,
      // /start, /choose, /trust
      '^/(?:soulseed|avatar(?:/upload)?|ritual|start|choose|trust)$': BACKEND,

      // proxy OpenAPI spec
      '/openapi.json': BACKEND,

      // proxy the entire docs/redoc tree (css, js, etc)
      '^/docs(?:/.*)?$':   BACKEND,
      '^/redoc(?:/.*)?$':  BACKEND,
    },
  },
})
