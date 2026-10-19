#!/usr/bin/env node
/**
 * @fileoverview Turns every SPA Vitest path argument into an include target by
 * resolving it against the real files and directories on disk, so a run never
 * collects fewer spec files than the caller named: a target that matches no
 * spec file stops the run. File and folder matches keep their own include
 * patterns, including when one glob matches both. This keeps `package.json`
 * test entrypoints aligned with `vitest.config.ts`.
 */

import { spawnSync } from "node:child_process";
import { existsSync, globSync, statSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { encodeVitestInclude, VITEST_INCLUDE_ENV } from "./vitest-include.mjs";

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

/**
 * Resolves one app-local or absolute target without a line selector against
 * the files and directories that actually exist. A directory contributes the
 * spec files beneath it; an explicit spec file contributes itself; any other
 * file is ignored. A match whose own path still contains a glob character
 * cannot be named exactly by Vitest's include list, so it is reported as
 * unnameable instead of being silently dropped.
 */
export function resolveVitestTarget(target) {
  const stripped = target.replace(/\/+$/, "");
  const normalized = stripped === "" ? "." : stripped;

  let matches;
  if (isGlob(normalized)) {
    matches = globSync(normalized, { cwd: appRoot, exclude: globExclude, withFileTypes: true }).map(
      (entry) => {
        const absolute = path.join(entry.parentPath, entry.name);
        const relative = path.relative(appRoot, absolute);
        if (relative === "") return ".";
        if (!relative.startsWith("..") && !path.isAbsolute(relative)) {
          return toPosix(relative);
        }
        return toPosix(absolute);
      },
    );
  } else if (normalized === ".") {
    matches = ["."];
  } else if (path.isAbsolute(normalized)) {
    matches = existsSync(normalized) ? [toPosix(normalized)] : [];
  } else {
    matches = existsSync(path.join(appRoot, normalized)) ? [normalized] : [];
  }

  const patterns = [];
  const seenPatterns = new Set();
  const specFiles = new Set();
  const unnameable = [];
  const pushPattern = (pattern) => {
    if (!seenPatterns.has(pattern)) {
      seenPatterns.add(pattern);
      patterns.push(pattern);
    }
  };

  for (const match of [...new Set(matches)].sort()) {
    if (isGlob(match)) {
      unnameable.push(match);
      continue;
    }
    const absoluteMatch = path.isAbsolute(match) ? match : path.join(appRoot, match);
    const entry = statSync(absoluteMatch);
    if (entry.isDirectory()) {
      const pattern = match === "." ? folderSpecPattern : `${match}/${folderSpecPattern}`;
      pushPattern(pattern);
      for (const file of listSpecFiles([pattern])) specFiles.add(file);
    } else if (entry.isFile() && isExplicitTest(match)) {
      pushPattern(match);
      specFiles.add(match);
    }
  }

  return { patterns, specFiles: [...specFiles].sort(), unnameable };
}

/** Separates the path targets Vitest would read as filters from flags and their values. */
export async function splitVitestArgs(rawArgs) {
  const separatorIndex = rawArgs.indexOf("--");
  const args =
    separatorIndex === -1
      ? rawArgs
      : [...rawArgs.slice(0, separatorIndex), ...rawArgs.slice(separatorIndex + 1)];
  // A remaining separator means the caller forwarded one separator and Vitest
  // arguments supply another. Vitest's parser stores everything after it in
  // `options["--"]` instead of its filter list, so every token past it is a
  // target the wrapper must validate; nothing there is forwarded to Vitest.
  const secondSeparatorIndex = args.indexOf("--");
  const head = secondSeparatorIndex === -1 ? args : args.slice(0, secondSeparatorIndex);
  const remainder =
    secondSeparatorIndex === -1 ? [] : args.slice(secondSeparatorIndex + 1).filter((arg) => arg !== "--");
  const { parseCLI } = await import(pathToFileURL(appRequire.resolve("vitest/node")).href);
  const headTargets = [];
  const headPassthrough = [];
  let filterCount = 0;

  // Vitest's own parser decides which tokens are flag values; a token is a
  // target exactly when it grows the filter list of the parsed prefix.
  head.forEach((arg, index) => {
    const prefixFilterCount = parseCLI(["vitest", ...head.slice(0, index + 1)]).filter.length;
    if (prefixFilterCount > filterCount) {
      headTargets.push(arg);
    } else {
      headPassthrough.push(arg);
    }
    filterCount = prefixFilterCount;
  });

  return { targets: [...headTargets, ...remainder], passthrough: headPassthrough };
}

function describeTargetFailure(arg, target) {
  const absoluteTarget = path.isAbsolute(target) ? target : path.join(appRoot, target);
  if (!isGlob(target) && !existsSync(absoluteTarget)) {
    return `${arg}: no such file or folder under ${appWorkspacePrefix}`;
  }
  if (!isGlob(target) && statSync(absoluteTarget).isFile()) {
    return `${arg}: not a spec file (expected *.spec.ts or *.test.ts)`;
  }
  return `${arg}: matches no spec file (tried ${target})`;
}

/**
 * Plans one Vitest invocation: Vitest arguments without path targets, plus the
 * include list that collects every named target. Throws when a target matches
 * no spec file, matches a path Vitest cannot include exactly, or carries a
 * line selector that Vitest would apply by narrowing other targets away.
 */
export async function planVitestRun(rawArgs) {
  const { targets, passthrough } = await splitVitestArgs(rawArgs);
  if (targets.length === 0) {
    return { args: passthrough, include: null };
  }

  const failures = [];
  const include = [];
  const seenInclude = new Set();
  const lineFilters = [];

  for (const arg of targets) {
    const normalized = normalizeVitestPathArg(arg);
    const [target, lineSelector] = splitLineSelector(normalized);
    const resolution = resolveVitestTarget(target);
    if (resolution.unnameable.length > 0) {
      failures.push(
        `${arg}: matches paths with glob characters that Vitest cannot include exactly ` +
          `(${resolution.unnameable.join(", ")}); name a folder above them`,
      );
      continue;
    }
    if (resolution.specFiles.length === 0) {
      failures.push(describeTargetFailure(arg, target));
      continue;
    }
    for (const pattern of resolution.patterns) {
      if (!seenInclude.has(pattern)) {
        seenInclude.add(pattern);
        include.push(pattern);
      }
    }
    if (lineSelector) {
      // A line selector is only meaningful on one literally named spec file;
      // on a glob or a folder it would silently narrow every other target.
      if (!isGlob(target) && resolution.specFiles.length === 1 && resolution.specFiles[0] === target) {
        lineFilters.push(normalized);
      } else {
        failures.push(`${arg}: line selector needs one literally named spec file without a glob`);
      }
    }
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
  delete env[VITEST_INCLUDE_ENV];
  if (plan.include) {
    env[VITEST_INCLUDE_ENV] = encodeVitestInclude(plan.include);
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
