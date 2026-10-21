/**
 * Guest handoff controller spec support (TASK-SKRIPT-41-02-06, U13b).
 *
 * Domain purpose:
 *   Shared setup for the guest handoff controller specs: one controller per
 *   effect scope, toast spies, the zip-download byte helpers, and the older
 *   format seating that makes a seeded draft unreadable to the browser. The
 *   handoff, download, removal and unreadable specs build on this so each
 *   file stays under its line budget.
 *
 * Relationships:
 *   - Imported by `useExamWorkspaceGuestHandoffController.handoff.spec.ts`,
 *     `useExamWorkspaceGuestHandoffController.download.spec.ts`,
 *     `useExamWorkspaceGuestHandoffController.removal.spec.ts` and
 *     `useExamWorkspaceGuestHandoffController.unreadable.spec.ts`; the
 *     seeded harness itself lives in `useExamWorkspaceGuestHandoff.specSupport`.
 */

import { effectScope } from "vue";
import { expect, vi } from "vitest";

import { useToastStore } from "../../../stores/toast";
import type {
  ExamWorkspaceGuestDraftStoragePort,
  StoredGuestDraft,
} from "./examWorkspaceGuestDraftStorage";
import type { ExamWorkspaceGuestDraft } from "./examWorkspaceGuestDraft";
import type {
  GuestHandoffDeps,
  GuestHandoffTeacher,
} from "./useExamWorkspaceGuestHandoff";
import { useExamWorkspaceGuestHandoffController } from "./useExamWorkspaceGuestHandoffController";

export type ImportResult = Awaited<ReturnType<GuestHandoffTeacher["importExamWorkspaceGuestDraft"]>>;

export function successResult(draft: ExamWorkspaceGuestDraft, lineageId = "lineage-new"): ImportResult {
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

export function toastSpies() {
  const store = useToastStore();
  return {
    failure: vi.spyOn(store, "failure"),
    success: vi.spyOn(store, "success"),
    warning: vi.spyOn(store, "warning"),
  };
}

export function toastMessages(spy: { mock: { calls: Array<[string, ...unknown[]]> } }): string[] {
  return spy.mock.calls.map((call) => call[0]);
}

export function startController(deps: Omit<GuestHandoffDeps, "owner">, download?: (blob: Blob, filename: string) => void) {
  const scope = effectScope();
  const controller = scope.run(() =>
    useExamWorkspaceGuestHandoffController(deps, download === undefined ? undefined : { download }),
  );
  if (controller === undefined) {
    throw new Error("expected the scope to produce a controller");
  }
  return { controller, scope };
}

/**
 * Read a download Blob as raw bytes through FileReader: jsdom's Blob has no
 * `arrayBuffer` the specs can rely on.
 */
export async function blobBytes(blob: Blob): Promise<Uint8Array> {
  return await new Promise<Uint8Array>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (reader.result instanceof ArrayBuffer) {
        resolve(new Uint8Array(reader.result));
        return;
      }
      reject(new Error("The FileReader did not return bytes."));
    };
    reader.onerror = () => reject(reader.error ?? new Error("Could not read the blob bytes."));
    reader.readAsArrayBuffer(blob);
  });
}

/**
 * jsdom's Blob has no `arrayBuffer`; equip the stored picture blobs with the
 * production Web API through FileReader, following the per-blob
 * `Object.defineProperty(file, "arrayBuffer", ...)` pattern in
 * `client.csrfRecovery.spec.ts`. The in-memory storage keeps picture bytes
 * by reference, so patching the loaded blobs patches the stored ones.
 */
export async function equipStoredPictureBytes(
  storage: ExamWorkspaceGuestDraftStoragePort,
): Promise<void> {
  const stored = await storage.load();
  if (stored === null) {
    throw new Error("expected a stored draft to equip");
  }
  for (const blob of Object.values(stored.assets)) {
    Object.defineProperty(blob, "arrayBuffer", {
      configurable: true,
      value: async (): Promise<ArrayBuffer> => {
        const bytes = await blobBytes(blob);
        const copy = new Uint8Array(bytes.length);
        copy.set(bytes);
        return copy.buffer;
      },
    });
  }
}

const OLD_TOKEN = '"native_exam_document_v11"';
const PREV_TOKEN = '"native_exam_document_v10"';

/**
 * Replace every current format token in the stored draft with the previous
 * version, so the browser itself reports the draft as unreadable while the
 * picture bytes stay by reference: the draft is JSON data, the assets are not.
 */
export async function seatOlderFormat(storage: {
  load(): Promise<StoredGuestDraft | null>;
  replaceIf(expectedCursor: string | null, next: StoredGuestDraft): Promise<boolean>;
}): Promise<void> {
  const stored = await storage.load();
  if (stored === null) {
    throw new Error("expected a seeded draft to downgrade");
  }
  const draft: ExamWorkspaceGuestDraft = JSON.parse(
    JSON.stringify(stored.draft).replaceAll(OLD_TOKEN, PREV_TOKEN),
  );
  // Picture bytes stay by reference: the draft is JSON data, the assets are not.
  const downgraded: StoredGuestDraft = { assets: stored.assets, draft };
  expect(await storage.replaceIf(stored.draft.cursor, downgraded)).toBe(true);
}
