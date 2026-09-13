import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Proxy en desarrollo: el frontend habla con /api sin preocuparse de CORS.
// En producción, nginx hace el mismo papel (ver nginx.conf).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:4000', changeOrigin: true },
    },
  },
  build: {
    target: 'es2022',
    sourcemap: false,
  },
});
