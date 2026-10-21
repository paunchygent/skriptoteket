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
 *     classroom planner database is not opened or changed. The draft and
 *     the edit lease are two object stores of that one database, so a
 *     whole-slot replacement decides on both in one transaction.
 */

import { openDB, type DBSchema, type IDBPDatabase } from "idb";

import {
  decideGuestEditLeaseClaim,
  decideGuestEditLeaseRenew,
  decideGuestEditLeaseTakeover,
  ownsGuestEditLease,
  type GuestEditLeaseRecord,
  type GuestEditLeaseStoragePort,
} from "./examWorkspaceGuestEditLease";
import type { InMemoryGuestEditLeaseStorage } from "./examWorkspaceGuestEditLeaseMemory";
import type { ExamWorkspaceGuestDraft } from "./examWorkspaceGuestDraft";
import type { GuestSlotAdmission } from "./examWorkspaceStore";

export const EXAM_WORKSPACE_GUEST_DRAFT_DB_NAME = "skriptoteket_exam_workspace_guest";
export const EXAM_WORKSPACE_GUEST_DRAFT_DB_VERSION = 2;
export const EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME = "drafts";
export const EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY = "current";
export const EXAM_WORKSPACE_GUEST_EDIT_LEASE_STORE_NAME = "edit_lease";
export const EXAM_WORKSPACE_GUEST_EDIT_LEASE_RECORD_KEY = "current";

export type StoredGuestDraft = {
  draft: ExamWorkspaceGuestDraft;
  /** Picture bytes by declared asset id; the draft itself holds no bytes. */
  assets: Record<string, Blob>;
};

/**
 * The outcome of one whole-slot replacement decision: written, refused
 * because another writer owns the slot or the writer was retired
 * (`conflict`), or refused because another tab holds a live edit lease.
 */
export type GuestSlotReplaceOutcome = "replaced" | "conflict" | "lease-held";

/**
 * The whole-slot replacement decision both adapters run inside one atomic
 * step, on the cursor and lease read in that step: a cursor that no longer
 * owns the slot is the ordinary conflict, a live lease of another tab
 * refuses next (a missing, own or expired lease passes, as the claim rule
 * decides), and the writer's own live authority is evaluated last,
 * immediately before the write it admits.
 */
