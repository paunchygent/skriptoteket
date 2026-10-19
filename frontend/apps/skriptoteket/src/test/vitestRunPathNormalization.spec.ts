// @vitest-environment node
/**
 * @fileoverview Locks down the SPA Vitest wrapper: every path argument becomes
 * an include target, so a run never silently collects fewer spec files than
 * the caller named, and a target without spec files fails before Vitest starts.
 */

import { describe, expect, it } from "vitest";

import {
  appRoot,
  expandVitestTarget,
  listSpecFiles,
  normalizeVitestPathArg,
  planVitestRun,
  resolveVitestBin,
  splitVitestArgs,
} from "../../scripts/vitest-run.mjs";

const examFolder = "src/views/apps/exam-workspace";
const examSpec = `${examFolder}/ExamCourseCombobox.spec.ts`;

// Vite's own glob is the independent oracle for the folder's spec files.
const examFolderSpecs = Object.keys(import.meta.glob("/src/views/apps/exam-workspace/**/*.spec.ts"))
  .map((key) => key.slice(1))
  .sort();

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

describe("expandVitestTarget", () => {
  it("keeps an explicit spec file as its own include pattern", () => {
    expect(expandVitestTarget(examSpec)).toEqual([examSpec]);
  });

  it("expands a folder with or without a trailing slash to its spec files", () => {
    expect(expandVitestTarget(examFolder)).toEqual([`${examFolder}/**/*.spec.ts`]);
    expect(expandVitestTarget(`${examFolder}/`)).toEqual([`${examFolder}/**/*.spec.ts`]);
  });

  it("expands a folder glob to the spec files beneath it", () => {
    expect(expandVitestTarget("src/views/apps/**")).toEqual(["src/views/apps/**/*.spec.ts"]);
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

  it("collects a glob target", async () => {
    const plan = await planVitestRun(["run", `${examFolder}/ExamCourse*.spec.ts`]);
    expect(collectedFiles(plan.include ?? [])).toEqual([examSpec]);
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
});

describe("resolveVitestBin", () => {
  it("resolves the Vitest entry from the app's own dependencies", () => {
    const bin = resolveVitestBin();
    expect(bin).toMatch(/\/node_modules\/(\.pnpm\/vitest@[^/]+\/node_modules\/)?vitest\/vitest\.mjs$/);
  });
});
