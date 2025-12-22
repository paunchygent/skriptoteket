import { fileURLToPath } from "node:url";
import path from "node:path";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

const dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ command }) => ({
  plugins: [vue(), tailwindcss()],
  // The SPA is mounted at "/" in production, but its built assets live under "/static/spa/".
  // For Vite dev server we want routes like "/browse" to work directly.
  base: command === "serve" ? "/" : "/static/spa/",
  build: {
    manifest: "manifest.json",
    outDir: path.resolve(dirname, "../../../src/skriptoteket/web/static/spa"),
    emptyOutDir: true,
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    fs: {
      allow: [path.resolve(dirname, "../../..")],
    },
    proxy: {
      "/api": "http://127.0.0.1:8000",
      // Proxy non-SPA static assets to backend; SPA assets served by Vite
      "^/static/(?!spa)": "http://127.0.0.1:8000",
    },
  },
}));
