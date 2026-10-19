#!/usr/bin/env node
/**
 * @fileoverview Turns every SPA Vitest path argument into an include target so
 * maintainers can pass repo-root or app-local spec files, folders and globs
 * through the canonical package scripts. A run never collects fewer spec files
 * than the caller named: a target that matches no spec file stops the run.
 * This keeps `package.json` test entrypoints aligned with `vitest.config.ts`.
 */

import { spawnSync } from "node:child_process";
import { existsSync, globSync, statSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
export const appRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(appRoot, "../../..");
const appWorkspacePrefix = toPosix(path.relative(repoRoot, appRoot));
const appRequire = createRequire(path.join(appRoot, "package.json"));
const explicitTestPattern = /(^|[/\\])[^/\\]+\.(spec|test)\.[cm]?[jt]sx?(?::\d+(?:,\d+)?)?$/;
const globPattern = /[*?[\]{}]/;
const folderSpecPattern = "**/*.spec.ts";
const globExclude = ["**/node_modules/**", "**/dist/**"];

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

/** Rewrites one path argument to app-local POSIX form, keeping a line selector. */
export function normalizeVitestPathArg(arg) {
  const [rawPath, lineSelector] = splitLineSelector(arg);
  let normalizedPath = rawPath;

  if (path.isAbsolute(rawPath)) {
    const relativeToApp = path.relative(appRoot, rawPath);
    if (!relativeToApp.startsWith("..") && !path.isAbsolute(relativeToApp)) {
      normalizedPath = relativeToApp || ".";
    } else {
      const relativeToRepo = path.relative(repoRoot, rawPath);
      if (!relativeToRepo.startsWith("..") && !path.isAbsolute(relativeToRepo)) {
        normalizedPath = relativeToRepo;
      }
    }
  }

  normalizedPath = stripLeadingCurrentDir(toPosix(normalizedPath));

  if (normalizedPath === appWorkspacePrefix || normalizedPath === `${appWorkspacePrefix}/`) {
    normalizedPath = ".";
  } else if (normalizedPath.startsWith(`${appWorkspacePrefix}/`)) {
    normalizedPath = normalizedPath.slice(appWorkspacePrefix.length + 1);
  }

  return `${normalizedPath}${lineSelector}`;
}

/** Lists the app-local files that include patterns collect, sorted. */
export function listSpecFiles(patterns) {
  return globSync(patterns, { cwd: appRoot, exclude: globExclude }).map(toPosix).sort();
}

/** Returns the include patterns for one app-local target without a line selector. */
export function expandVitestTarget(target) {
  if (isExplicitTest(target)) return [target];
  const folder = target.replace(/\/+$/, "");
  if (folder === "" || folder === ".") return [folderSpecPattern];
  if (folder.endsWith("**")) return [`${folder}/*.spec.ts`];
  return [`${folder}/${folderSpecPattern}`];
}

/** Separates the path targets Vitest would read as filters from flags and their values. */
export async function splitVitestArgs(rawArgs) {
  const separatorIndex = rawArgs.indexOf("--");
  const args =
    separatorIndex === -1
      ? rawArgs
      : [...rawArgs.slice(0, separatorIndex), ...rawArgs.slice(separatorIndex + 1)];
  const { parseCLI } = await import(pathToFileURL(appRequire.resolve("vitest/node")).href);
  const targets = [];
  const passthrough = [];
  let filterCount = 0;

  // Vitest's own parser decides which tokens are flag values; a token is a
  // target exactly when it grows the filter list of the parsed prefix.
  args.forEach((arg, index) => {
    const prefixFilterCount = parseCLI(["vitest", ...args.slice(0, index + 1)]).filter.length;
    if (prefixFilterCount > filterCount) {
      targets.push(arg);
    } else {
      passthrough.push(arg);
    }
    filterCount = prefixFilterCount;
  });

  return { targets, passthrough };
}

function describeTargetFailure(arg, target) {
  const absoluteTarget = path.join(appRoot, target);
  if (!isGlob(target) && !existsSync(absoluteTarget)) {
    return `${arg}: no such file or folder under ${appWorkspacePrefix}`;
  }
  if (!isGlob(target) && statSync(absoluteTarget).isFile()) {
    return `${arg}: not a spec file (expected *.spec.ts or *.test.ts)`;
  }
  return `${arg}: matches no spec file (tried ${expandVitestTarget(target).join(", ")})`;
}

/**
 * Plans one Vitest invocation: Vitest arguments without path targets, plus the
 * include list that collects every named target. Throws when a target matches
 * no spec file or a line selector would narrow other targets away.
 */
export async function planVitestRun(rawArgs) {
  const { targets, passthrough } = await splitVitestArgs(rawArgs);
  if (targets.length === 0) {
    return { args: passthrough, include: null };
  }

  const failures = [];
  const include = [];
  const lineFilters = [];

  for (const arg of targets) {
    const normalized = normalizeVitestPathArg(arg);
    const [target, lineSelector] = splitLineSelector(normalized);
    const patterns = expandVitestTarget(target);
    if (listSpecFiles(patterns).length === 0) {
      failures.push(describeTargetFailure(arg, target));
      continue;
    }
    include.push(...patterns);
    if (lineSelector) lineFilters.push(normalized);
  }

  if (lineFilters.length > 0 && lineFilters.length < targets.length) {
    failures.push(
      `a line selector (${lineFilters.join(", ")}) makes Vitest skip every other target; ` +
        "run line-selected specs on their own",
    );
  }
  if (failures.length > 0) {
    throw new Error(`vitest-run: ${failures.join("\n  ")}`);
  }

  return { args: [...passthrough, ...lineFilters], include };
}

/** Returns the Vitest CLI entry installed in this app's own dependencies. */
export function resolveVitestBin() {
  const packageJsonPath = appRequire.resolve("vitest/package.json");
  const { bin } = appRequire(packageJsonPath);
  const entry = typeof bin === "string" ? bin : bin.vitest;
  return path.join(path.dirname(packageJsonPath), entry);
}

export async function main(rawArgs = process.argv.slice(2)) {
  let plan;
  try {
    plan = await planVitestRun(rawArgs);
  } catch (error) {
    console.error(error instanceof Error ? error.message : error);
    return 1;
  }

  const env = { ...process.env };
  delete env.VITEST_INCLUDE;
  if (plan.include) {
    env.VITEST_INCLUDE = JSON.stringify(plan.include);
  }

  const result = spawnSync(process.execPath, [resolveVitestBin(), ...plan.args], {
    cwd: appRoot,
    stdio: "inherit",
    env,
  });

  return result.status ?? 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(await main());
}
