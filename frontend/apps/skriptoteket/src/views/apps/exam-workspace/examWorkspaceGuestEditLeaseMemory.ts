/**
 * Guest exam workspace edit lease, in memory.
 *
 * Domain purpose:
 *   The lease slot of one browser held in memory, for the specs and every
 *   test double that runs two tabs over one slot. It runs the same atomic
 *   decisions as the IndexedDB adapter.
 *
 * Relationships:
 *   - The decisions come from `examWorkspaceGuestEditLease.ts`; the
 *     IndexedDB adapter lives in `examWorkspaceGuestDraftStorage.ts`.
 *   - `peek` feeds the in-memory draft slot of
 *     `examWorkspaceGuestDraftStorage.ts`, so a whole-slot replacement
 *     decides on the current lease without an await.
 */

import {
  decideGuestEditLeaseClaim,
  decideGuestEditLeaseRenew,
  decideGuestEditLeaseTakeover,
  ownsGuestEditLease,
  type GuestEditLeaseRecord,
  type GuestEditLeaseStoragePort,
} from "./examWorkspaceGuestEditLease";

/** The in-memory lease port, plus the synchronous read the in-memory draft slot decides on. */
export type InMemoryGuestEditLeaseStorage = GuestEditLeaseStoragePort & {
  /**
   * The current record, read synchronously. The in-memory draft slot reads
   * it inside its own synchronous compare-and-write, as the IndexedDB slot
   * write reads the lease store inside its transaction.
   */
  peek(): GuestEditLeaseRecord | null;
};

/** One in-memory lease slot, shared by every controller that receives it, like two tabs. */
export function createInMemoryGuestEditLeaseStorage(): InMemoryGuestEditLeaseStorage {
  let record: GuestEditLeaseRecord | null = null;
  return {
    peek() {
      return record === null ? null : { ...record };
    },
    async load() {
      return record === null ? null : { ...record };
    },
    async claim(tabId, at) {
      // No await runs between the read and the write below, so concurrent
      // claims against this slot decide one after another, like IndexedDB
      // serializes one readwrite transaction per tab.
      const decided = decideGuestEditLeaseClaim(record, tabId, at);
      if (decided.held) {
        record = { ...decided.record };
      }
      return { held: decided.held, record: { ...decided.record } };
    },
    async renew(tabId, at) {
      const decided = decideGuestEditLeaseRenew(record, tabId, at);
      if (decided.held && decided.record !== null) {
        record = { ...decided.record };
      }
      return {
        held: decided.held,
        record: decided.record === null ? null : { ...decided.record },
      };
    },
    async release(tabId) {
      if (!ownsGuestEditLease(record, tabId)) {
        return false;
      }
      record = null;
      return true;
    },
    async requestTakeover(tabId, at) {
      const decided = decideGuestEditLeaseTakeover(record, tabId, at);
      if (decided.outcome !== "own") {
        record = { ...decided.record };
      }
      return { outcome: decided.outcome, record: { ...decided.record } };
    },
  };
}
