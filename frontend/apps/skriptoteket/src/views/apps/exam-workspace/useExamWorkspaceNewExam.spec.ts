/**
 * Exam workspace new-exam flow (TASK-SKRIPT-40-04-21, F1 repair).
 *
 * Expected behavior:
 *   Nytt prov submits one coordinator intent with the D9 check's cursor and
 *   never opens a routed document itself. A teacher's click submits at once
 *   and reloads the saved list when the coordinator reports "created"; a
 *   failed creation reloads nothing and toasts nothing (the coordinator owns
 *   the failure toast). While the open gate is blocked the click toasts the
 *   gate's reason and submits nothing. A guest with an empty draft submits
 *   at once with no confirm; with content it confirms first, and Ersätt
 *   re-checks the gate and the cursor before submitting.
 */

import { computed, ref } from "vue";
import { describe, expect, it, vi } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { blankDocument, keylessItem } from "../ExamWorkspaceGuestMode.specSupport";
import { OPEN_BUSY_COPY } from "./useExamWorkspaceOpenBlocking";
import { PENDING_SAVE_COPY } from "./useExamWorkspaceSaveStatus";
import type { ExamWorkspaceSaveStatus } from "./useExamWorkspaceSaveStatus";
import type { ExamWorkspaceNewExamOutcome } from "./examWorkspaceReplacementTypes";
import {
  useExamWorkspaceNewExam,
  type UseExamWorkspaceNewExamDeps,
} from "./useExamWorkspaceNewExam";
import { createGuestExamWorkspaceStore } from "./examWorkspaceGuestStore";
import { createGuestPublicApiMocks } from "./examWorkspaceGuestStore.specSupport";
import {
  createExamWorkspaceGuestDraftStorage,
  createInMemoryExamWorkspaceGuestDraftStorage,
} from "./examWorkspaceGuestDraftStorage";
import { createIds } from "./examWorkspaceGuestStore.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";

const CURSOR = "00000000-0000-4000-8000-000000000001";

/** The true blank shape: no title and one question with nothing in it. */
function emptyDraft(): NativeExamDocument {
  return {
    ...blankDocument(),
    header: { tags: [] },
    instructions: [],
    items: [
      {
        ...keylessItem(1, "single_choice"),
        answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
        body: [],
        choices: [],
      },
    ],
    title: "",
  };
}

/** A draft with content: the D9 check asks to confirm replacing it. */
function contentDraft(): NativeExamDocument {
  return blankDocument();
}

function guestStore(): UseExamWorkspaceNewExamDeps["store"] {
  const publicMocks = createGuestPublicApiMocks();
  const storage = createExamWorkspaceGuestDraftStorage({
    port: createInMemoryExamWorkspaceGuestDraftStorage(),
  });
  const guest = createGuestExamWorkspaceStore({
    api: publicMocks,
    ids: createIds(),
    onLimit: () => undefined,
    storage,
  });
  return guest.store;
}

function arrange(options: {
  teacher?: boolean;
  saveStatus?: ExamWorkspaceSaveStatus;
  isBusy?: boolean;
  isDirty?: boolean;
  isOpenBlockedByOtherOperation?: boolean;
  cursor?: string | null;
  document?: NativeExamDocument | null;
  outcome?: ExamWorkspaceNewExamOutcome;
}) {
  const status: ExamWorkspaceSaveStatus = options.saveStatus ?? {
    detail: null,
    savedAt: "2026-10-21T10:00:00Z",
    state: "saved",
  };
  const toast = { failure: vi.fn() };
  const newExam = vi.fn(async (): Promise<ExamWorkspaceNewExamOutcome> => options.outcome ?? "created");
  const loadSavedDocuments = vi.fn(async (): Promise<void> => undefined);
  const editing: UseExamWorkspaceNewExamDeps["editing"] = {
    history: { saveStatus: computed(() => status) },
    historyCursor: ref(options.cursor ?? null),
    isBusy: computed(() => options.isBusy ?? false),
    isDirty: computed(() => options.isDirty ?? false),
    isOpenBlockedByOtherOperation: computed(() => options.isOpenBlockedByOtherOperation ?? false),
    loadSavedDocuments,
    newExam,
    workspaceDocument: ref(options.document ?? null),
  };
  const store = options.teacher === false ? guestStore() : serverExamWorkspaceStore;
  const flow = useExamWorkspaceNewExam({ editing, store, toast });
  return { editing, flow, loadSavedDocuments, newExam, toast };
}

