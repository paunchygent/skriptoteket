/**
 * Guest handoff race repair proof (TASK-SKRIPT-41-02-05, U7a).
 *
 * Expected behavior (review ba74ef97 R1-R4, fixed):
 *   a) A session retired during the pending draft load defers: no POST, no record.
 *   b) An owner retired during the pending load posts nothing and records nothing.
 *   c) A late permanent failure for A after B replaced the slot and was
 *      recorded leaves B's record; a following B run makes no POST.
 *   d) A success for A after B was recorded leaves B's record unchanged.
 *   e) A record for B with retryVaultFullOf A returns rejected B, no POST.
 *   f) A vault_full record for A with retryVaultFullOf A posts once.
 *   g) Two concurrent attempts over one lock and one shared localStorage make
 *      exactly one POST; the second sees the first permanent record.
 *   h) Removing stale A keeps B's record; the next B load makes no POST.
 *   i) A 200 arriving after the owner retired still clears the posted
 *      snapshot and its record, defers, and causes no B POST.
 *   j) A 422 arriving after the owner retired defers and clears nothing.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import type { ExamWorkspaceDocumentResponse } from "../../../api/examWorkspace";
import { importExamWorkspaceGuestDraft } from "../../../api/examWorkspace";
import { useAuthStore } from "../../../stores/auth";
import { createTestUser } from "../../../stores/authTestHelpers";
import type { StoredGuestDraft } from "./examWorkspaceGuestDraftStorage";
import {
  createLocalStorageGuestHandoffRejectionStorage,
} from "./examWorkspaceGuestHandoffRejection";
import type { ExamWorkspaceGuestDraft } from "./examWorkspaceGuestDraft";
import { runGuestHandoff } from "./useExamWorkspaceGuestHandoff";
import { useExamWorkspaceGuestHandoffController } from "./useExamWorkspaceGuestHandoffController";
import {
  guestHandoffApiError,
  guestHandoffOwnerStub,
  seedGuestHandoffHarness,
} from "./useExamWorkspaceGuestHandoff.specSupport";

const B_CURSOR = "20000000-0000-4000-8000-000000000002";

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

async function replaceSlotWithB(
  storage: Awaited<ReturnType<typeof seedGuestHandoffHarness>>["storage"],
): Promise<ExamWorkspaceGuestDraft> {
  const current = (await storage.load())!;
  const b = { ...current.draft, cursor: B_CURSOR };
  expect(await storage.replaceIf(current.draft.cursor, { ...current, draft: b })).toBe(true);
  return b;
}

beforeEach(() => {
  setActivePinia(createPinia());
  localStorage.clear();
});

describe("runGuestHandoff races", () => {
  it("a) a session retired during the pending draft load defers with no POST and no record", async () => {
    const { lock, rejections, storage } = await seedGuestHandoffHarness();
    const stored = await storage.load();
    const load = deferred<StoredGuestDraft | null>();
    const auth = useAuthStore();
    auth.$patch({
      csrfToken: "csrf-a",
      sharedSessionId: "session-a",
      user: createTestUser({ id: "10000000-0000-4000-8000-000000000001" }),
    });
    const sessionA = auth.captureSession();
    vi.mocked(fetch).mockImplementation(async () =>
      new Response(JSON.stringify({ error: { code: "VALIDATION_ERROR", message: "rejected" } }), {
        headers: { "Content-Type": "application/json" },
        status: 422,
      }),
    );
    const pending = runGuestHandoff({
      lock,
      owner: { isLive: () => auth.isCurrentSession(sessionA), session: sessionA },
      rejections,
      storage: { ...storage, load: () => load.promise },
      teacher: { importExamWorkspaceGuestDraft },
    });
    auth.$patch({
      csrfToken: "csrf-b",
      sharedSessionId: "session-b",
      user: createTestUser({ id: "20000000-0000-4000-8000-000000000002" }),
    });
    expect(auth.isCurrentSession(sessionA)).toBe(false);
    load.resolve(stored);
    await expect(pending).resolves.toEqual({ kind: "deferred" });
    expect(vi.mocked(fetch)).not.toHaveBeenCalled();
    expect(rejections.read()).toBeNull();
  });

  it("b) an owner retired during the pending load posts nothing and records nothing", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    const stored = await storage.load();
    const load = deferred<StoredGuestDraft | null>();
    let live = true;
    const pending = runGuestHandoff({
      lock,
      owner: { isLive: () => live, session: Symbol("guest handoff owner") },
      rejections,
      storage: { ...storage, load: () => load.promise },
      teacher,
    });
    live = false;
    load.resolve(stored);
    await expect(pending).resolves.toEqual({ kind: "deferred" });
    expect(teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
    expect(rejections.read()).toBeNull();
  });

  it("c) a late permanent failure for A after B was recorded leaves B and posts no more", async () => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedGuestHandoffHarness();
    const old = deferred<never>();
    teacher.importExamWorkspaceGuestDraft
      .mockReturnValueOnce(old.promise)
      .mockRejectedValue(guestHandoffApiError(422));
    const pendingA = runGuestHandoff({ lock, owner, rejections, storage, teacher });
    await vi.waitFor(() => expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1));
    const b = await replaceSlotWithB(storage);
    const pendingB = runGuestHandoff({ lock, owner, rejections, storage, teacher });
    old.reject(guestHandoffApiError(422));
    await expect(pendingA).resolves.toEqual({ kind: "none" });
    await expect(pendingB).resolves.toEqual({ draft: b, kind: "rejected", reason: "permanent" });
    expect(rejections.read()).toEqual({ cursor: b.cursor, reason: "permanent" });
    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      draft: b,
      kind: "rejected",
      reason: "permanent",
    });
    expect(teacher.importExamWorkspaceGuestDraft.mock.calls.map((call) => call[0])).toEqual([
      draft.cursor,
      b.cursor,
    ]);
  });

  it("d) a success for A after B was recorded leaves B's record unchanged", async () => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedGuestHandoffHarness();
    let resolvePost!: (value: ExamWorkspaceDocumentResponse) => void;
    const post = new Promise<ExamWorkspaceDocumentResponse>((resolve) => {
      resolvePost = resolve;
    });
    teacher.importExamWorkspaceGuestDraft.mockReturnValue(post);
    const pendingA = runGuestHandoff({ lock, owner, rejections, storage, teacher });
    await vi.waitFor(() => expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1));
    const b = await replaceSlotWithB(storage);
    rejections.write({ cursor: b.cursor, reason: "permanent" });
    resolvePost(handoffResponse(draft, "lineage-a"));
    await expect(pendingA).resolves.toEqual({ kind: "handed_off", lineageId: "lineage-a" });
    expect(rejections.read()).toEqual({ cursor: b.cursor, reason: "permanent" });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      draft: b,
      kind: "rejected",
      reason: "permanent",
    });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
  });

  it("e) a permanent record for B is honoured when retry names A", async () => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedGuestHandoffHarness();
    const b = await replaceSlotWithB(storage);
    rejections.write({ cursor: b.cursor, reason: "permanent" });
    await expect(
      runGuestHandoff({ lock, owner, rejections, storage, teacher }, { retryVaultFullOf: draft.cursor }),
    ).resolves.toEqual({ draft: b, kind: "rejected", reason: "permanent" });
    expect(teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
  });

  it("f) a vault_full record for A posts once when retry names A", async () => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(
      guestHandoffApiError(422, "VALIDATION_ERROR", { reason: "vault_full" }),
    );
    rejections.write({ cursor: draft.cursor, reason: "vault_full" });
    await expect(
      runGuestHandoff({ lock, owner, rejections, storage, teacher }, { retryVaultFullOf: draft.cursor }),
    ).resolves.toEqual({ draft, kind: "rejected", reason: "vault_full" });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
  });

  it("g) two concurrent attempts make exactly one POST; the second sees the permanent record", async () => {
    const { draft, lock, owner, storage, teacher } = await seedGuestHandoffHarness();
    const one = createLocalStorageGuestHandoffRejectionStorage();
    const two = createLocalStorageGuestHandoffRejectionStorage();
    const reply = deferred<never>();
    teacher.importExamWorkspaceGuestDraft.mockReturnValue(reply.promise);
    const first = runGuestHandoff({ lock, owner, rejections: one, storage, teacher });
    const second = runGuestHandoff({ lock, owner, rejections: two, storage, teacher });
    await vi.waitFor(() => expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1));
    reply.reject(guestHandoffApiError(422));
    await expect(first).resolves.toEqual({ draft, kind: "rejected", reason: "permanent" });
    await expect(second).resolves.toEqual({ draft, kind: "rejected", reason: "permanent" });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(two.read()).toEqual({ cursor: draft.cursor, reason: "permanent" });
  });

  it("h) removing stale A keeps B's record and the next B load makes no POST", async () => {
    const { draft, lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(guestHandoffApiError(422));
    const scope = effectScope();
    const controller = scope.run(() =>
      useExamWorkspaceGuestHandoffController({ lock, rejections, storage, teacher }),
    )!;
    try {
      await controller.start();
      const b = await replaceSlotWithB(storage);
      await runGuestHandoff({
        lock,
        owner: guestHandoffOwnerStub(),
        rejections,
        storage,
        teacher,
      });
      expect(rejections.read()).toEqual({ cursor: b.cursor, reason: "permanent" });
      await controller.remove();
      expect((await storage.load())?.draft.cursor).toBe(b.cursor);
      expect(rejections.read()).toEqual({ cursor: b.cursor, reason: "permanent" });
      await expect(
        runGuestHandoff({ lock, owner: guestHandoffOwnerStub(), rejections, storage, teacher }),
      ).resolves.toEqual({ draft: b, kind: "rejected", reason: "permanent" });
      expect(teacher.importExamWorkspaceGuestDraft.mock.calls.map((call) => call[0])).toEqual([
        draft.cursor,
        b.cursor,
      ]);
    } finally {
      scope.stop();
    }
  });

  it("i) a 200 arriving after the owner retired clears the saved snapshot and defers; B makes no POST", async () => {
    const { draft, lock, rejections, storage } = await seedGuestHandoffHarness();
    const auth = useAuthStore();
    auth.$patch({
      csrfToken: "csrf-a",
      sharedSessionId: "session-a",
      user: createTestUser({ id: "10000000-0000-4000-8000-000000000001" }),
    });
    const sessionA = auth.captureSession();
    const sent = deferred<void>();
    const response = deferred<Response>();
    const requests: string[] = [];
    vi.mocked(fetch).mockImplementationOnce(() => {
      requests.push(auth.user?.id ?? "anonymous");
      sent.resolve();
      return response.promise;
    });
    const pending = runGuestHandoff({
      lock,
      owner: { isLive: () => auth.isCurrentSession(sessionA), session: sessionA },
      rejections,
      storage,
      teacher: { importExamWorkspaceGuestDraft },
    });
    await sent.promise;
    auth.$patch({
      csrfToken: "csrf-b",
      sharedSessionId: "session-b",
      user: createTestUser({ id: "20000000-0000-4000-8000-000000000002" }),
    });
    expect(auth.isCurrentSession(sessionA)).toBe(false);
    response.resolve(
      new Response(JSON.stringify(handoffResponse(draft, "lineage-a")), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
    );
    await expect(pending).resolves.toEqual({ kind: "deferred" });
    expect(await storage.load()).toBeNull();
    expect(rejections.read()).toBeNull();
    const sessionB = auth.captureSession();
    await expect(
      runGuestHandoff({
        lock,
        owner: { isLive: () => auth.isCurrentSession(sessionB), session: sessionB },
        rejections,
        storage,
        teacher: { importExamWorkspaceGuestDraft },
      }),
    ).resolves.toEqual({ kind: "none" });
    expect(requests).toEqual(["10000000-0000-4000-8000-000000000001"]);
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1);
  });

  it("j) a 422 arriving after the owner retired defers and clears nothing", async () => {
    const { draft, lock, rejections, storage } = await seedGuestHandoffHarness();
    const auth = useAuthStore();
    auth.$patch({
      csrfToken: "csrf-a",
      sharedSessionId: "session-a",
      user: createTestUser({ id: "10000000-0000-4000-8000-000000000001" }),
    });
    const sessionA = auth.captureSession();
    const sent = deferred<void>();
    const response = deferred<Response>();
    vi.mocked(fetch).mockImplementationOnce(() => {
      sent.resolve();
      return response.promise;
    });
    const pending = runGuestHandoff({
      lock,
      owner: { isLive: () => auth.isCurrentSession(sessionA), session: sessionA },
      rejections,
      storage,
      teacher: { importExamWorkspaceGuestDraft },
    });
    await sent.promise;
    auth.$patch({
      csrfToken: "csrf-b",
      sharedSessionId: "session-b",
      user: createTestUser({ id: "20000000-0000-4000-8000-000000000002" }),
    });
    expect(auth.isCurrentSession(sessionA)).toBe(false);
    response.resolve(
      new Response(JSON.stringify({ error: { code: "VALIDATION_ERROR", message: "rejected" } }), {
        headers: { "Content-Type": "application/json" },
        status: 422,
      }),
    );
    await expect(pending).resolves.toEqual({ kind: "deferred" });
    expect((await storage.load())?.draft.cursor).toBe(draft.cursor);
    expect(rejections.read()).toBeNull();
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1);
  });
});
