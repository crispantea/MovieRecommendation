import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],

    server: {
      proxy: {
        '/api/inference': {
          target: env.VITE_INFERENCE_SERVICE_URL,
          changeOrigin: true,
          rewrite: (path) =>
            path.replace(/^\/api\/inference/, ''),
        },
        '/api/profiles': {
          target: env.VITE_PROFILES_SERVICE_URL,
          changeOrigin: true,
          rewrite: (path) =>
            path.replace(/^\/api\/profiles/, ''),
        },
      },
    },
  }
})