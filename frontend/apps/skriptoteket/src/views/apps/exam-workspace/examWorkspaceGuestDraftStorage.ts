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
  save(stored: StoredGuestDraft): Promise<void>;
  clear(): Promise<void>;
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
    async save(stored) {
      await db.put(
        EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME,
        stored,
        EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY,
      );
    },
    async clear() {
      await db.delete(
        EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME,
        EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY,
      );
    },
  };
}

/** A single-slot in-memory store for specs and for a test double the factory accepts. */
export function createInMemoryExamWorkspaceGuestDraftStorage(): ExamWorkspaceGuestDraftStoragePort {
  let stored: StoredGuestDraft | null = null;
  return {
    async load() {
      return stored;
    },
    async save(next) {
      stored = next;
    },
    async clear() {
      stored = null;
    },
  };
}

/**
 * The guest storage: the injected port when a caller supplies one (specs and
 * embedders), otherwise the IndexedDB adapter opened lazily on first use so
 * importing this module never touches a database.
 */
export function createExamWorkspaceGuestDraftStorage(deps?: {
  port?: ExamWorkspaceGuestDraftStoragePort;
}): ExamWorkspaceGuestDraftStoragePort {
  if (deps?.port) {
    return deps.port;
  }
  let portPromise: Promise<ExamWorkspaceGuestDraftStoragePort> | null = null;
  const port = (): Promise<ExamWorkspaceGuestDraftStoragePort> => {
    portPromise ??= createIndexedDbPort();
    return portPromise;
  };
  return {
    async load() {
      return (await port()).load();
    },
    async save(stored) {
      await (await port()).save(stored);
    },
    async clear() {
      await (await port()).clear();
    },
  };
}
