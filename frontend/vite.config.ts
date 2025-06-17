// frontend/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // API endpoints
      '/avatar': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/soulseed': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/start': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/choose': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/trust': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // serve uploaded files
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
