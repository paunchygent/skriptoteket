/**
 * Guest handoff controller: first attempt, backoff, toasts and notice actions
 * (TASK-SKRIPT-41-02-05, U2b).
 *
 * Expected behavior:
 *   The first attempt gates the view. Transient failures show one toast and
 *   retry in the background with doubling delay, at most three times; the last
 *   failure shows one more toast. Rejections leave a notice with download,
 *   remove and (vault-full) manual retry actions. Disposing the scope stops
 *   timers and silences late completions.
 */

import { createPinia, setActivePinia } from "pinia";
import { effectScope } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useToastStore } from "../../../stores/toast";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
import { createInMemoryGuestHandoffRejectionStorage } from "./examWorkspaceGuestHandoffRejection";
import type { ExamWorkspaceGuestDraft } from "./examWorkspaceGuestDraft";
import {
  editedGuestDraft,
  guestHandoffApiError as apiError,
  seedGuestHandoffHarness,
} from "./useExamWorkspaceGuestHandoff.specSupport";
import {
  GUEST_HANDOFF_LATE_SUCCESS_COPY,
  GUEST_HANDOFF_MANUAL_RETRY_FAILED_COPY,
  GUEST_HANDOFF_RETRIES_EXHAUSTED_COPY,
  GUEST_HANDOFF_TRANSIENT_COPY,
  useExamWorkspaceGuestHandoffController,
} from "./useExamWorkspaceGuestHandoffController";
import {
  type GuestHandoffDeps,
  type GuestHandoffTeacher,
} from "./useExamWorkspaceGuestHandoff";

type ImportResult = Awaited<ReturnType<GuestHandoffTeacher["importExamWorkspaceGuestDraft"]>>;

function successResult(draft: ExamWorkspaceGuestDraft, lineageId = "lineage-new"): ImportResult {
  return {
    conversion: null,
    document: draft.saved_document,
    export_blockers: [],
    history_cursor: draft.cursor,
    notes: [],
    saved_document: draft.saved_document,
    summary: {
      course_key: null,
      lineage_id: lineageId,
      name: draft.saved_document.title,
      saved_at: draft.saved_at,
      title: draft.saved_document.title,
      vault_file_id: "file-1",
      version: draft.saved_document.revision,
    },
  };
}

function toastSpies() {
  const store = useToastStore();
  return {
    failure: vi.spyOn(store, "failure"),
    success: vi.spyOn(store, "success"),
    warning: vi.spyOn(store, "warning"),
  };
}

function toastMessages(spy: { mock: { calls: Array<[string, ...unknown[]]> } }): string[] {
  return spy.mock.calls.map((call) => call[0]);
}

/**
 * jsdom's Blob has no `text` and its Response cannot consume a Blob; read the
 * download bytes through FileReader like the production fallback.
 */
async function blobText(blob: Blob): Promise<string> {
  return await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
        return;
      }
      reject(new Error("The FileReader did not return text."));
    };
    reader.onerror = () => reject(reader.error ?? new Error("Could not read the blob text."));
    reader.readAsText(blob);
  });
}

