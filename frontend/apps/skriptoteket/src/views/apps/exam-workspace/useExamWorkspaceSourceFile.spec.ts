/** Import intake preserves the teacher's course choice and rejects invalid input. */
import { ref } from "vue";
import { describe, expect, it, vi } from "vitest";

import { useExamWorkspaceSourceFile } from "./useExamWorkspaceSourceFile";

const COURSE = "SVESVE02";

function intake(blocked = false) {
  const importDocument = vi.fn().mockResolvedValue(undefined);
  const importBlocked = ref(blocked);
  return {
    ...useExamWorkspaceSourceFile(importDocument, importBlocked),
    importDocument,
    importBlocked,
  };
}

describe("exam workspace course-aware source intake", () => {
  it.each(["picker", "drop"] as const)("forwards the selected key through %s", (path) => {
    const state = intake();
    const file = new File(["exam"], "Svenska 2.DOCX");
    if (path === "picker") state.handleSelectedFile(file, COURSE);
    else state.handleDroppedFiles([file], COURSE);
    expect(state.importDocument).toHaveBeenCalledExactlyOnceWith(file, COURSE);
  });

  it("imports without a course when the optional picker is empty", () => {
    const state = intake();
    const file = new File(["exam"], "prov.docx");
    state.handleDroppedFiles([file], null);
    expect(state.importDocument).toHaveBeenCalledExactlyOnceWith(file, null);
  });

  it.each(["picker", "drop"] as const)("a course never makes non-DOCX input importable through %s", (path) => {
    const state = intake();
    const file = new File(["exam"], "prov.pdf");
    if (path === "picker") state.handleSelectedFile(file, COURSE);
    else state.handleDroppedFiles([file], COURSE);
    expect(state.importDocument).not.toHaveBeenCalled();
    expect(state.sourceFileError.value).toBeTruthy();
  });

  it("accepts a DigiExam export and counts a .docx and a .dxe in one drop as two exams", () => {
    const state = intake();
    const digiExam = new File(["dxe"], "Prov.DXE");
    state.handleDroppedFiles([digiExam, new File(["a"], "a.docx")], COURSE);
    expect(state.importDocument).not.toHaveBeenCalled();
    state.handleSelectedFile(digiExam, COURSE);
    expect(state.importDocument).toHaveBeenCalledExactlyOnceWith(digiExam, COURSE);
  });

  it("rejects two exams without discarding the key for the next single-file attempt", () => {
    const state = intake();
    const first = new File(["a"], "a.docx");
    state.handleDroppedFiles([first, new File(["b"], "b.docx")], COURSE);
    expect(state.importDocument).not.toHaveBeenCalled();
    state.handleDroppedFiles([first], COURSE);
    expect(state.importDocument).toHaveBeenCalledExactlyOnceWith(first, COURSE);
    expect(state.sourceFileError.value).toBeNull();
  });

  it("blocks picker and drop while unsaved changes or work prohibit import", () => {
    const state = intake(true);
    const file = new File(["exam"], "prov.docx");
    state.handleSelectedFile(file, COURSE);
    state.handleDroppedFiles([file], COURSE);
    expect(state.importDocument).not.toHaveBeenCalled();
    state.importBlocked.value = false;
    state.handleSelectedFile(file, COURSE);
    expect(state.importDocument).toHaveBeenCalledExactlyOnceWith(file, COURSE);
  });
});
