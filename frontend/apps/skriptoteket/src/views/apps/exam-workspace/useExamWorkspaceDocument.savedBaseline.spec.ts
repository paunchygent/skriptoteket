/** The saved baseline follows the exam file: every confirmed autosave step updates it. */
import { createPinia, setActivePinia } from "pinia";
import { effectScope } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceDocumentResponse } from "../../../api/examWorkspace";
import { buildResponse } from "./useExamWorkspaceDocument.specSupport";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { createSyncFence } from "./examWorkspaceSyncFence";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";

const api = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
  copyExamWorkspaceDocument: vi.fn(),
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
  it.each(["open", "reload", "reopen"])("keeps command results dirty on %s and opens the copied exam clean", async (path) => {
    const response = commandResponse();
    api.getExamWorkspaceDocument.mockResolvedValue(response);
    const scope = effectScope();
    const state = scope.run(() => useExamWorkspaceDocument({ store: serverExamWorkspaceStore }))!;
    try {
      await state.openDocument("lineage-1");
      if (path === "reload") await state.reloadDocument();
      if (path === "reopen") await state.openDocument("lineage-1");
      expect(state.workspaceDocument.value).toEqual(response.document);
      expect(state.isDirty.value).toBe(true);
      expect(state.isBusy.value).toBe(false);
      expect(state.savedRevision.value).toBe(1);
      const copied = { ...response.document };
      api.copyExamWorkspaceDocument.mockResolvedValue({
        ...response, document: copied, saved_document: copied,
        summary: { ...response.summary, lineage_id: "lineage-2", version: 1 },
      });
      expect(await state.saveDocumentAs("Kopia", createSyncFence().begin())).toBe("saved");
      expect(api.copyExamWorkspaceDocument).toHaveBeenCalledWith(
        "lineage-1",
        "Kopia",
        response.document,
      );
      expect(state.isDirty.value).toBe(false);
      expect(state.savedRevision.value).toBe(1);
    } finally {
      scope.stop();
    }
  });

  it("marks the copy clean once its pending edit is confirmed stored", async () => {
    const base = buildResponse();
    const response = { ...base, document: { ...base.document, title: "Arbetskopia" } };
    api.getExamWorkspaceDocument.mockResolvedValue(response);
    const scope = effectScope();
    const state = scope.run(() => useExamWorkspaceDocument({ store: serverExamWorkspaceStore }))!;
    try {
      await state.openDocument("lineage-1");
      expect(state.isDirty.value).toBe(true);
      state.noteStored(createSyncFence().begin(), { ...response.document });
      expect(state.isDirty.value).toBe(false);
      expect(state.savedRevision.value).toBe(1);
    } finally {
      scope.stop();
    }
  });

  it("opens an unchanged saved exam clean", async () => {
    const response = buildResponse();
    api.getExamWorkspaceDocument.mockResolvedValue({ ...response, saved_document: response.document });
    const scope = effectScope();
    const state = scope.run(() => useExamWorkspaceDocument({ store: serverExamWorkspaceStore }))!;
    try {
      await state.openDocument("lineage-1");
      expect(state.isDirty.value).toBe(false);
    } finally {
      scope.stop();
    }
  });
});
