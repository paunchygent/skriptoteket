import { fileURLToPath } from "node:url";
import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

const dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  build: {
    manifest: "manifest.json",
    outDir: path.resolve(dirname, "../../src/skriptoteket/web/static/spa"),
    emptyOutDir: true,
    rollupOptions: {
      input: ["src/entrypoints/demo.ts"],
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
