/** Spara compares the working copy with the exam file, not its latest undo step. */
import { createPinia, setActivePinia } from "pinia";
import { effectScope } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceDocumentResponse } from "../../../api/examWorkspace";
import { buildResponse } from "./useExamWorkspaceDocument.specSupport";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";

const api = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));
vi.mock("../../../api/examWorkspace", async (importOriginal) => ({
  ...await importOriginal<typeof import("../../../api/examWorkspace")>(),
  ...api,
}));

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
});

function commandResponse(): ExamWorkspaceDocumentResponse {
  const base = buildResponse();
  const document = buildParentDocument();
  return {
    ...base,
    saved_document: { ...document, parents: [] },
    document,
  };
}

describe("saved exam baseline", () => {
  it.each(["open", "reload", "reopen"])("keeps command results dirty on %s and saves the whole working copy", async (path) => {
    const response = commandResponse();
    api.getExamWorkspaceDocument.mockResolvedValue(response);
    const scope = effectScope();
    const state = scope.run(() => useExamWorkspaceDocument())!;
    try {
      await state.openDocument("lineage-1");
      if (path === "reload") await state.reloadDocument();
      if (path === "reopen") await state.openDocument("lineage-1");
      expect(state.workspaceDocument.value).toEqual(response.document);
      expect(state.isDirty.value).toBe(true);
      expect(state.isBusy.value).toBe(false);
      expect(state.savedRevision.value).toBe(1);
      const next = { ...response.document, revision: 2 };
      api.saveExamWorkspaceDocument.mockResolvedValue({
        ...response, document: next, saved_document: next,
        summary: { ...response.summary, version: 2 },
      });
      expect(await state.saveDocument("position-1")).toBe(true);
      expect(api.saveExamWorkspaceDocument).toHaveBeenCalledWith("lineage-1", {
        document: next, expectedRevision: 1, positionStepId: "position-1",
      });
      expect(state.isDirty.value).toBe(false);
      expect(state.savedRevision.value).toBe(2);
    } finally {
      scope.stop();
    }
  });

  it("keeps a reopened autosave dirty until Spara writes it", async () => {
    const base = buildResponse();
    const response = { ...base, document: { ...base.document, title: "Arbetskopia" } };
    api.getExamWorkspaceDocument.mockResolvedValue(response);
    const scope = effectScope();
    const state = scope.run(() => useExamWorkspaceDocument())!;
    try {
      await state.openDocument("lineage-1");
      expect(state.isDirty.value).toBe(true);
      const document = { ...response.document, revision: 2 };
      api.saveExamWorkspaceDocument.mockResolvedValue({
        ...response, document, saved_document: document,
        summary: { ...response.summary, version: 2 },
      });
      expect(await state.saveDocument("position-1")).toBe(true);
      expect(api.saveExamWorkspaceDocument).toHaveBeenCalledWith("lineage-1", {
        document, expectedRevision: 1, positionStepId: "position-1",
      });
      expect(state.isDirty.value).toBe(false);
    } finally {
      scope.stop();
    }
  });

  it("keeps unsaved commands dirty after a stale save reloads the working copy", async () => {
    api.getExamWorkspaceDocument.mockResolvedValue(buildResponse());
    const scope = effectScope();
    const state = scope.run(() => useExamWorkspaceDocument())!;
    try {
      await state.openDocument("lineage-1");
      state.setTitle("Lokal ändring");
      const response = commandResponse();
      api.getExamWorkspaceDocument.mockResolvedValue({
        ...response,
        document: { ...response.document, revision: 2 },
        saved_document: { ...response.saved_document, revision: 2 },
        summary: { ...response.summary, version: 2 },
      });
      api.saveExamWorkspaceDocument.mockRejectedValue(new ApiError({
        status: 409, code: "CONFLICT", message: "Provet har ändrats.",
      }));
      expect(await state.saveDocument("position-1")).toBe(false);
      expect(state.workspaceDocument.value?.parents).toEqual(response.document.parents);
      expect(state.savedRevision.value).toBe(2);
      expect(state.isDirty.value).toBe(true);
    } finally {
      scope.stop();
    }
  });

  it("opens an unchanged saved exam clean", async () => {
    const response = buildResponse();
    api.getExamWorkspaceDocument.mockResolvedValue({ ...response, saved_document: response.document });
    const scope = effectScope();
    const state = scope.run(() => useExamWorkspaceDocument())!;
    try {
      await state.openDocument("lineage-1");
      expect(state.isDirty.value).toBe(false);
    } finally {
      scope.stop();
    }
  });
});
