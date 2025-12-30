#!/usr/bin/env node
import { spawnSync } from "node:child_process";

const args = process.argv.slice(2);
const targetPattern = /\.(spec|test)\.[jt]sx?$/;
const globPattern = /[*?[\]{}]/;
const testSuffixes = [".spec.*", ".test.*"];
const appendTestSuffixes = (patternBase) =>
  testSuffixes.map((suffix) => `${patternBase}${suffix}`);

const isExplicitTest = (arg) => targetPattern.test(arg) || arg.includes(".spec") || arg.includes(".test");
const isGlob = (arg) => globPattern.test(arg);

const normalizeGlob = (arg) => {
  if (isExplicitTest(arg)) return [arg];
  if (arg.endsWith("**/")) return appendTestSuffixes(`${arg}*`);
  if (arg.endsWith("**")) return appendTestSuffixes(`${arg}/*`);
  if (arg.endsWith("*")) return appendTestSuffixes(arg);
  if (arg.endsWith("/")) return appendTestSuffixes(`${arg}**/*`);
  return appendTestSuffixes(`${arg}/**/*`);
};

const targets = args
  .filter((arg) => !arg.startsWith("-") && (isExplicitTest(arg) || isGlob(arg)))
  .flatMap((arg) => (isGlob(arg) ? normalizeGlob(arg) : [arg]));

const env = { ...process.env };
if (targets.length > 0) {
  env.VITEST_INCLUDE = targets.join(",");
}

const result = spawnSync("vitest", ["run", ...args], {
  stdio: "inherit",
  env,
  shell: process.platform === "win32",
});

process.exit(result.status ?? 1);