describe("useExamWorkspaceNewExam teacher", () => {
  it("submits the history cursor, reloads the saved list and opens nothing itself", async () => {
    const { flow, loadSavedDocuments, newExam, toast } = arrange({
      cursor: CURSOR,
      document: contentDraft(),
    });

    await flow.start();

    expect(newExam).toHaveBeenCalledTimes(1);
    expect(newExam).toHaveBeenCalledWith(CURSOR);
    expect(loadSavedDocuments).toHaveBeenCalledTimes(1);
    expect(flow.confirmOpen.value).toBe(false);
    expect(toast.failure).not.toHaveBeenCalled();
    expect(flow.busy.value).toBe(false);
  });

  it("submits a null cursor when no exam is open", async () => {
    const { flow, newExam } = arrange({ cursor: null, document: null });

    await flow.start();

    expect(newExam).toHaveBeenCalledTimes(1);
    expect(newExam).toHaveBeenCalledWith(null);
  });

  it("never confirms, even over a draft with content", async () => {
    const { flow, newExam } = arrange({ cursor: CURSOR, document: contentDraft() });

    await flow.start();

    expect(flow.confirmOpen.value).toBe(false);
    expect(newExam).toHaveBeenCalledTimes(1);
  });

  it("ignores a second click while the submit is in flight", async () => {
    const { flow, newExam } = arrange({ document: contentDraft() });
    let release!: () => void;
    const pending = new Promise<ExamWorkspaceNewExamOutcome>((run) => {
      release = () => run("created");
    });
    newExam.mockReturnValueOnce(pending);

    const first = flow.start();
    await flow.start();
    release();
    await first;

    expect(newExam).toHaveBeenCalledTimes(1);
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
    { name: "saving", reason: PENDING_SAVE_COPY, saveStatus: { detail: null, state: "saving" } },
    {
      name: "unsaved",
      reason: "Exporten saknar titel.",
      saveStatus: { detail: "Exporten saknar titel.", state: "unsaved" },
    },
    {
      name: "other operation",
      reason: OPEN_BUSY_COPY,
      isBusy: true,
      isOpenBlockedByOtherOperation: true,
    },
  ];
  it.each(blockedCases)(
    "toasts the gate's reason and submits nothing while blocked ($name)",
    async ({ reason, saveStatus, isBusy, isDirty, isOpenBlockedByOtherOperation }) => {
      const { flow, loadSavedDocuments, newExam, toast } = arrange({
        cursor: CURSOR,
        document: contentDraft(),
        isBusy,
        isDirty,
        isOpenBlockedByOtherOperation,
        saveStatus,
      });

      await flow.start();

      expect(newExam).not.toHaveBeenCalled();
      expect(loadSavedDocuments).not.toHaveBeenCalled();
      expect(toast.failure).toHaveBeenCalledTimes(1);
      expect(toast.failure).toHaveBeenCalledWith(reason);
      expect(flow.confirmOpen.value).toBe(false);
      expect(flow.busy.value).toBe(false);
    },
  );

  it("reloads nothing and toasts nothing when the coordinator reports a failure", async () => {
    const { flow, loadSavedDocuments, newExam, toast } = arrange({
      cursor: CURSOR,
      document: contentDraft(),
      outcome: "failed",
    });

    await flow.start();

    expect(newExam).toHaveBeenCalledTimes(1);
    expect(loadSavedDocuments).not.toHaveBeenCalled();
    expect(toast.failure).not.toHaveBeenCalled();
    expect(flow.busy.value).toBe(false);
  });
});

describe("useExamWorkspaceNewExam guest", () => {
  it("submits the empty draft at once with no confirm", async () => {
    const { flow, newExam, toast } = arrange({
      cursor: CURSOR,
      document: emptyDraft(),
      teacher: false,
    });

    await flow.start();

    expect(newExam).toHaveBeenCalledTimes(1);
    expect(newExam).toHaveBeenCalledWith(CURSOR);
    expect(flow.confirmOpen.value).toBe(false);
    expect(toast.failure).not.toHaveBeenCalled();
  });

  it("submits a null cursor when no draft is open", async () => {
    const { flow, newExam } = arrange({ cursor: null, document: null, teacher: false });

    await flow.start();

    expect(newExam).toHaveBeenCalledWith(null);
    expect(flow.confirmOpen.value).toBe(false);
  });

  it("confirms before replacing a draft that has content", async () => {
    const { flow, newExam } = arrange({
      cursor: CURSOR,
      document: contentDraft(),
      teacher: false,
    });

    await flow.start();

    expect(newExam).not.toHaveBeenCalled();
    expect(flow.confirmOpen.value).toBe(true);
  });

  it("Ersätt submits the checked cursor and closes the confirm", async () => {
    const { flow, newExam } = arrange({
      cursor: CURSOR,
      document: contentDraft(),
      teacher: false,
    });

    await flow.start();
    await flow.confirmReplace();

    expect(newExam).toHaveBeenCalledTimes(1);
    expect(newExam).toHaveBeenCalledWith(CURSOR);
    expect(flow.confirmOpen.value).toBe(false);
    expect(flow.busy.value).toBe(false);
  });

  it("Avbryt closes the confirm and submits nothing", async () => {
    const { flow, newExam } = arrange({
      cursor: CURSOR,
      document: contentDraft(),
      teacher: false,
    });

    await flow.start();
    flow.cancelReplace();

    expect(flow.confirmOpen.value).toBe(false);
    expect(newExam).not.toHaveBeenCalled();
  });

  it("Ersätt toasts the gate's reason and replaces nothing when the gate is now blocked", async () => {
    const status = ref<ExamWorkspaceSaveStatus>({
      detail: null,
      savedAt: "2026-10-21T10:00:00Z",
      state: "saved",
    });
    const toast = { failure: vi.fn() };
    const newExam = vi.fn(async (): Promise<ExamWorkspaceNewExamOutcome> => "created");
    const loadSavedDocuments = vi.fn(async (): Promise<void> => undefined);
    const editing: UseExamWorkspaceNewExamDeps["editing"] = {
      history: { saveStatus: computed(() => status.value) },
      historyCursor: ref(CURSOR),
      isBusy: computed(() => false),
      isDirty: computed(() => status.value.state !== "saved"),
      isOpenBlockedByOtherOperation: computed(() => false),
      loadSavedDocuments,
      newExam,
      workspaceDocument: ref(contentDraft()),
    };
    const flow = useExamWorkspaceNewExam({ editing, store: guestStore(), toast });

    await flow.start();
    expect(flow.confirmOpen.value).toBe(true);

    status.value = { detail: null, state: "saving" };
    await flow.confirmReplace();

    expect(flow.confirmOpen.value).toBe(false);
    expect(newExam).not.toHaveBeenCalled();
    expect(toast.failure).toHaveBeenCalledTimes(1);
    expect(toast.failure).toHaveBeenCalledWith(PENDING_SAVE_COPY);
  });

  it("Ersätt asks again when the cursor moved while the confirm was open", async () => {
    const cursor = ref<string | null>(CURSOR);
    const toast = { failure: vi.fn() };
    const newExam = vi.fn(async (): Promise<ExamWorkspaceNewExamOutcome> => "created");
    const loadSavedDocuments = vi.fn(async (): Promise<void> => undefined);
    const editing: UseExamWorkspaceNewExamDeps["editing"] = {
      history: {
        saveStatus: computed(
          (): ExamWorkspaceSaveStatus => ({
            detail: null,
            savedAt: "2026-10-21T10:00:00Z",
            state: "saved",
          }),
        ),
      },
      historyCursor: computed(() => cursor.value),
      isBusy: computed(() => false),
      isDirty: computed(() => false),
      isOpenBlockedByOtherOperation: computed(() => false),
      loadSavedDocuments,
      newExam,
      workspaceDocument: ref(contentDraft()),
    };
    const flow = useExamWorkspaceNewExam({ editing, store: guestStore(), toast });

    await flow.start();
    cursor.value = "moved-cursor";
    await flow.confirmReplace();

    expect(newExam).not.toHaveBeenCalled();
    expect(flow.confirmOpen.value).toBe(true);
  });
});
