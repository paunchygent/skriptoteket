/** Adoption guards, not a second copy of the shared package's declarations. */
import { readFileSync, readdirSync } from "node:fs";
import { relative, resolve } from "node:path";

import { parse as parseCss } from "postcss";
import selectorParser from "postcss-selector-parser";
import { parse as parseSfc } from "vue/compiler-sfc";
import type { TemplateChildNode } from "vue/compiler-sfc";
import { describe, expect, it } from "vitest";

const buttonClasses = [
  "btn-cta", "btn-ghost", "btn-primary",
  "btn-inline-edit", "btn-inline-primary", "btn-inline-cancel",
] as const;
const src = resolve(process.cwd(), "src");
const sharedPath = resolve(src, "styles/action-buttons.css");
const actionImport = '"../styles/action-buttons.css"';
const prerequisiteImports = ['"../styles/tokens.css"', '"../styles/tailwind-theme.css"'];

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name);
    return entry.isDirectory() ? sourceFiles(path) : [path];
  });
}

function importsIn(css: string): string[] {
  const imports: string[] = [];
  parseCss(css).walkAtRules("import", (rule: { params: string }) => {
    // Both CSS string delimiters represent the same import.
    imports.push(rule.params.replaceAll("'", '"'));
  });
  return imports;
}

function importProblems(css: string): string[] {
  const imports = importsIn(css);
  const problems: string[] = [];
  if (imports.filter((value) => value === actionImport).length !== 1) {
    problems.push("action-buttons must be imported exactly once");
  }
  for (const prerequisite of prerequisiteImports) {
    if (!imports.includes(prerequisite) || imports.indexOf(prerequisite) >= imports.indexOf(actionImport)) {
      problems.push(`action-buttons must follow ${prerequisite}`);
    }
  }
  return problems;
}

function buttonRules(css: string): Set<string> {
  const classes = new Set<string>();
  parseCss(css).walkRules((rule: { selector: string }) => {
    selectorParser().astSync(rule.selector).walkClasses((node: { value: string }) => {
      if (buttonClasses.some((name) => name === node.value)) classes.add(node.value);
    });
  });
  return classes;
}

function markupButtons(source: string): Set<string> {
  const { descriptor, errors } = parseSfc(source);
  if (errors.length) throw errors[0];
  const classes = new Set<string>();
  function visit(node: TemplateChildNode) {
    if (node.type !== 1) return; // Vue element; comments/text cannot supply a class.
    for (const prop of node.props) {
      const value = prop.type === 6 && prop.name === "class"
        ? prop.value?.content
        : prop.type === 7 && prop.name === "bind" && prop.arg?.type === 4 && prop.arg.content === "class"
          ? prop.exp?.loc.source
          : undefined;
      if (!value) continue;
      // Class names are bounded lexical tokens inside a parsed class attribute
      // (including literal names in :class arrays/objects), not arbitrary prose.
      const tokens = value.match(/[\w-]+/g) ?? [];
      for (const name of buttonClasses) if (tokens.includes(name)) classes.add(name);
    }
    node.children.forEach(visit);
  }
  descriptor.template?.ast?.children.forEach(visit);
  return classes;
}

const files = sourceFiles(src);
const stylesheet = readFileSync(resolve(src, "assets/main.css"), "utf8");
const sharedRules = buttonRules(readFileSync(sharedPath, "utf8"));
const usedButtons = new Set(files.filter((file) => file.endsWith(".vue")).flatMap((file) =>
  [...markupButtons(readFileSync(file, "utf8"))],
));

describe("shared action-button adoption", () => {
  it("imports the shared stylesheet exactly once after tokens and theme", () => {
    expect(importProblems(stylesheet)).toEqual([]);
  });

  it("keeps global CSS rules for the six classes exclusively in the shared file", () => {
    // Scoped Vue layout rules are deliberately outside this global-CSS contract.
    const overrides = files.filter((file) => file.endsWith(".css") && file !== sharedPath)
      .flatMap((file) => [...buttonRules(readFileSync(file, "utf8"))]
        .map((name) => `${relative(src, file)}: .${name}`));
    expect(overrides).toEqual([]);
  });

  it("supplies a shared rule for every action-button class used in markup", () => {
    expect(usedButtons.size).toBeGreaterThan(0);
    expect([...usedButtons].filter((name) => !sharedRules.has(name))).toEqual([]);
  });
});

describe("adoption guard adversarial fixtures", () => {
  const imports = prerequisiteImports.map((path) => `@import ${path};`).join("\n");
  const adopted = `${imports}\n@import ${actionImport};`;

  it.each([
    ["missing", imports],
    ["commented out", `${imports}\n/* @import ${actionImport}; */`],
    ["duplicated", `${adopted}\n@import ${actionImport};`],
    ["before both prerequisites", `@import ${actionImport};\n${imports}`],
    ["before theme", `@import ${prerequisiteImports[0]};\n@import ${actionImport};\n@import ${prerequisiteImports[1]};`],
  ])("rejects a %s shared import", (_state, css) => {
    expect(importProblems(css).length).toBeGreaterThan(0);
  });

  it("accepts either CSS string delimiter and ignores commented imports", () => {
    expect(importProblems(`/* @import ${actionImport}; */\n${adopted.replaceAll('"', "'")}`)).toEqual([]);
  });

  it.each(buttonClasses)("detects a reintroduced .%s override, including nested/grouped/escaped selectors", (name) => {
    const escaped = name.replace("btn-", "btn\\-");
    expect([...buttonRules(`@media (hover: hover) { .unrelated, :is(.${escaped}):hover { color: red; } }`)])
      .toEqual([name]);
  });

  it("does not treat comments, declaration strings, or similarly named classes as overrides", () => {
    expect([...buttonRules(`/* .btn-cta { color: red } */
      .planner-btn-ghost, .btn-primary-extra { content: ".btn-inline-edit"; }
      [data-example=".btn-inline-cancel"] { color: red; }`)]).toEqual([]);
  });

  it.each(buttonClasses)("detects a missing shared rule for a used .%s class", (name) => {
    const used = markupButtons(`<template><button class="${name}">Action</button></template>`);
    const incomplete = buttonRules(buttonClasses.filter((other) => other !== name)
      .map((other) => `.${other} { color: red; }`).join("\n"));
    expect([...used].filter((item) => !incomplete.has(item))).toEqual([name]);
  });

  it("reads static and bound markup classes, not comments, text, scripts or scoped styles", () => {
    expect([...markupButtons(`<template>
      <!-- <button class="btn-cta" /> -->
      <p>btn-primary</p><button class="btn-ghost" :class="{ 'btn-inline-edit': editing }" />
      <button :class="['btn-inline-primary', extra]" />
    </template><script setup>const example = 'btn-inline-cancel';</script>
    <style scoped>.btn-cta { color: red; }</style>`)]).toEqual([
      "btn-ghost", "btn-inline-edit", "btn-inline-primary",
    ]);
  });
});
