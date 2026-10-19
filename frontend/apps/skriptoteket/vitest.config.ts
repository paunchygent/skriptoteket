/**
 * Skriptoteket SPA unit-test build configuration.
 *
 * Purpose:
 *   Run jsdom-focused Vue and TypeScript tests without loading production CSS
 *   compilers that are only needed for browser dev/build assets.
 *
 * Relationships:
 *   - `vite.config.ts` owns Tailwind and production/development asset builds.
 *   - `scripts/vitest-run.mjs` turns every path argument into the include
 *     list before Vitest reads this config.
 */

import { fileURLToPath } from "node:url";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: "jsdom",
    // `scripts/vitest-run.mjs` passes named targets as a JSON array so glob
    // braces such as `{a,b}` survive intact.
    include: process.env.VITEST_INCLUDE
      ? (JSON.parse(process.env.VITEST_INCLUDE) as string[])
      : ["src/**/*.spec.ts"],
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
