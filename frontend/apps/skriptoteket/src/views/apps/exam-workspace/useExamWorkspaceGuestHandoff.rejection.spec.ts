/**
 * Guest handoff typed outcomes and recorded rejections (TASK-SKRIPT-41-02-05, U2a).
 *
 * Expected behavior:
 *   One handoff attempt returns a typed outcome. Permanent and vault_full
 *   rejections are recorded per draft cursor; while the record matches the
 *   stored draft's cursor, later calls return the rejection without posting.
 *   A vault-full record is bypassed only by a retry naming that same cursor.
 *   No toast is shown in any case.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { ApiError } from "../../../api/client";

import {
  createInMemoryExamWorkspaceGuestDraftStorage,
  type StoredGuestDraft,
} from "./examWorkspaceGuestDraftStorage";
import { createInMemoryGuestHandoffRejectionStorage } from "./examWorkspaceGuestHandoffRejection";
import { createInMemoryGuestHandoffLock } from "./examWorkspaceGuestHandoffLock";
import {
  editedGuestDraft as editedDraft,
  guestHandoffApiError as apiError,
  guestHandoffFailureToasts as failureToasts,
  guestHandoffOwnerStub,
  guestHandoffTeacherMock as teacherMock,
  GUEST_HANDOFF_SPEC_NOW as NOW,
  seedGuestHandoffHarness as seedHarness,
} from "./useExamWorkspaceGuestHandoff.specSupport";
import type { ExamWorkspaceGuestDraft } from "./examWorkspaceGuestDraft";
import { runGuestHandoff } from "./useExamWorkspaceGuestHandoff";

beforeEach(() => {
  setActivePinia(createPinia());
});

describe("runGuestHandoff rejections", () => {
  it("a) 422 DOCUMENT_SCHEMA_OUTDATED rejects permanent, keeps the draft, records, and never posts again", async () => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(
      apiError(422, "DOCUMENT_SCHEMA_OUTDATED"),
    );

    const first = await runGuestHandoff({ lock, owner, rejections, storage, teacher });
    expect(first).toEqual({ draft, kind: "rejected", reason: "permanent" });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(rejections.read()).toEqual({ cursor: draft.cursor, reason: "permanent" });
    const kept: StoredGuestDraft | null = await storage.load();
    expect(kept?.draft).toEqual(draft);

    const second = await runGuestHandoff({ lock, owner, rejections, storage, teacher });
    expect(second).toEqual({ draft, kind: "rejected", reason: "permanent" });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(failureToasts()).toEqual([]);
  });

  it("b) 422 VALIDATION_ERROR rejects permanent and never posts again", async () => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "VALIDATION_ERROR"));

    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "permanent",
    });
    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "permanent",
    });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(rejections.read()).toEqual({ cursor: draft.cursor, reason: "permanent" });
    expect(failureToasts()).toEqual([]);
  });

  it("c) 413 PAYLOAD_TOO_LARGE rejects permanent and never posts again", async () => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(413, "PAYLOAD_TOO_LARGE"));

    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "permanent",
    });
    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "permanent",
    });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(failureToasts()).toEqual([]);
  });

  it("d) vault_full is remembered, skipped without posting, and retried only when the retry names its cursor", async () => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(
      apiError(422, "VALIDATION_ERROR", { reason: "vault_full" }),
    );

    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "vault_full",
    });
    expect(rejections.read()).toEqual({ cursor: draft.cursor, reason: "vault_full" });

    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "vault_full",
    });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);

    await expect(
      runGuestHandoff(
        { lock, owner, rejections, storage, teacher },
        { retryVaultFullOf: draft.cursor },
      ),
    ).resolves.toEqual({ draft, kind: "rejected", reason: "vault_full" });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
    expect(failureToasts()).toEqual([]);
  });

  it("e) a declared picture with no stored bytes rejects permanent with zero POSTs", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const rejections = createInMemoryGuestHandoffRejectionStorage();
    const lock = createInMemoryGuestHandoffLock();
    const owner = guestHandoffOwnerStub();
    const { draft } = editedDraft();
    expect(await storage.replaceIf(null, {
      assets: { asset_a: new Blob(["a"]) },
      draft,
    })).toBe(true);
    const teacher = teacherMock();

    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "permanent",
    });
    expect(teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
    expect(rejections.read()).toEqual({ cursor: draft.cursor, reason: "permanent" });
    expect(failureToasts()).toEqual([]);
  });

  it("f) a draft whose position snapshot is missing resolves rejected permanent with zero POSTs", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const rejections = createInMemoryGuestHandoffRejectionStorage();
    const lock = createInMemoryGuestHandoffLock();
    const owner = guestHandoffOwnerStub();
    const { draft } = editedDraft();
    const broken: ExamWorkspaceGuestDraft = { ...draft, position_step_id: "missing-step" };
    expect(await storage.replaceIf(null, { assets: {}, draft: broken })).toBe(true);
    const teacher = teacherMock();

    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      draft: broken,
      kind: "rejected",
      reason: "permanent",
    });
    expect(teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
    expect(rejections.read()).toEqual({ cursor: broken.cursor, reason: "permanent" });
    expect(failureToasts()).toEqual([]);
  });

  it.each([
    ["503", apiError(503, "SERVICE_UNAVAILABLE")],
    ["429", apiError(429, "RATE_LIMITED")],
    ["fetch TypeError", new TypeError("Failed to fetch")],
  ])("g) %s returns transient, records nothing, and posts again", async (_label, error) => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(error);

    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      kind: "transient",
    });
    expect(rejections.read()).toBeNull();
    const kept = await storage.load();
    expect(kept?.draft).toEqual(draft);

    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      kind: "transient",
    });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
    expect(failureToasts()).toEqual([]);
  });

  it("h) 401 returns deferred and records nothing", async () => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(401, "UNAUTHORIZED"));

    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      kind: "deferred",
    });
    expect(rejections.read()).toBeNull();
    const kept = await storage.load();
    expect(kept?.draft).toEqual(draft);
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(failureToasts()).toEqual([]);
  });

  it("h2) 403 AUTHORIZATION_ERROR returns deferred, records nothing, and posts again", async () => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(
      new ApiError({
        code: "AUTHORIZATION_ERROR",
        message: "CSRF token required for browser session write",
        status: 403,
      }),
    );

    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      kind: "deferred",
    });
    expect(rejections.read()).toBeNull();
    const kept = await storage.load();
    expect(kept?.draft).toEqual(draft);

    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      kind: "deferred",
    });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
    expect(failureToasts()).toEqual([]);
  });

  it("i) a stale record for another cursor is cleared and the current draft is posted", async () => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedHarness();
    rejections.write({ cursor: "other-cursor", reason: "permanent" });
    teacher.importExamWorkspaceGuestDraft.mockResolvedValue({
      conversion: null,
      document: draft.saved_document,
      export_blockers: [],
      history_cursor: draft.cursor,
      notes: [],
      saved_document: draft.saved_document,
      summary: {
        course_key: null,
        lineage_id: "lineage-new",
        name: draft.saved_document.title,
        saved_at: NOW,
        title: draft.saved_document.title,
        vault_file_id: "file-1",
        version: draft.saved_document.revision,
      },
    });

    await expect(runGuestHandoff({ lock, owner, rejections, storage, teacher })).resolves.toEqual({
      kind: "handed_off",
      lineageId: "lineage-new",
    });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(rejections.read()).toBeNull();
    expect(failureToasts()).toEqual([]);
  });

  it("j) success under the matching vault-full retry clears the draft and the record", async () => {
    const { draft, lock, owner, rejections, storage, teacher } = await seedHarness();
    rejections.write({ cursor: draft.cursor, reason: "vault_full" });
    teacher.importExamWorkspaceGuestDraft.mockResolvedValue({
      conversion: null,
      document: draft.saved_document,
      export_blockers: [],
      history_cursor: draft.cursor,
      notes: [],
      saved_document: draft.saved_document,
      summary: {
        course_key: null,
        lineage_id: "lineage-new",
        name: draft.saved_document.title,
        saved_at: NOW,
        title: draft.saved_document.title,
        vault_file_id: "file-1",
        version: draft.saved_document.revision,
      },
    });

    await expect(
      runGuestHandoff(
        { lock, owner, rejections, storage, teacher },
        { retryVaultFullOf: draft.cursor },
      ),
    ).resolves.toEqual({ kind: "handed_off", lineageId: "lineage-new" });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    await expect(storage.load()).resolves.toBeNull();
    expect(rejections.read()).toBeNull();
    expect(failureToasts()).toEqual([]);
  });

  it("k) no toast is shown in any failure case", async () => {
    const { lock, owner, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(
      apiError(422, "DOCUMENT_SCHEMA_OUTDATED"),
    );

    await runGuestHandoff({ lock, owner, rejections, storage, teacher });
    await runGuestHandoff({ lock, owner, rejections, storage, teacher });
    expect(failureToasts()).toEqual([]);
  });
});
