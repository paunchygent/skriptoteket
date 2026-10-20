/**
 * Exam workspace document: an exam the app cannot read reports `unreadable`.
 *
 * Expected behavior (unit D15, U5):
 *   Opening a document whose stored schema is older than the current native
 *   exam document fails with `DOCUMENT_SCHEMA_OUTDATED`, and opening a
 *   current-version file the app cannot parse fails with
 *   `DOCUMENT_UNREADABLE`. Both outcomes report `unreadable` with no toast:
 *   the teacher sees the download-or-remove notice instead. Every other
 *   open failure keeps `Det gick inte att öppna provet. Försök igen.` and
 *   reports `failed`.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import { ApiError } from "../../../api/client";
import { useToastStore } from "../../../stores/toast";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { createSyncFence } from "./examWorkspaceSyncFence";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";

const OPEN_FAILURE_COPY = "Det gick inte att öppna provet. Försök igen.";

const api = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
}));
vi.mock("../../../api/examWorkspace", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
});

function toastMessages(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
}

describe("openDocument with a file the app cannot read", () => {
  it("an older saved format reports unreadable with no toast", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(
      new ApiError({
        code: "DOCUMENT_SCHEMA_OUTDATED",
        message: "Native exam document uses an outdated schema version.",
        status: 422,
      }),
    );
    const scope = effectScope();
    const fence = createSyncFence();
    const state = scope.run(() => useExamWorkspaceDocument({ getFence: () => fence, store: serverExamWorkspaceStore, submitRoute: () => Promise.resolve("failed"), noteInstallingCursor: () => undefined }))!;
    try {
      const opened = await state.openDocument("lineage-1", fence.begin());

      expect(opened).toBe("unreadable");
      expect(state.workspaceDocument.value).toBeNull();
      expect(toastMessages()).toEqual([]);
    } finally {
      scope.stop();
    }
  });

  it("a corrupt current-version file reports unreadable with no toast", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(
      new ApiError({
        code: "DOCUMENT_UNREADABLE",
        message: "Stored exam file cannot be read.",
        status: 422,
      }),
    );
    const scope = effectScope();
    const fence = createSyncFence();
    const state = scope.run(() => useExamWorkspaceDocument({ getFence: () => fence, store: serverExamWorkspaceStore, submitRoute: () => Promise.resolve("failed"), noteInstallingCursor: () => undefined }))!;
    try {
      const opened = await state.openDocument("lineage-1", fence.begin());

      expect(opened).toBe("unreadable");
      expect(state.workspaceDocument.value).toBeNull();
      expect(toastMessages()).toEqual([]);
    } finally {
      scope.stop();
    }
  });

  it("keeps the generic copy for a corrupt saved document", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(
      new ApiError({
        code: "VALIDATION_ERROR",
        message: "Native exam document payload failed validation.",
        status: 422,
      }),
    );
    const scope = effectScope();
    const fence = createSyncFence();
    const state = scope.run(() => useExamWorkspaceDocument({ getFence: () => fence, store: serverExamWorkspaceStore, submitRoute: () => Promise.resolve("failed"), noteInstallingCursor: () => undefined }))!;
    try {
      const opened = await state.openDocument("lineage-1", fence.begin());

      expect(opened).toBe("failed");
      expect(state.workspaceDocument.value).toBeNull();
      expect(toastMessages()).toEqual([OPEN_FAILURE_COPY]);
    } finally {
      scope.stop();
    }
  });

  it("keeps the generic copy when the open request never reaches the server", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(new Error("network down"));
    const scope = effectScope();
    const fence = createSyncFence();
    const state = scope.run(() => useExamWorkspaceDocument({ getFence: () => fence, store: serverExamWorkspaceStore, submitRoute: () => Promise.resolve("failed"), noteInstallingCursor: () => undefined }))!;
    try {
      const opened = await state.openDocument("lineage-1", fence.begin());

      expect(opened).toBe("failed");
      expect(state.workspaceDocument.value).toBeNull();
      expect(toastMessages()).toEqual([OPEN_FAILURE_COPY]);
    } finally {
      scope.stop();
    }
  });
});
