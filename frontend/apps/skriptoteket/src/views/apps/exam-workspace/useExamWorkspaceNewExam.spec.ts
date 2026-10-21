/**
 * Exam workspace new-exam flow (TASK-SKRIPT-40-04-21).
 *
 * Expected behavior:
 *   A teacher's click posts once to the blank route, reloads the saved list
 *   and opens the returned lineage, with no confirm dialog ever. While the
 *   open gate is blocked the click posts nothing, opens nothing and toasts
 *   the gate's reason. A failed create toasts the server's message, or the
 *   new-exam fallback copy when the failure carries none.
 */

import { computed, ref } from "vue";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { blankDocument } from "../ExamWorkspaceGuestMode.specSupport";
import { NEW_EXAM_FAILURE_COPY } from "./examWorkspaceNewExam";
import { OPEN_BUSY_COPY } from "./useExamWorkspaceOpenBlocking";
import { PENDING_SAVE_COPY } from "./useExamWorkspaceSaveStatus";
import { useExamWorkspaceNewExam } from "./useExamWorkspaceNewExam";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import type { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import type { ExamWorkspaceSaveStatus } from "./useExamWorkspaceSaveStatus";

type Editing = ReturnType<typeof useExamWorkspaceEditing>;

function arrange(options: {
  teacher?: boolean;
  saveStatus?: ExamWorkspaceSaveStatus;
  isBusy?: boolean;
  isDirty?: boolean;
  isOpenBlockedByOtherOperation?: boolean;
  document?: NativeExamDocument | null;
  create?: () => Promise<{ lineage_id: string }>;
  startBlank?: () => Promise<string>;
}) {
  const toast = { failure: vi.fn() };
  const openRoutedDocument = vi.fn();
  const createExamWorkspaceBlank = vi.fn(
    options.create ?? (async () => ({ lineage_id: "lineage-new" })),
  );
  const startBlank = vi.fn(options.startBlank ?? (async () => "guest-lineage-new"));
  const loadSavedDocuments = vi.fn(async () => undefined);
  const store: ExamWorkspaceStore = {
    shared: {} as ExamWorkspaceStore["shared"],
    teacher:
      options.teacher === false
        ? null
        : ({ createExamWorkspaceBlank } as unknown as NonNullable<ExamWorkspaceStore["teacher"]>),
    guest: options.teacher === false ? { startBlank, startFromQti: vi.fn() } : null,
  };
  const editing = {
    history: {
      saveStatus: computed(
        () =>
          options.saveStatus ?? {
            state: "saved",
            detail: null,
            savedAt: "2026-10-21T10:00:00Z",
          },
      ),
    },
    isBusy: computed(() => options.isBusy ?? false),
    isDirty: computed(() => options.isDirty ?? false),
    isOpenBlockedByOtherOperation: computed(() => options.isOpenBlockedByOtherOperation ?? false),
    loadSavedDocuments,
    workspaceDocument: ref(options.document ?? null),
  } as unknown as Editing;
  const flow = useExamWorkspaceNewExam({ editing, store, openRoutedDocument, toast });
  return { createExamWorkspaceBlank, flow, loadSavedDocuments, openRoutedDocument, startBlank, toast };
}

describe("useExamWorkspaceNewExam teacher", () => {
  it("posts once, reloads the saved list and opens the returned lineage with no confirm", async () => {
    const { createExamWorkspaceBlank, flow, loadSavedDocuments, openRoutedDocument, toast } =
      arrange({ document: blankDocument() });

    await flow.start();

    expect(createExamWorkspaceBlank).toHaveBeenCalledTimes(1);
    expect(loadSavedDocuments).toHaveBeenCalledTimes(1);
    expect(openRoutedDocument).toHaveBeenCalledTimes(1);
    expect(openRoutedDocument).toHaveBeenCalledWith("lineage-new");
    expect(flow.confirmOpen.value).toBe(false);
    expect(toast.failure).not.toHaveBeenCalled();
    expect(flow.busy.value).toBe(false);
  });

  const blockedCases: Array<{
    name: string;
    reason: string;
    saveStatus?: ExamWorkspaceSaveStatus;
    isBusy?: boolean;
    isDirty?: boolean;
    isOpenBlockedByOtherOperation?: boolean;
  }> = [
    { name: "dirty", reason: PENDING_SAVE_COPY, isDirty: true },
    { name: "saving", reason: PENDING_SAVE_COPY, saveStatus: { state: "saving", detail: null } },
    {
      name: "unsaved",
      reason: "Exporten saknar titel.",
      saveStatus: { state: "unsaved", detail: "Exporten saknar titel." },
    },
    {
      name: "other operation",
      reason: OPEN_BUSY_COPY,
      isBusy: true,
      isOpenBlockedByOtherOperation: true,
    },
  ];
  it.each(blockedCases)(
    "posts nothing, opens nothing and toasts the gate's reason while blocked ($name)",
    async ({ reason, saveStatus, isBusy, isDirty, isOpenBlockedByOtherOperation }) => {
      const { createExamWorkspaceBlank, flow, loadSavedDocuments, openRoutedDocument, toast } =
        arrange({
          document: blankDocument(),
          isBusy,
          isDirty,
          isOpenBlockedByOtherOperation,
          saveStatus,
        });

      await flow.start();

      expect(createExamWorkspaceBlank).not.toHaveBeenCalled();
      expect(loadSavedDocuments).not.toHaveBeenCalled();
      expect(openRoutedDocument).not.toHaveBeenCalled();
      expect(toast.failure).toHaveBeenCalledTimes(1);
      expect(toast.failure).toHaveBeenCalledWith(reason);
      expect(flow.confirmOpen.value).toBe(false);
      expect(flow.busy.value).toBe(false);
    },
  );

  it("toasts the server's refusal when the create fails", async () => {
    const { flow, openRoutedDocument, toast } = arrange({
      create: async () => {
        throw new ApiError({ code: "REFUSED", message: "Provet kunde inte skapas.", status: 409 });
      },
    });

    await flow.start();

    expect(openRoutedDocument).not.toHaveBeenCalled();
    expect(toast.failure).toHaveBeenCalledTimes(1);
    expect(toast.failure).toHaveBeenCalledWith("Provet kunde inte skapas.");
    expect(flow.busy.value).toBe(false);
  });

  it("toasts the fallback copy when the failure carries no server message", async () => {
    const { flow, toast } = arrange({
      create: async () => {
        throw new Error("network down");
      },
    });

    await flow.start();

    expect(toast.failure).toHaveBeenCalledWith(NEW_EXAM_FAILURE_COPY);
  });
});

describe("useExamWorkspaceNewExam guest", () => {
  it("starts the guest draft at once when no draft is open", async () => {
    const { flow, openRoutedDocument, startBlank, toast } = arrange({
      teacher: false,
      document: null,
    });

    await flow.start();

    expect(startBlank).toHaveBeenCalledTimes(1);
    expect(openRoutedDocument).toHaveBeenCalledWith("guest-lineage-new");
    expect(flow.confirmOpen.value).toBe(false);
    expect(toast.failure).not.toHaveBeenCalled();
  });
});
