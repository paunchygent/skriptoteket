#!/usr/bin/env node
/**
 * @fileoverview Normalizes SPA Vitest path filters so maintainers can pass either
 * repo-root or app-local test targets through the canonical package scripts.
 * This keeps `package.json` test entrypoints aligned with `vitest.config.ts`.
 */

import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(appRoot, "../../..");
const appWorkspacePrefix = toPosix(path.relative(repoRoot, appRoot));
const explicitTestPattern = /(^|[/\\])[^/\\]+\.(spec|test)\.[cm]?[jt]sx?(?::\d+(?:,\d+)?)?$/;
const globPattern = /[*?[\]{}]/;
const testSuffixes = [".spec.*", ".test.*"];

function toPosix(value) {
  return value.replaceAll(path.sep, "/");
}

function stripLeadingCurrentDir(value) {
  return value.replace(/^\.\/+/, "");
}

function splitLineSelector(arg) {
  const match = /^(.*?)(:\d+(?:,\d+)?)$/.exec(arg);
  return match ? [match[1], match[2]] : [arg, ""];
}

export function isExplicitTest(arg) {
  return explicitTestPattern.test(arg);
}

export function isGlob(arg) {
  return globPattern.test(arg);
}

export function normalizeVitestPathArg(arg) {
  if (arg.startsWith("-")) {
    return arg;
  }

  const [rawPath, lineSelector] = splitLineSelector(arg);
  let normalizedPath = rawPath;

  if (path.isAbsolute(rawPath)) {
    const relativeToApp = path.relative(appRoot, rawPath);
    if (!relativeToApp.startsWith("..") && !path.isAbsolute(relativeToApp)) {
      normalizedPath = relativeToApp;
    } else {
      const relativeToRepo = path.relative(repoRoot, rawPath);
      if (!relativeToRepo.startsWith("..") && !path.isAbsolute(relativeToRepo)) {
        normalizedPath = relativeToRepo;
      }
    }
  }

  normalizedPath = stripLeadingCurrentDir(toPosix(normalizedPath));

  if (normalizedPath === appWorkspacePrefix) {
    normalizedPath = ".";
  } else if (normalizedPath.startsWith(`${appWorkspacePrefix}/`)) {
    normalizedPath = normalizedPath.slice(appWorkspacePrefix.length + 1);
  }

  return `${normalizedPath}${lineSelector}`;
}

function appendTestSuffixes(patternBase) {
  return testSuffixes.map((suffix) => `${patternBase}${suffix}`);
}

export function expandVitestTarget(arg) {
  if (isExplicitTest(arg)) return [arg];
  if (arg.endsWith("**/")) return appendTestSuffixes(`${arg}*`);
  if (arg.endsWith("**")) return appendTestSuffixes(`${arg}/*`);
  if (arg.endsWith("*")) return appendTestSuffixes(arg);
  if (arg.endsWith("/")) return appendTestSuffixes(`${arg}**/*`);
  return appendTestSuffixes(`${arg}/**/*`);
}

export function normalizeVitestArgs(args) {
  return args.map((arg) => {
    if (arg.startsWith("-")) {
      return arg;
    }

    if (isExplicitTest(arg) || isGlob(arg)) {
      return normalizeVitestPathArg(arg);
    }

    return arg;
  });
}

export function collectVitestTargets(args) {
  return args
    .filter((arg) => !arg.startsWith("-") && (isExplicitTest(arg) || isGlob(arg)))
    .flatMap((arg) => (isGlob(arg) ? expandVitestTarget(arg) : [arg]));
}

export function main(rawArgs = process.argv.slice(2)) {
  const args = normalizeVitestArgs(rawArgs);
  const targets = collectVitestTargets(args);
  const env = { ...process.env };

  if (targets.length > 0) {
    env.VITEST_INCLUDE = targets.join(",");
  }

  const result = spawnSync("vitest", args, {
    stdio: "inherit",
    env,
    shell: process.platform === "win32",
  });

  return result.status ?? 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(main());
}
