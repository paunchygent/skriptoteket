/**
 * Guest handoff held-read lifecycle proof (TASK-SKRIPT-41-02-05, U9a; R7).
 *
 * Expected behavior (fixed):
 *   a) Disposing the controller while the first draft load is pending settles
 *      start at once, admits a second lock user before the old load is
 *      released, posts nothing, and the late load resolves to no POST and no
 *      record.
 *   b) Aborting the attempt signal during the first load defers at once and
 *      frees the lock; the late load resolves to no POST and no record.
 *   c) Aborting during the permanent-failure re-load defers at once, records
 *      nothing, and frees the lock.
 *   d) Aborting during the unlocked load after a lock refusal defers at once.
 *   e) A 200 POST with the signal intact still clears the posted snapshot.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import type { ExamWorkspaceDocumentResponse } from "../../../api/examWorkspace";
import type { ExamWorkspaceGuestDraft } from "./examWorkspaceGuestDraft";
import type { StoredGuestDraft } from "./examWorkspaceGuestDraftStorage";
import {
  GuestHandoffLockUnavailableError,
  type GuestHandoffLockPort,
} from "./examWorkspaceGuestHandoffLock";
import { runGuestHandoff } from "./useExamWorkspaceGuestHandoff";
import { useExamWorkspaceGuestHandoffController } from "./useExamWorkspaceGuestHandoffController";
import {
  guestHandoffApiError,
  liveAttempt,
  seedGuestHandoffHarness,
} from "./useExamWorkspaceGuestHandoff.specSupport";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, reject, resolve };
}

function handoffResponse(draft: ExamWorkspaceGuestDraft, lineageId: string): ExamWorkspaceDocumentResponse {
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

beforeEach(() => {
  setActivePinia(createPinia());
  localStorage.clear();
});

describe("runGuestHandoff held-read lifecycle", () => {
  it(
    "a) disposing during the held draft read settles start and admits a later live host before the old read is released",
    { timeout: 2_000 },
    async () => {
      const deps = await seedGuestHandoffHarness();
      const stored = await deps.storage.load();
      const entered = deferred<void>();
      const load = deferred<StoredGuestDraft | null>();
      const storage = { ...deps.storage, load: () => { entered.resolve(); return load.promise; } };
      const scope = effectScope();
      const controller = scope.run(() => useExamWorkspaceGuestHandoffController({ ...deps, storage }))!;
      const first = controller.start();
      await entered.promise;
      scope.stop();
      const secondEntered = deferred<void>();
      let secondStarted = false;
      const second = deps.lock.run(async () => { secondStarted = true; secondEntered.resolve(); return true; }, new AbortController().signal);
      await secondEntered.promise;
      expect(secondStarted).toBe(true);
      await expect(first).resolves.toBeNull();
      await second;
      expect(deps.teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
      load.resolve(stored);
      await Promise.resolve();
      await Promise.resolve();
      expect(deps.teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
      expect(deps.rejections.read()).toBeNull();
    }
  );

  it(
    "b) aborting the signal during the first load defers at once and frees the lock",
    { timeout: 2_000 },
    async () => {
      const { lock, owner, rejections, storage, teacher } = await seedGuestHandoffHarness();
      const stored = await storage.load();
      const entered = deferred<void>();
      const load = deferred<StoredGuestDraft | null>();
      const gated = { ...storage, load: () => { entered.resolve(); return load.promise; } };
      const attempt = new AbortController();
      const pending = runGuestHandoff(
        { lock, owner, rejections, storage: gated, teacher },
        { signal: attempt.signal },
      );
      await entered.promise;
      attempt.abort();
      await expect(pending).resolves.toEqual({ kind: "deferred" });
      expect(teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
      expect(rejections.read()).toBeNull();
      const secondEntered = deferred<void>();
      const second = lock.run(async () => { secondEntered.resolve(); return true; }, new AbortController().signal);
      await secondEntered.promise;
      await second;
      load.resolve(stored);
      await Promise.resolve();
      await Promise.resolve();
      expect(teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
      expect(rejections.read()).toBeNull();
    }
  );

  it(
    "c) aborting during the permanent-failure re-load defers with no record and frees the lock",
    { timeout: 2_000 },
    async () => {
      const { lock, owner, rejections, storage, teacher } = await seedGuestHandoffHarness();
      teacher.importExamWorkspaceGuestDraft.mockRejectedValue(guestHandoffApiError(422));
      let loads = 0;
      const reload = deferred<StoredGuestDraft | null>();
      const gated = {
        ...storage,
        load: () => {
          loads += 1;
          return loads === 1 ? storage.load() : reload.promise;
        },
      };
      const attempt = new AbortController();
      const pending = runGuestHandoff(
        { lock, owner, rejections, storage: gated, teacher },
        { signal: attempt.signal },
      );
      await vi.waitFor(() => expect(loads).toBe(2));
      attempt.abort();
      await expect(pending).resolves.toEqual({ kind: "deferred" });
      expect(rejections.read()).toBeNull();
      const secondEntered = deferred<void>();
      const second = lock.run(async () => { secondEntered.resolve(); return true; }, new AbortController().signal);
      await secondEntered.promise;
      await second;
      reload.resolve(await storage.load());
      await Promise.resolve();
      await Promise.resolve();
      expect(rejections.read()).toBeNull();
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    }
  );

  it(
    "d) aborting during the unlocked load after a lock refusal defers at once",
    { timeout: 2_000 },
    async () => {
      const { owner, rejections, storage, teacher } = await seedGuestHandoffHarness();
      const stored = await storage.load();
      const entered = deferred<void>();
      const load = deferred<StoredGuestDraft | null>();
      const gated = { ...storage, load: () => { entered.resolve(); return load.promise; } };
      const failingLock: GuestHandoffLockPort = {
        run<T>(_work: () => Promise<T>, _signal: AbortSignal): Promise<T> {
          return Promise.reject(new GuestHandoffLockUnavailableError("Web Locks are unavailable."));
        },
      };
      const attempt = new AbortController();
      const pending = runGuestHandoff(
        { lock: failingLock, owner, rejections, storage: gated, teacher },
        { signal: attempt.signal },
      );
      await entered.promise;
      attempt.abort();
      await expect(pending).resolves.toEqual({ kind: "deferred" });
      load.resolve(stored);
      await Promise.resolve();
      await Promise.resolve();
      expect(teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
      expect(rejections.read()).toBeNull();
    }
  );

  it("e) a 200 POST with the signal intact still clears the posted snapshot", async () => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockResolvedValue(handoffResponse(draft, "lineage-new"));
    await expect(
      runGuestHandoff({ lock, owner, rejections, storage, teacher }, liveAttempt()),
    ).resolves.toEqual({ kind: "handed_off", lineageId: "lineage-new" });
    await expect(storage.load()).resolves.toBeNull();
  });
});
