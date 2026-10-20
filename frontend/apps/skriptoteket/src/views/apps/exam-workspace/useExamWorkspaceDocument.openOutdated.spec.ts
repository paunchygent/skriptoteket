/**
 * Exam workspace document: an exam saved in an older format gets its own message.
 *
 * Expected behavior (unit D1o):
 *   Opening a document whose stored schema is older than the current native
 *   exam document fails with `DOCUMENT_SCHEMA_OUTDATED`, and the failure
 *   toast reads `Provet är sparat i ett äldre format och kan inte öppnas.
 *   Importera originalfilen på nytt.`
 *   Every other open failure keeps `Det gick inte att öppna provet. Försök
 *   igen.` Both outcomes report `failed`, so the deep link watcher restores the
 *   address exactly as it does for any other failed open.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import { ApiError } from "../../../api/client";
import { useToastStore } from "../../../stores/toast";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { createSyncFence } from "./examWorkspaceSyncFence";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";

const OUTDATED_COPY = "Provet är sparat i ett äldre format och kan inte öppnas. Importera originalfilen på nytt.";
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

describe("openDocument with an older saved format", () => {
  it("shows the older-format copy and opens nothing", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(
      new ApiError({
        code: "DOCUMENT_SCHEMA_OUTDATED",
        message: "Native exam document uses an outdated schema version.",
        status: 422,
      }),
    );
    const scope = effectScope();
    const fence = createSyncFence();
    const state = scope.run(() => useExamWorkspaceDocument({ getFence: () => fence, store: serverExamWorkspaceStore }))!;
    try {
      const opened = await state.openDocument("lineage-1", fence.begin());

      expect(opened).toBe("failed");
      expect(state.workspaceDocument.value).toBeNull();
      expect(toastMessages()).toContain(OUTDATED_COPY);
      expect(toastMessages()).not.toContain(OPEN_FAILURE_COPY);
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
    const state = scope.run(() => useExamWorkspaceDocument({ getFence: () => fence, store: serverExamWorkspaceStore }))!;
    try {
      const opened = await state.openDocument("lineage-1", fence.begin());

      expect(opened).toBe("failed");
      expect(state.workspaceDocument.value).toBeNull();
      expect(toastMessages()).toContain(OPEN_FAILURE_COPY);
      expect(toastMessages()).not.toContain(OUTDATED_COPY);
    } finally {
      scope.stop();
    }
  });

  it("keeps the generic copy when the open request never reaches the server", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(new Error("network down"));
    const scope = effectScope();
    const fence = createSyncFence();
    const state = scope.run(() => useExamWorkspaceDocument({ getFence: () => fence, store: serverExamWorkspaceStore }))!;
    try {
      const opened = await state.openDocument("lineage-1", fence.begin());

      expect(opened).toBe("failed");
      expect(state.workspaceDocument.value).toBeNull();
      expect(toastMessages()).toContain(OPEN_FAILURE_COPY);
      expect(toastMessages()).not.toContain(OUTDATED_COPY);
    } finally {
      scope.stop();
    }
  });
});
