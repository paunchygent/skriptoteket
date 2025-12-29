import { fileURLToPath } from "node:url";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  test: {
    globals: true,
    environment: "jsdom",
    include: ["src/**/*.spec.ts"],
    exclude: ["node_modules", "dist"],
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      include: ["src/**/*.ts", "src/**/*.vue"],
      exclude: [
        "src/**/*.spec.ts",
        "src/api/openapi.d.ts",
        "src/test/**",
        "src/main.ts",
        "src/env.d.ts",
      ],
    },
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
