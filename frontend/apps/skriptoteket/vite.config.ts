import { fileURLToPath } from "node:url";
import path from "node:path";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

const dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [vue()],
  base: "/static/spa/",
  build: {
    manifest: "manifest.json",
    outDir: path.resolve(dirname, "../../../src/skriptoteket/web/static/spa"),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      // Proxy non-SPA static assets to backend; SPA assets served by Vite
      "^/static/(?!spa)": "http://127.0.0.1:8000",
    },
  },
});
