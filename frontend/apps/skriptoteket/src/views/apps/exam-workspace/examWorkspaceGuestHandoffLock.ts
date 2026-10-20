/**
 * Exam workspace guest handoff cross-tab lock.
 *
 * Domain purpose:
 *   Arbitrate handoff attempts across tabs so two signed-in hosts never POST
 *   the same rejected cursor before either reply arrives. Every handoff
 *   attempt runs inside this lock and re-reads the draft and the rejection
 *   record after admission, so a second automatic attempt observes the first
 *   tab's permanent outcome instead of posting again.
 *
 * Relationships:
 *   - Held by `runGuestHandoff` only; the edit lease owns document editing
 *     and stays separate. The server cannot make a failed same-cursor create
 *     idempotent: schema or asset validation can refuse before claiming, and
 *     a refused create rolls its claim back, so the client must serialize
 *     attempts instead of relying on the idempotency key.
 *   - Production tabs share one named Web Lock; specs share one in-memory
 *     serial lock to model two tabs. No fallback exists when
 *     `navigator.locks` is missing: a throw there surfaces.
 */

export const EXAM_WORKSPACE_GUEST_HANDOFF_LOCK_NAME =
  "skriptoteket.exam-workspace.guest-handoff";

export type GuestHandoffLockPort = {
  run<T>(work: () => Promise<T>): Promise<T>;
};

/** One named exclusive Web Lock shared by every tab of this browser. */
export function createWebGuestHandoffLock(): GuestHandoffLockPort {
  return {
    async run<T>(work: () => Promise<T>): Promise<T> {
      return await navigator.locks.request(
        EXAM_WORKSPACE_GUEST_HANDOFF_LOCK_NAME,
        { mode: "exclusive" },
        () => work(),
      );
    },
  };
}

/** A serial promise chain for specs; one instance models two tabs. */
export function createInMemoryGuestHandoffLock(): GuestHandoffLockPort {
  let tail: Promise<unknown> = Promise.resolve();
  return {
    run<T>(work: () => Promise<T>): Promise<T> {
      const next = tail.then(work, work);
      tail = next.catch(() => undefined);
      return next;
    },
  };
}