function startController(deps: GuestHandoffDeps, download?: (blob: Blob, filename: string) => void) {
  const scope = effectScope();
  const controller = scope.run(() =>
    useExamWorkspaceGuestHandoffController(deps, download === undefined ? undefined : { download }),
  );
  if (controller === undefined) {
    throw new Error("expected the scope to produce a controller");
  }
  return { controller, scope };
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("useExamWorkspaceGuestHandoffController", () => {
  it("1) transient at start retries three times with doubling delay, then stops", async () => {
    const { rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(503, "SERVICE_UNAVAILABLE"));
    const { controller, scope } = startController({ rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
      expect(useToastStore().toasts.map((toast) => toast.message)).toEqual([
        GUEST_HANDOFF_TRANSIENT_COPY,
      ]);

      await vi.advanceTimersByTimeAsync(4_999);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
      await vi.advanceTimersByTimeAsync(1);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
      expect(toastMessages(spies.warning)).toEqual([GUEST_HANDOFF_TRANSIENT_COPY]);

      await vi.advanceTimersByTimeAsync(10_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(3);
      expect(toastMessages(spies.warning)).toEqual([GUEST_HANDOFF_TRANSIENT_COPY]);

      await vi.advanceTimersByTimeAsync(20_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(4);
      expect(toastMessages(spies.warning)).toEqual([
        GUEST_HANDOFF_TRANSIENT_COPY,
        GUEST_HANDOFF_RETRIES_EXHAUSTED_COPY,
      ]);

      await vi.advanceTimersByTimeAsync(3_600_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(4);
    } finally {
      scope.stop();
    }
  });

  it("2) a late success on retry #2 toasts, clears the draft and stops", async () => {
    const { draft, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft
      .mockRejectedValueOnce(apiError(503, "SERVICE_UNAVAILABLE"))
      .mockRejectedValueOnce(apiError(503, "SERVICE_UNAVAILABLE"))
      .mockResolvedValue(successResult(draft));
    const { controller, scope } = startController({ rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      await vi.advanceTimersByTimeAsync(5_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
      expect(toastMessages(spies.success)).toEqual([]);

      await vi.advanceTimersByTimeAsync(10_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(3);
      expect(toastMessages(spies.success)).toEqual([GUEST_HANDOFF_LATE_SUCCESS_COPY]);
      await expect(storage.load()).resolves.toBeNull();

      await vi.advanceTimersByTimeAsync(3_600_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(3);
    } finally {
      scope.stop();
    }
  });

  it("3) permanent at start leaves a notice, no toast and no retry", async () => {
    const { rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const { controller, scope } = startController({ rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
      expect(spies.warning).not.toHaveBeenCalled();
      expect(spies.success).not.toHaveBeenCalled();
      expect(spies.failure).not.toHaveBeenCalled();

      await vi.advanceTimersByTimeAsync(3_600_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    } finally {
      scope.stop();
    }
  });

  it.each([
    ["429", apiError(429, "RATE_LIMITED")],
    ["fetch TypeError", new TypeError("Failed to fetch")],
  ])("4) %s follows the transient path with a retry at 5s", async (_label, error) => {
    const { rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(error);
    const { controller, scope } = startController({ rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
      expect(toastMessages(spies.warning)).toEqual([GUEST_HANDOFF_TRANSIENT_COPY]);
      expect(controller.notice.value).toBeNull();

      await vi.advanceTimersByTimeAsync(5_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
    } finally {
      scope.stop();
    }
  });

  it("5) 401 shows nothing and never retries", async () => {
    const { rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(401, "UNAUTHORIZED"));
    const { controller, scope } = startController({ rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(controller.notice.value).toBeNull();
      expect(spies.warning).not.toHaveBeenCalled();
      expect(spies.success).not.toHaveBeenCalled();
      expect(spies.failure).not.toHaveBeenCalled();

      await vi.advanceTimersByTimeAsync(3_600_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    } finally {
      scope.stop();
    }
  });

  it("6a) vault_full retry posts again ignoring the record; success closes the notice", async () => {
    const { draft, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft
      .mockRejectedValueOnce(apiError(422, "VALIDATION_ERROR", { reason: "vault_full" }))
      .mockResolvedValue(successResult(draft));
    const { controller, scope } = startController({ rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(controller.notice.value).toEqual({ reason: "vault_full", busy: false });
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);

      await controller.retry();
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
      expect(controller.notice.value).toBeNull();
      expect(toastMessages(spies.success)).toEqual([GUEST_HANDOFF_LATE_SUCCESS_COPY]);
      await expect(storage.load()).resolves.toBeNull();
    } finally {
      scope.stop();
    }
  });

  it("6b) vault_full retry can turn permanent with a new draft", async () => {
    const { rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft
      .mockRejectedValueOnce(apiError(422, "VALIDATION_ERROR", { reason: "vault_full" }))
      .mockRejectedValueOnce(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const { controller, scope } = startController({ rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      await controller.retry();
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
      expect(spies.warning).not.toHaveBeenCalled();
      expect(spies.success).not.toHaveBeenCalled();
      expect(spies.failure).not.toHaveBeenCalled();
    } finally {
      scope.stop();
    }
  });

  it("6c) vault_full retry failing transiently keeps the notice, toasts failure, no schedule", async () => {
    const { rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft
      .mockRejectedValueOnce(apiError(422, "VALIDATION_ERROR", { reason: "vault_full" }))
      .mockRejectedValue(apiError(503, "SERVICE_UNAVAILABLE"));
    const { controller, scope } = startController({ rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      await controller.retry();
      expect(controller.notice.value).toEqual({ reason: "vault_full", busy: false });
      expect(toastMessages(spies.failure)).toEqual([GUEST_HANDOFF_MANUAL_RETRY_FAILED_COPY]);

      await vi.advanceTimersByTimeAsync(3_600_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
    } finally {
      scope.stop();
    }
  });

  it("7) download saves the held draft under its title, Prov for a blank title", async () => {
    const { draft, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const download = vi.fn<(blob: Blob, filename: string) => void>();
    const { controller, scope } = startController({ rejections, storage, teacher }, download);
    try {
      await expect(controller.start()).resolves.toBeNull();
      controller.download();
      expect(download).toHaveBeenCalledTimes(1);
      const [blob, filename] = download.mock.calls[0];
      expect(filename).toBe(`${draft.saved_document.title}.json`);
      // FileReader never fires under fake timers; no retry timer is pending here.
      vi.useRealTimers();
      expect(JSON.parse(await blobText(blob))).toEqual(draft);
    } finally {
      scope.stop();
    }
  });

  it("7b) download falls back to Prov.json when the title is blank", async () => {
    const blankStorage = createInMemoryExamWorkspaceGuestDraftStorage();
    const blankRejections = createInMemoryGuestHandoffRejectionStorage();
    const { draft: base } = editedGuestDraft();
    const blank: ExamWorkspaceGuestDraft = {
      ...base,
      saved_document: { ...base.saved_document, title: "   " },
    };
    expect(await blankStorage.replaceIf(null, { assets: {}, draft: blank })).toBe(true);
    const { teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const download = vi.fn<(blob: Blob, filename: string) => void>();
    const { controller, scope } = startController(
      { rejections: blankRejections, storage: blankStorage, teacher },
      download,
    );
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
      controller.download();
      expect(download).toHaveBeenCalledTimes(1);
      const [blob, filename] = download.mock.calls[0];
      expect(filename).toBe("Prov.json");
      // FileReader never fires under fake timers; no retry timer is pending here.
      vi.useRealTimers();
      expect(JSON.parse(await blobText(blob))).toEqual(blank);
    } finally {
      scope.stop();
    }
  });

  it("8a) remove clears the draft, the record and the notice", async () => {
    const { rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const { controller, scope } = startController({ rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      await controller.remove();
      await expect(storage.load()).resolves.toBeNull();
      expect(rejections.read()).toBeNull();
      expect(controller.notice.value).toBeNull();
      expect(spies.warning).not.toHaveBeenCalled();
      expect(spies.success).not.toHaveBeenCalled();
      expect(spies.failure).not.toHaveBeenCalled();
    } finally {
      scope.stop();
    }
  });

  it("8b) remove keeps the notice and the record when clearIf throws", async () => {
    const { draft, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const failingStorage = {
      ...storage,
      clearIf: vi.fn<() => Promise<boolean>>().mockRejectedValue(new Error("locked")),
    };
    const { controller, scope } = startController({
      rejections,
      storage: failingStorage,
      teacher,
    });
    try {
      await expect(controller.start()).resolves.toBeNull();
      await controller.remove();
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
      expect(rejections.read()).toEqual({ cursor: draft.cursor, reason: "permanent" });
      await expect(storage.load()).resolves.not.toBeNull();
    } finally {
      scope.stop();
    }
  });

  it("9a) stopping the scope while a retry is pending makes no second POST", async () => {
    const { rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(503, "SERVICE_UNAVAILABLE"));
    const { controller, scope } = startController({ rejections, storage, teacher });
    const spies = toastSpies();
    await expect(controller.start()).resolves.toBeNull();
    scope.stop();

    await vi.advanceTimersByTimeAsync(3_600_000);
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(toastMessages(spies.warning)).toEqual([GUEST_HANDOFF_TRANSIENT_COPY]);
  });

  it("9b) an attempt resolving after dispose shows no toast", async () => {
    const { draft, rejections, storage, teacher } = await seedGuestHandoffHarness();
    const pendingPost: { resolve: ((value: ImportResult) => void) | null } = { resolve: null };
    teacher.importExamWorkspaceGuestDraft.mockImplementationOnce(
      () =>
        new Promise<ImportResult>((resolve) => {
          pendingPost.resolve = resolve;
        }),
    );
    const { controller, scope } = startController({ rejections, storage, teacher });
    const spies = toastSpies();
    const pending = controller.start();
    // Let the first attempt reach the teacher POST so it is in flight.
    await vi.advanceTimersByTimeAsync(0);
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    scope.stop();
    pendingPost.resolve?.(successResult(draft));
    await expect(pending).resolves.toBeNull();
    expect(spies.warning).not.toHaveBeenCalled();
    expect(spies.success).not.toHaveBeenCalled();
    expect(spies.failure).not.toHaveBeenCalled();
    expect(controller.notice.value).toBeNull();
  });

  it("10) retry while busy is ignored to one POST", async () => {
    const { draft, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft
      .mockRejectedValueOnce(apiError(422, "VALIDATION_ERROR", { reason: "vault_full" }))
      .mockResolvedValue(successResult(draft));
    const { controller, scope } = startController({ rejections, storage, teacher });
    try {
      await expect(controller.start()).resolves.toBeNull();
      const first = controller.retry();
      const second = controller.retry();
      await Promise.all([first, second]);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
      expect(controller.notice.value).toBeNull();
    } finally {
      scope.stop();
    }
  });
});
