/**
 * Exam workspace guest draft browser storage.
 *
 * Domain purpose:
 *   Persist the one exam draft a guest edits while signed out, together with
 *   the tiny picture blobs its document declares. A guest's exam lives only
 *   in this browser: the draft and its assets never leave the device until
 *   the guest signs in and hands the draft over. There is one current draft,
 *   and clearing it is the whole guest reset.
 *
 * Relationships:
 *   - Port consumed by the guest workspace store; the IndexedDB adapter is the
 *     production implementation, the in-memory adapter the specs' controller.
 *   - The record shape comes from `examWorkspaceGuestDraft.ts`; picture bytes
 *     stay here, keyed by the document's asset ids, never in the draft record.
 *   - Owns the `skriptoteket_exam_workspace_guest` database only; the shared
 *     classroom planner database is not opened or changed.
 */

import { openDB, type DBSchema, type IDBPDatabase } from "idb";

import type { ExamWorkspaceGuestDraft } from "./examWorkspaceGuestDraft";

export const EXAM_WORKSPACE_GUEST_DRAFT_DB_NAME = "skriptoteket_exam_workspace_guest";
export const EXAM_WORKSPACE_GUEST_DRAFT_DB_VERSION = 1;
export const EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME = "drafts";
export const EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY = "current";

export type StoredGuestDraft = {
  draft: ExamWorkspaceGuestDraft;
  /** Picture bytes by declared asset id; the draft itself holds no bytes. */
  assets: Record<string, Blob>;
};

export type ExamWorkspaceGuestDraftStoragePort = {
  load(): Promise<StoredGuestDraft | null>;
  /**
   * Store `next` only when the stored record's draft cursor equals
   * `expectedCursor` (or when nothing is stored and `expectedCursor` is
   * null). Reports whether the write happened; a false return means another
   * tab or store instance committed first and the caller must surface the
   * established conflict outcome instead of claiming a write it lost.
   */
  replaceIf(expectedCursor: string | null, next: StoredGuestDraft): Promise<boolean>;
  /**
   * Delete the stored record only when its draft cursor equals
   * `expectedCursor`. Reports whether the delete happened; a false return
   * means a newer draft or newer edits own the slot now and must be kept.
   */
  clearIf(expectedCursor: string): Promise<boolean>;
};

type ExamWorkspaceGuestDraftDb = DBSchema & {
  drafts: {
    key: string;
    value: StoredGuestDraft;
  };
};

let dbPromise: Promise<IDBPDatabase<ExamWorkspaceGuestDraftDb>> | null = null;

function getDb(): Promise<IDBPDatabase<ExamWorkspaceGuestDraftDb>> {
  if (!dbPromise) {
    dbPromise = openDB<ExamWorkspaceGuestDraftDb>(
      EXAM_WORKSPACE_GUEST_DRAFT_DB_NAME,
      EXAM_WORKSPACE_GUEST_DRAFT_DB_VERSION,
      {
        upgrade(db) {
          if (!db.objectStoreNames.contains(EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME)) {
            db.createObjectStore(EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME);
          }
        },
      },
    );
  }
  return dbPromise;
}

async function createIndexedDbPort(): Promise<ExamWorkspaceGuestDraftStoragePort> {
  const db = await getDb();
  return {
    async load() {
      return (
        (await db.get(
          EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME,
          EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY,
        )) ?? null
      );
    },
    /**
     * One readwrite transaction: read the stored cursor, compare, then put.
     * IndexedDB serializes readwrite transactions on one store across tabs,
     * so the compare-and-write is atomic across tabs. Only IndexedDB calls
     * are awaited inside the transaction; anything else would auto-close it.
     */
    async replaceIf(expectedCursor, next) {
      const tx = db.transaction(EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME, "readwrite");
      const store = tx.store;
      const current = await store.get(EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY);
      if ((current?.draft.cursor ?? null) !== expectedCursor) {
        await tx.done;
        return false;
      }
      await store.put(next, EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY);
      await tx.done;
      return true;
    },
    async clearIf(expectedCursor) {
      const tx = db.transaction(EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME, "readwrite");
      const store = tx.store;
      const current = await store.get(EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY);
      if ((current?.draft.cursor ?? null) !== expectedCursor) {
        await tx.done;
        return false;
      }
      await store.delete(EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY);
      await tx.done;
      return true;
    },
  };
}

/**
 * A single-slot in-memory store for specs and for a test double the factory accepts.
 *
 * Like IndexedDB, it structured-clones the draft on write and on read, so a
 * spec that hands it a Vue reactive value fails the way the browser does.
 * Picture bytes stay by reference: jsdom Blobs do not survive a structured
 * clone, and the draft itself never holds bytes.
 */
export function createInMemoryExamWorkspaceGuestDraftStorage(): ExamWorkspaceGuestDraftStoragePort {
  let stored: StoredGuestDraft | null = null;
  return {
    async load() {
      if (stored === null) {
        return null;
      }
      return { assets: { ...stored.assets }, draft: structuredClone(stored.draft) };
    },
    async replaceIf(expectedCursor, next) {
      if ((stored?.draft.cursor ?? null) !== expectedCursor) {
        return false;
      }
      stored = { assets: { ...next.assets }, draft: structuredClone(next.draft) };
      return true;
    },
    async clearIf(expectedCursor) {
      if ((stored?.draft.cursor ?? null) !== expectedCursor) {
        return false;
      }
      stored = null;
      return true;
    },
  };
}

/**
 * Copy `next` into a plain serialisable snapshot: the draft as plain JSON
 * data, the asset Blobs unchanged by reference. The draft is JSON data from
 * the public routes, so the round-trip keeps it whole while dropping every
 * Vue reactive Proxy a call site may have handed over.
 */
function snapshotStoredGuestDraft(next: StoredGuestDraft): StoredGuestDraft {
  const draft: ExamWorkspaceGuestDraft = JSON.parse(JSON.stringify(next.draft));
  return { assets: { ...next.assets }, draft };
}

/**
 * The guest storage: every port it returns, the IndexedDB adapter and an
 * injected port alike, receives a plain snapshot on `replaceIf`, so a stored
 * draft is always serialisable. Importing this module never touches a
 * database: the IndexedDB adapter opens lazily on first use.
 */
export function createExamWorkspaceGuestDraftStorage(deps?: {
  port?: ExamWorkspaceGuestDraftStoragePort;
}): ExamWorkspaceGuestDraftStoragePort {
  let portPromise: Promise<ExamWorkspaceGuestDraftStoragePort> | null = null;
  const port = (): Promise<ExamWorkspaceGuestDraftStoragePort> => {
    if (deps?.port) {
      return Promise.resolve(deps.port);
    }
    portPromise ??= createIndexedDbPort();
    return portPromise;
  };
  return {
    async load() {
      return (await port()).load();
    },
    async replaceIf(expectedCursor, next) {
      return await (await port()).replaceIf(expectedCursor, snapshotStoredGuestDraft(next));
    },
    async clearIf(expectedCursor) {
      return await (await port()).clearIf(expectedCursor);
    },
  };
}
