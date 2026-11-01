// @ts-check

import { createRequire } from "node:module";
import { describe, it } from "node:test";

const appRequire = createRequire(
  new URL("../apps/skriptoteket/package.json", import.meta.url),
);
const { RuleTester } = appRequire("eslint");
const vueParser = appRequire("vue-eslint-parser");
const cssModule = await import(appRequire.resolve("@eslint/css"));
const css = cssModule.default.default ?? cssModule.default;
const { default: rule } = await import("./no-hardcoded-colour.js");

RuleTester.describe = describe;
RuleTester.it = it;

const tsTester = new RuleTester({
  languageOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
  },
});

const vueTester = new RuleTester({
  languageOptions: {
    parser: vueParser,
    parserOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
    },
  },
});

const cssTester = new RuleTester({
  plugins: { css },
  language: "css/css",
});

tsTester.run("no-hardcoded-colour", rule, {
  valid: [
    { code: `const id = "#main";`, filename: "sample.ts" },
    { code: `const html = "&#123;";`, filename: "sample.ts" },
    { code: `const name = "background";`, filename: "sample.ts" },
    {
      code: `const c = "var(--huleedu-text-primary)";`,
      filename: "sample.ts",
    },
    { code: `const w = "border-t-2";`, filename: "sample.ts" },
    { code: `const x = "border-x";`, filename: "sample.ts" },
    { code: `const y = "text-shadow-lg";`, filename: "sample.ts" },
    { code: `const z = "inset-shadow-sm";`, filename: "sample.ts" },
    { code: `const o = "ring-offset-2";`, filename: "sample.ts" },
  ],
  invalid: [
    {
      code: `const c = "#123456";`,
      filename: "sample.ts",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
    {
      code: `const s = "rgba(0,0,0,.1)";`,
      filename: "sample.ts",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
    {
      code: `const k = "hover:text-slate-500/50";`,
      filename: "sample.ts",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
    {
      code: `const a = "border-t-red-500";`,
      filename: "sample.ts",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
    {
      code: `const b = "border-x-blue-600";`,
      filename: "sample.ts",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
    {
      code: `const d = "border-s-slate-200";`,
      filename: "sample.ts",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
    {
      code: `const e = "inset-shadow-black/10";`,
      filename: "sample.ts",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
    {
      code: `const f = "inset-ring-gray-300";`,
      filename: "sample.ts",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
    {
      code: `const g = "text-shadow-white";`,
      filename: "sample.ts",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
    {
      code: `const h = "ring-offset-white";`,
      filename: "sample.ts",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
    {
      code: `const i = "drop-shadow-black/20";`,
      filename: "sample.ts",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
  ],
});

vueTester.run("no-hardcoded-colour", rule, {
  valid: [
    {
      code: `<template><div class="bg-canvas text-navy"></div></template>\n<style>\n.a { color: var(--huleedu-text-primary); }\n</style>`,
      filename: "sample.vue",
    },
  ],
  invalid: [
    {
      code: `<template><div class="bg-white p-2"></div></template>`,
      filename: "sample.vue",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
    {
      code: `<template><div></div></template>\n<style>\n.a { color: #fff; }\n</style>`,
      filename: "sample.vue",
      errors: [{ messageId: "noHardcodedColour", line: 3 }],
    },
  ],
});

cssTester.run("no-hardcoded-colour", rule, {
  valid: [
    {
      code: `a { color: var(--huleedu-text-primary); }`,
      filename: "sample.css",
    },
  ],
  invalid: [
    {
      code: `a { color: rgba(0,0,0,.1); }`,
      filename: "sample.css",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
    {
      code: `a { background: #123456; }`,
      filename: "sample.css",
      errors: [{ messageId: "noHardcodedColour", line: 1 }],
    },
  ],
});
