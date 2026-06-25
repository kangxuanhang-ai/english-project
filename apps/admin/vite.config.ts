import { fileURLToPath, URL } from 'node:url'
import { Config } from '@en/config'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    port: Config.ports.admin,
    proxy: {
      '/api': {
        target: `http://localhost:${Config.ports.server}`,
        changeOrigin: true,
      },
    },
  },
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
