// @vitest-environment node
/**
 * @fileoverview Locks down the SPA Vitest wrapper: every path argument becomes
 * an include target, so a run never silently collects fewer spec files than
 * the caller named, and a target without spec files fails before Vitest starts.
 */

import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { afterAll, describe, expect, it } from "vitest";

import {
  appRoot,
  listSpecFiles,
  normalizeVitestPathArg,
  planVitestRun,
  resolveVitestBin,
  resolveVitestTarget,
  splitVitestArgs,
} from "../../scripts/vitest-run.mjs";

const examFolder = "src/views/apps/exam-workspace";
const examSpec = `${examFolder}/ExamCourseCombobox.spec.ts`;
const wrapperSpec = "src/test/vitestRunPathNormalization.spec.ts";

// Vite's own glob is the independent oracle for the spec files each target must collect.
const examFolderSpecs = Object.keys(import.meta.glob("/src/views/apps/exam-workspace/**/*.spec.ts"))
  .map((key) => key.slice(1))
  .sort();
const homeFolderSpecs = Object.keys(import.meta.glob("/src/composables/home/**/*.spec.ts"))
  .map((key) => key.slice(1))
  .sort();
const testFolderSpecs = Object.keys(import.meta.glob("/src/test/*.spec.ts"))
  .map((key) => key.slice(1))
  .sort();
const appsFolderSpecs = Object.keys(import.meta.glob("/src/views/apps/**/*.spec.ts"))
  .map((key) => key.slice(1))
  .sort();

const scratchDirs: string[] = [];
afterAll(() => {
  for (const dir of scratchDirs) rmSync(dir, { recursive: true, force: true });
});

function collectedFiles(include: string[]): string[] {
  return [...new Set(listSpecFiles(include))].sort();
}

describe("normalizeVitestPathArg", () => {
  it("normalizes repo-root test paths to app-local paths", () => {
    expect(normalizeVitestPathArg(`frontend/apps/skriptoteket/${examSpec}`)).toBe(examSpec);
  });

  it("normalizes repo-root folder paths to app-local paths", () => {
    expect(normalizeVitestPathArg(`frontend/apps/skriptoteket/${examFolder}/`)).toBe(
      `${examFolder}/`,
    );
  });

  it("normalizes absolute paths to app-local paths", () => {
    expect(normalizeVitestPathArg(`${appRoot}/${examFolder}`)).toBe(examFolder);
  });

  it("strips a leading ./ and preserves Vitest line selectors", () => {
    expect(normalizeVitestPathArg(`./${examSpec}:42`)).toBe(`${examSpec}:42`);
  });
});

describe("resolveVitestTarget", () => {
  it("resolves a mixed file-and-folder brace glob to both branches", () => {
    const expected = [...homeFolderSpecs, wrapperSpec].sort();
    const resolution = resolveVitestTarget(
      "src/{test/vitestRunPathNormalization.spec.ts,composables/home}",
    );
    expect(resolution.unnameable).toEqual([]);
    expect(resolution.specFiles).toEqual(expected);
    expect(collectedFiles(resolution.patterns)).toEqual(expected);
  });

  it("resolves file-glob families to the spec files they match", () => {
    // import.meta.glob leaves the importing file itself out of its own
    // results (probed), so the oracle gains this file back explicitly.
    const expected = [...testFolderSpecs, wrapperSpec].sort();
    for (const target of ["src/test/*.{spec,test}.ts", "src/test/*.ts"]) {
      const resolution = resolveVitestTarget(target);
      expect(resolution.unnameable).toEqual([]);
      expect(resolution.specFiles).toEqual(expected);
      expect(collectedFiles(resolution.patterns)).toEqual(expected);
    }
  });

  it("resolves a folder glob to the spec files beneath it", () => {
    const resolution = resolveVitestTarget("src/views/apps/**");
    expect(resolution.unnameable).toEqual([]);
    expect(resolution.specFiles).toEqual(appsFolderSpecs);
    expect(collectedFiles(resolution.patterns)).toEqual(appsFolderSpecs);
  });

  it("resolves a literal folder and a trailing wildcard to the same specs", () => {
    expect(resolveVitestTarget(examFolder).specFiles).toEqual(examFolderSpecs);
    expect(resolveVitestTarget(`${examFolder}/*`).specFiles).toEqual(examFolderSpecs);
  });
});

describe("splitVitestArgs", () => {
  it("separates path targets from flags and flag values", async () => {
    await expect(
      splitVitestArgs(["run", "-t", "renders", "--reporter", "verbose", examFolder, "--coverage"]),
    ).resolves.toEqual({
      targets: [examFolder],
      passthrough: ["run", "-t", "renders", "--reporter", "verbose", "--coverage"],
    });
  });

  it("drops a leading package-manager -- separator instead of hiding targets behind it", async () => {
    await expect(splitVitestArgs(["run", "--", examFolder])).resolves.toEqual({
      targets: [examFolder],
      passthrough: ["run"],
    });
  });

  it("treats every token after a second -- as a target instead of forwarding it", async () => {
    await expect(splitVitestArgs(["run", "--", "--", "src/no-such-folder"])).resolves.toEqual({
      targets: ["src/no-such-folder"],
      passthrough: ["run"],
    });
  });

  it("keeps flag values in the head while targets after the second -- stay targets", async () => {
    await expect(
      splitVitestArgs(["list", "--filesOnly", "--", "--reporter", "dot", examFolder, "--", examSpec]),
    ).resolves.toEqual({
      targets: [examFolder, examSpec],
      passthrough: ["list", "--filesOnly", "--reporter", "dot"],
    });
  });

  it("treats a flag-looking token after the second -- as a target", async () => {
    await expect(
      splitVitestArgs(["run", "--", examFolder, "--", "--coverage"]),
    ).resolves.toEqual({
      targets: [examFolder, "--coverage"],
      passthrough: ["run"],
    });
  });
});

