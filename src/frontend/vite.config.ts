/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { copyPublicAssets } from './tools/optional-public.mjs';

const root = fileURLToPath(new URL('.', import.meta.url));

// Files on a WSL-mounted Windows drive (/mnt/<letter>/...) do not raise inotify
// events when edited from Windows, so the dev server polls there. Override with
// BPP_WATCH_POLL=0 or BPP_WATCH_POLL=1.
const pollEnv = process.env.BPP_WATCH_POLL;
const usePolling = pollEnv === '1' || (pollEnv !== '0' && root.startsWith('/mnt/'));

// Large generated or research folders never need watching (public/data alone is
// ~2000 files); polling them would waste CPU.
const ignored = [
  '**/public/data/**',
  '**/research/**',
  '**/inputs/**',
  '**/.venv/**',
  '**/artifacts/**',
  '**/delivery/**',
  '**/tools/**',
  '**/backups/**',
  '**/dist/**',
];

export default defineConfig({
  plugins: [react(), {
    name: 'optional-historical-exports',
    apply: 'build',
    writeBundle(options) {
      copyPublicAssets(resolve(root, 'public'), resolve(root, options.dir ?? 'dist'));
    },
  }],
  resolve: {
    alias: {
      '@core': `${root}core`,
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    watch: { usePolling, interval: 400, ignored },
  },
  preview: {
    host: '127.0.0.1',
    port: 4173,
  },
  build: {
    copyPublicDir: false,
    outDir: 'dist',
    target: 'es2022',
    chunkSizeWarningLimit: 900,
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
