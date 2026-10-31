import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// A porta 3000 é a FRONTEND_URL padrão do backend (links de e-mail e CORS)
export default defineConfig({
  plugins: [react()],
  server: { port: 3000, strictPort: true },
})