describe("planVitestRun", () => {
  it("leaves the config include list in charge when no target is named", async () => {
    await expect(planVitestRun(["run", "--coverage"])).resolves.toEqual({
      args: ["run", "--coverage"],
      include: null,
    });
  });

  it("lists more than one spec file in the oracle folder", () => {
    expect(examFolderSpecs.length).toBeGreaterThan(1);
  });

  it("collects every spec file of a folder named alone", async () => {
    const plan = await planVitestRun(["run", examFolder]);
    expect(plan.args).toEqual(["run"]);
    expect(collectedFiles(plan.include ?? [])).toEqual(examFolderSpecs);
  });

  it("collects the whole folder when a spec file and its folder are named together", async () => {
    const plan = await planVitestRun(["run", examSpec, examFolder]);
    const files = collectedFiles(plan.include ?? []);
    expect(files.length).toBeGreaterThan(1);
    expect(files).toEqual(examFolderSpecs);
  });

  it("collects a repo-root folder path", async () => {
    const plan = await planVitestRun(["run", `frontend/apps/skriptoteket/${examFolder}`]);
    expect(collectedFiles(plan.include ?? [])).toEqual(examFolderSpecs);
  });

  it("collects both branches of a mixed file-and-folder brace glob", async () => {
    const expected = [...homeFolderSpecs, wrapperSpec].sort();
    const plan = await planVitestRun([
      "run",
      "src/{test/vitestRunPathNormalization.spec.ts,composables/home}",
    ]);
    expect(collectedFiles(plan.include ?? [])).toEqual(expected);
  });

  it("collects a glob target", async () => {
    const plan = await planVitestRun(["run", `${examFolder}/ExamCourse*.spec.ts`]);
    expect(collectedFiles(plan.include ?? [])).toEqual([examSpec]);
  });

  it("collects the spec files directly inside a folder named by a trailing wildcard", async () => {
    const plan = await planVitestRun(["run", `${examFolder}/*`]);
    expect(collectedFiles(plan.include ?? [])).toEqual(examFolderSpecs);
  });

  it("passes flags and their values through without treating them as targets", async () => {
    const plan = await planVitestRun(["run", "-t", "renders", examFolder, "--reporter=dot"]);
    expect(plan.args).toEqual(["run", "-t", "renders", "--reporter=dot"]);
    expect(plan.include).toEqual([`${examFolder}/**/*.spec.ts`]);
  });

  it("keeps a line selector as a Vitest filter and includes only its file", async () => {
    await expect(planVitestRun(["run", `${examSpec}:12`])).resolves.toEqual({
      args: ["run", `${examSpec}:12`],
      include: [examSpec],
    });
  });

  it("rejects a line selector on a glob target", async () => {
    await expect(
      planVitestRun(["run", `${examFolder}/ExamCourse*.spec.ts:12`]),
    ).rejects.toThrow(/line selector/);
  });

  it("rejects a line selector on a folder that holds one spec file", async () => {
    expect(resolveVitestTarget("src/composables/home").specFiles).toHaveLength(1);
    await expect(planVitestRun(["run", "src/composables/home:12"])).rejects.toThrow(
      /line selector/,
    );
  });

  it("rejects a line selector mixed with other targets, which Vitest would narrow away", async () => {
    await expect(planVitestRun(["run", `${examSpec}:12`, examFolder])).rejects.toThrow(
      /line selector/,
    );
  });

  it("fails loudly on a nonexistent path even when another target matches", async () => {
    await expect(planVitestRun(["run", examFolder, "src/does-not-exist"])).rejects.toThrow(
      /src\/does-not-exist/,
    );
  });

  it("fails loudly on a glob that matches no spec file", async () => {
    await expect(planVitestRun(["run", "src/**/NoSuchThing*.spec.ts"])).rejects.toThrow(
      /NoSuchThing/,
    );
  });

  it("fails loudly on a file that is not a spec file", async () => {
    await expect(
      planVitestRun([
        "run",
        "src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec-support.ts",
      ]),
    ).rejects.toThrow(/compilePinballTable\.spec-support\.ts/);
  });

  it("rejects a target hidden behind a second -- instead of running the default suite", async () => {
    await expect(planVitestRun(["run", "--", "--", "src/no-such-folder"])).rejects.toThrow(
      /src\/no-such-folder/,
    );
  });

  it("rejects a glob matching a path Vitest cannot include exactly", async () => {
    const scratch = mkdtempSync(`${tmpdir()}/vitest-unnameable-`);
    scratchDirs.push(scratch);
    mkdirSync(`${scratch}/a[1]`, { recursive: true });
    writeFileSync(`${scratch}/a[1]/x.spec.ts`, "export const x = 1;\n");
    await expect(planVitestRun(["run", `${scratch}/*`])).rejects.toThrow(/a\[1\]/);
  });
});

describe("resolveVitestBin", () => {
  it("resolves the Vitest CLI entry from the app's own dependencies", () => {
    const bin = resolveVitestBin();
    expect(bin).toMatch(/\/node_modules\/(\.pnpm\/vitest@[^/]+\/node_modules\/)?vitest\/vitest\.mjs$/);
  });
});
