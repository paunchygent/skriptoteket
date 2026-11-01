// @ts-check

import css from "@eslint/css";
import eslint from "@eslint/js";
import eslintPluginVue from "eslint-plugin-vue";
import globals from "globals";
import tseslint from "typescript-eslint";
import vueParser from "vue-eslint-parser";
import noHardcodedColour from "../../eslint-rules/no-hardcoded-colour.js";
import noTemplateRefValue from "../../eslint-rules/no-template-ref-value.js";

// The pinball game keeps its own palette (TASK-SKRIPT-42-01-01).
const COLOUR_EXCLUSIONS = [
  "src/views/apps/FlunkOutFrenzyView.vue",
  "src/views/apps/styles/fof-shell-layout.css",
  "src/views/apps/styles/fof-shell-panels.css",
  "src/components/apps/flunk-out-frenzy/**",
];

const skriptoteketPlugin = {
  rules: {
    "no-template-ref-value": noTemplateRefValue,
    "no-hardcoded-colour": noHardcodedColour,
  },
};

export default tseslint.config(
  {
    // components/ui/shared holds synced huleedu-integrated bytes; design-system-validate owns them.
    ignores: ["*.d.ts", "**/coverage/**", "**/dist/**", "src/components/ui/shared/**"],
  },
  {
    files: ["src/**/*.{ts,vue}"],
    extends: [
      eslint.configs.recommended,
      ...tseslint.configs.recommended,
      ...eslintPluginVue.configs["flat/recommended"],
    ],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: globals.browser,
      parserOptions: {
        parser: tseslint.parser,
        extraFileExtensions: [".vue"],
      },
    },
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "vue/multi-word-component-names": "off",
      "vue/singleline-html-element-content-newline": "off",
    },
  },
  {
    files: ["src/**/*.vue"],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        ecmaVersion: "latest",
        sourceType: "module",
        extraFileExtensions: [".vue"],
      },
    },
    plugins: {
      skriptoteket: skriptoteketPlugin,
    },
    rules: {
      "skriptoteket/no-template-ref-value": "error",
    },
  },
  {
    files: ["src/**/*.{ts,vue}"],
    ignores: COLOUR_EXCLUSIONS,
    plugins: {
      skriptoteket: skriptoteketPlugin,
    },
    rules: {
      "skriptoteket/no-hardcoded-colour": "error",
    },
  },
  {
    files: ["src/**/*.css"],
    ignores: COLOUR_EXCLUSIONS,
    plugins: { css, skriptoteket: skriptoteketPlugin },
    language: "css/css",
    languageOptions: { tolerant: true },
    rules: {
      "skriptoteket/no-hardcoded-colour": "error",
    },
  },
);
