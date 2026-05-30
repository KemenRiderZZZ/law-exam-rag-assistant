import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    build: {
      // Lower the transpile target so more mobile browsers/WebViews can run the app.
      target: 'es2019',
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // Allow disabling HMR during automation or low-noise local debugging.
      hmr: process.env.DISABLE_HMR !== 'true',
      proxy: {
        '/api': 'http://127.0.0.1:8765',
      },
      // Disable file watching when DISABLE_HMR is true to reduce local CPU usage.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
  };
});
