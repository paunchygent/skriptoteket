/**
 * Guest handoff spec support (TASK-SKRIPT-41-02-05, U2b).
 *
 * Domain purpose:
 *   Shared in-memory harness builders for the guest handoff specs: one
 *   seeded draft with picture bytes, a vi.fn teacher double, and real
 *   ApiError instances. Both the outcome spec and the controller spec build
 *   on this so the two files stay under their line budget.
 *
 * Relationships:
 *   - Imported by `useExamWorkspaceGuestHandoff.rejection.spec.ts` and
 *     `useExamWorkspaceGuestHandoffController.spec.ts`; no production reader.
 */

import { useToastStore } from "../../../stores/toast";
import {
  createInMemoryExamWorkspaceGuestDraftStorage,
  type ExamWorkspaceGuestDraftStoragePort,
} from "./examWorkspaceGuestDraftStorage";
import {
  createInMemoryGuestHandoffRejectionStorage,
  type GuestHandoffRejectionStoragePort,
} from "./examWorkspaceGuestHandoffRejection";
import {
  createInMemoryGuestHandoffLock,
  type GuestHandoffLockPort,
} from "./examWorkspaceGuestHandoffLock";
import type { GuestHandoffOwner, RunGuestHandoffOptions } from "./useExamWorkspaceGuestHandoff";
import {
  newGuestDraft,
  storeGuestUndoStep,
  type ExamWorkspaceGuestDraft,
  type ExamWorkspaceGuestDraftIdSource,
} from "./examWorkspaceGuestDraft";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { ApiError } from "../../../api/client";
import { vi, type Mock } from "vitest";
import type { GuestHandoffTeacher } from "./useExamWorkspaceGuestHandoff";

export const GUEST_HANDOFF_SPEC_NOW = "2026-10-18T10:00:00.000Z";

export function createGuestHandoffIds(start = 0): ExamWorkspaceGuestDraftIdSource {
  let counter = start;
  return {
    now: () => GUEST_HANDOFF_SPEC_NOW,
    uuid: () => {
      counter += 1;
      return `10000000-0000-4000-8000-${String(counter).padStart(12, "0")}`;
    },
  };
}

function assetEntry(assetId: string) {
  return {
    asset_id: assetId,
    byte_length: 1,
    height: 1,
    media_type: "image/png" as const,
    sha256: "a".repeat(64),
    width: 1,
  };
}

export function pictureDocument() {
  return {
    ...buildParentDocument(),
    assets: [assetEntry("asset_a"), assetEntry("asset_b")],
  };
}

export function editedGuestDraft(): { draft: ExamWorkspaceGuestDraft } {
  const ids = createGuestHandoffIds();
  const draft = newGuestDraft(pictureDocument(), ids, []);
  const outcome = storeGuestUndoStep(
    draft,
    { afterStepId: null, document: { ...pictureDocument(), title: "Redigerad" }, expectedCursor: draft.cursor },
    ids,
  );
  if (outcome.kind !== "ok") {
    throw new Error(`expected a stored step, got ${outcome.kind}`);
  }
  return { draft: outcome.draft };
}

export function guestHandoffApiError(status: number, code = "ERROR", details: unknown = null): ApiError {
  return new ApiError({ code, details, message: code, status });
}

export function guestHandoffTeacherMock(): {
  importExamWorkspaceGuestDraft: Mock<GuestHandoffTeacher["importExamWorkspaceGuestDraft"]>;
} {
  return {
    importExamWorkspaceGuestDraft: vi.fn<GuestHandoffTeacher["importExamWorkspaceGuestDraft"]>(),
  };
}

export type GuestHandoffHarness = {
  storage: ExamWorkspaceGuestDraftStoragePort;
  rejections: GuestHandoffRejectionStoragePort;
  teacher: { importExamWorkspaceGuestDraft: Mock<GuestHandoffTeacher["importExamWorkspaceGuestDraft"]> };
  draft: ExamWorkspaceGuestDraft;
  lock: GuestHandoffLockPort;
  owner: GuestHandoffOwner;
};

/** A live owner for specs that do not retire the session mid-flight. */
export function guestHandoffOwnerStub(): GuestHandoffOwner {
  return { isLive: () => true, session: Symbol("guest handoff test session") };
}

/** A fresh unaborted attempt: every `runGuestHandoff` caller names its signal. */
export function liveAttempt(): RunGuestHandoffOptions {
  return { signal: new AbortController().signal };
}

export async function seedGuestHandoffHarness(): Promise<GuestHandoffHarness> {
  const storage = createInMemoryExamWorkspaceGuestDraftStorage();
  const rejections = createInMemoryGuestHandoffRejectionStorage();
  const { draft } = editedGuestDraft();
  const seeded = await storage.replaceIf(null, {
    assets: { asset_a: new Blob(["a"]), asset_b: new Blob(["b"]) },
    draft,
  });
  if (!seeded) {
    throw new Error("expected the harness draft to seed");
  }
  return {
    draft,
    lock: createInMemoryGuestHandoffLock(),
    owner: guestHandoffOwnerStub(),
    rejections,
    storage,
    teacher: guestHandoffTeacherMock(),
  };
}

export function guestHandoffFailureToasts(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
}
