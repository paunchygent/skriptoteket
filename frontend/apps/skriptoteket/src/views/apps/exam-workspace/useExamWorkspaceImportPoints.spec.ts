/**
 * The open-workspace state of the import-time points check
 * (TASK-SKRIPT-40-04-23, P1, P3, P4).
 *
 * Expected behavior:
 *   The check shows only for an import started in this workspace, once its
 *   exam is open and no import or conversion runs any more. It never shows
 *   for an exam opened any other way, after the teacher opens another exam
 *   or opens the imported exam again, or after Avfärda. Nothing is stored,
 *   so a reload starts with no check.
 */

import { describe, expect, it } from "vitest";
import { effectScope, nextTick, ref } from "vue";

import { useExamWorkspaceImportPoints } from "./useExamWorkspaceImportPoints";

function setup() {
  const lineageId = ref<string | null>("old-exam");
  const settled = ref(false);
  const scope = effectScope();
  const check = scope.run(() =>
    useExamWorkspaceImportPoints({ lineageId: () => lineageId.value, settled: () => settled.value }),
  )!;
  return { check, lineageId, settled, scope };
}

describe("useExamWorkspaceImportPoints", () => {
  it("shows once the imported exam is open and its conversion has finished", async () => {
    const { check, lineageId, settled } = setup();
    check.noteImportStarted("imported");
    await nextTick();
    expect(check.shown.value).toBe(false);

    check.noteOpening("imported");
    lineageId.value = "imported";
    await nextTick();
    // The first batch is open but the conversion still runs.
    expect(check.shown.value).toBe(false);

    settled.value = true;
    await nextTick();
    expect(check.shown.value).toBe(true);
  });

  it("shows for an import that opens already settled, as a QTI package does", async () => {
    const { check, lineageId, settled } = setup();
    settled.value = true;
    check.noteImportStarted("imported");
    check.noteOpening("imported");
    lineageId.value = "imported";
    await nextTick();
    expect(check.shown.value).toBe(true);
  });

  it("never shows for an exam that was only opened", async () => {
    const { check, lineageId, settled } = setup();
    settled.value = true;
    check.noteOpening("other");
    lineageId.value = "other";
    await nextTick();
    expect(check.shown.value).toBe(false);
  });

  it("goes for good when the teacher opens another exam, also when they come back", async () => {
    const { check, lineageId, settled } = setup();
    settled.value = true;
    check.noteImportStarted("imported");
    check.noteOpening("imported");
    lineageId.value = "imported";
    await nextTick();
    expect(check.shown.value).toBe(true);

    check.noteOpening("other");
    lineageId.value = "other";
    await nextTick();
    expect(check.shown.value).toBe(false);

    check.noteOpening("imported");
    lineageId.value = "imported";
    await nextTick();
    expect(check.shown.value).toBe(false);
  });

  it("goes when the imported exam is opened again", async () => {
    const { check, lineageId, settled } = setup();
    settled.value = true;
    check.noteImportStarted("imported");
    check.noteOpening("imported");
    lineageId.value = "imported";
    await nextTick();
    expect(check.shown.value).toBe(true);

    check.noteOpening("imported");
    await nextTick();
    expect(check.shown.value).toBe(false);
  });

  it("does not show when the teacher leaves for another exam before the conversion finishes", async () => {
    const { check, lineageId, settled } = setup();
    check.noteImportStarted("imported");
    check.noteOpening("imported");
    lineageId.value = "imported";
    await nextTick();
    check.noteOpening("other");
    lineageId.value = "other";
    settled.value = true;
    await nextTick();
    check.noteOpening("imported");
    lineageId.value = "imported";
    await nextTick();
    expect(check.shown.value).toBe(false);
  });

  it("Avfärda hides it and it never returns for that import", async () => {
    const { check, lineageId, settled } = setup();
    settled.value = true;
    check.noteImportStarted("imported");
    check.noteOpening("imported");
    lineageId.value = "imported";
    await nextTick();
    check.dismiss();
    await nextTick();
    expect(check.shown.value).toBe(false);
    settled.value = false;
    await nextTick();
    settled.value = true;
    await nextTick();
    expect(check.shown.value).toBe(false);
  });

  it("starts with nothing shown in a fresh workspace, as after a reload", async () => {
    const { check, lineageId, settled } = setup();
    settled.value = true;
    lineageId.value = "imported";
    await nextTick();
    expect(check.shown.value).toBe(false);
  });
});