export function decideGuestSlotReplacement(
  storedCursor: string | null,
  lease: GuestEditLeaseRecord | null,
  expectedCursor: string | null,
  admission: GuestSlotAdmission,
): GuestSlotReplaceOutcome {
  if (storedCursor !== expectedCursor) {
    return "conflict";
  }
  if (!decideGuestEditLeaseClaim(lease, admission.tabId, Date.now()).held) {
    return "lease-held";
  }
  return admission.isLive() ? "replaced" : "conflict";
}

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
   * Replace the whole slot with a new exam, which deletes the stored draft,
   * its history and its picture bytes. One atomic step reads the stored
   * cursor and the edit lease and runs `decideGuestSlotReplacement`: the
   * write happens only while `expectedCursor` owns the slot, no other tab
   * holds a live edit lease, and `admission.isLive()` is still true. A tab
   * that took the lease before this step therefore keeps the slot even when
   * the writing tab has not yet seen its loss.
   */
  replaceSlotIf(
    expectedCursor: string | null,
    next: StoredGuestDraft,
    admission: GuestSlotAdmission,
  ): Promise<GuestSlotReplaceOutcome>;
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
  edit_lease: {
    key: string;
    value: GuestEditLeaseRecord;
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
          if (!db.objectStoreNames.contains(EXAM_WORKSPACE_GUEST_EDIT_LEASE_STORE_NAME)) {
            db.createObjectStore(EXAM_WORKSPACE_GUEST_EDIT_LEASE_STORE_NAME);
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
    /**
     * One readwrite transaction over both object stores: read the lease and
     * the cursor, decide, then put. IndexedDB runs readwrite transactions
     * with overlapping scopes one after another, across tabs too, so no
     * lease claim and no draft write of another tab lands between this
     * decision and its put. `admission.isLive` runs synchronously inside the
     * decision; only IndexedDB calls are awaited inside the transaction.
     */
    async replaceSlotIf(expectedCursor, next, admission) {
      const tx = db.transaction(
        [EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME, EXAM_WORKSPACE_GUEST_EDIT_LEASE_STORE_NAME],
        "readwrite",
      );
      const drafts = tx.objectStore(EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME);
      const lease =
        (await tx
          .objectStore(EXAM_WORKSPACE_GUEST_EDIT_LEASE_STORE_NAME)
          .get(EXAM_WORKSPACE_GUEST_EDIT_LEASE_RECORD_KEY)) ?? null;
      const current = await drafts.get(EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY);
      const outcome = decideGuestSlotReplacement(
        current?.draft.cursor ?? null,
        lease,
        expectedCursor,
        admission,
      );
      if (outcome === "replaced") {
        await drafts.put(next, EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY);
      }
      await tx.done;
      return outcome;
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
 *
 * `lease` is the in-memory lease slot of the same browser: a whole-slot
 * replacement reads it synchronously inside its compare-and-write, as the
 * IndexedDB adapter reads the lease store inside its transaction. Without
 * it the lease slot reads as empty.
 */
export function createInMemoryExamWorkspaceGuestDraftStorage(options?: {
  lease?: Pick<InMemoryGuestEditLeaseStorage, "peek">;
}): ExamWorkspaceGuestDraftStoragePort {
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
    async replaceSlotIf(expectedCursor, next, admission) {
      // No await runs between the reads, the decision and the write.
      const lease = options?.lease?.peek() ?? null;
      const outcome = decideGuestSlotReplacement(
        stored?.draft.cursor ?? null,
        lease,
        expectedCursor,
        admission,
      );
      if (outcome === "replaced") {
        stored = { assets: { ...next.assets }, draft: structuredClone(next.draft) };
      }
      return outcome;
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
 * injected port alike, receives a plain snapshot on `replaceIf` and
 * `replaceSlotIf`, so a stored
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
    async replaceSlotIf(expectedCursor, next, admission) {
      return await (await port()).replaceSlotIf(
        expectedCursor,
        snapshotStoredGuestDraft(next),
        admission,
      );
    },
    async clearIf(expectedCursor) {
      return await (await port()).clearIf(expectedCursor);
    },
  };
}

/**
 * The guest edit lease in the same IndexedDB database as the draft: one
 * plain-JSON record beside it, in its own object store. The lease record and
 * the draft stay separate stores so a lease renewal never rewrites the draft
 * and a draft write never touches the lease. Importing this module never
 * touches a database: the adapter opens lazily on first use.
 */
export function createIndexedDbGuestEditLeaseStorage(): GuestEditLeaseStoragePort {
  return {
    async load() {
      const db = await getDb();
      return (
        (await db.get(
          EXAM_WORKSPACE_GUEST_EDIT_LEASE_STORE_NAME,
          EXAM_WORKSPACE_GUEST_EDIT_LEASE_RECORD_KEY,
        )) ?? null
      );
    },
    /**
     * One readwrite transaction: read the stored lease, run the claim
     * decision, then write only when this tab takes the slot. IndexedDB
     * serializes readwrite transactions on one store across tabs, so the
     * decision is atomic across tabs. Only IndexedDB calls are awaited
     * inside the transaction; anything else would auto-close it.
     */
    async claim(tabId, at) {
      const db = await getDb();
      const tx = db.transaction(EXAM_WORKSPACE_GUEST_EDIT_LEASE_STORE_NAME, "readwrite");
      const current =
        (await tx.store.get(EXAM_WORKSPACE_GUEST_EDIT_LEASE_RECORD_KEY)) ?? null;
      const decided = decideGuestEditLeaseClaim(current, tabId, at);
      if (decided.held) {
        await tx.store.put({ ...decided.record }, EXAM_WORKSPACE_GUEST_EDIT_LEASE_RECORD_KEY);
      }
      await tx.done;
      return decided;
    },
    /**
     * One readwrite transaction: renew only while this tab holds the slot
     * and nobody else asked to take over, so a stale renewal never
     * overwrites a new owner.
     */
    async renew(tabId, at) {
      const db = await getDb();
      const tx = db.transaction(EXAM_WORKSPACE_GUEST_EDIT_LEASE_STORE_NAME, "readwrite");
      const current =
        (await tx.store.get(EXAM_WORKSPACE_GUEST_EDIT_LEASE_RECORD_KEY)) ?? null;
      const decided = decideGuestEditLeaseRenew(current, tabId, at);
      if (decided.held && decided.record !== null) {
        await tx.store.put({ ...decided.record }, EXAM_WORKSPACE_GUEST_EDIT_LEASE_RECORD_KEY);
      }
      await tx.done;
      return decided;
    },
    /**
     * One readwrite transaction: free the slot only while this tab holds
     * it, so a stale release never clears a new owner.
     */
    async release(tabId) {
      const db = await getDb();
      const tx = db.transaction(EXAM_WORKSPACE_GUEST_EDIT_LEASE_STORE_NAME, "readwrite");
      const current =
        (await tx.store.get(EXAM_WORKSPACE_GUEST_EDIT_LEASE_RECORD_KEY)) ?? null;
      if (!ownsGuestEditLease(current, tabId)) {
        await tx.done;
        return false;
      }
      await tx.store.delete(EXAM_WORKSPACE_GUEST_EDIT_LEASE_RECORD_KEY);
      await tx.done;
      return true;
    },
    /**
     * One readwrite transaction: take a free or expired slot at once, or
     * record this tab's ask on the live record.
     */
    async requestTakeover(tabId, at) {
      const db = await getDb();
      const tx = db.transaction(EXAM_WORKSPACE_GUEST_EDIT_LEASE_STORE_NAME, "readwrite");
      const current =
        (await tx.store.get(EXAM_WORKSPACE_GUEST_EDIT_LEASE_RECORD_KEY)) ?? null;
      const decided = decideGuestEditLeaseTakeover(current, tabId, at);
      if (decided.outcome !== "own") {
        await tx.store.put({ ...decided.record }, EXAM_WORKSPACE_GUEST_EDIT_LEASE_RECORD_KEY);
      }
      await tx.done;
      return decided;
    },
  };
}
