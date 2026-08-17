import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (/lightweight-charts|recharts/.test(id)) return 'charts'
          if (/framer-motion/.test(id)) return 'motion'
          if (/react|scheduler|react-router|sonner|@tanstack/.test(id)) return 'react-vendor'
          return 'vendor'
        },
      },
    },
  },
  server: {
    port: parseInt(process.env.VITE_PORT || '5173', 10),
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://127.0.0.1:8001',
      },
    },
    headers: {
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
    },
  },
  preview: {
    port: parseInt(process.env.VITE_PREVIEW_PORT || '4173', 10),
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://127.0.0.1:8001',
      },
    },
  },
})
