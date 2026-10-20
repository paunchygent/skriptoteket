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
 *     serial lock to model two tabs. There is no unlocked fallback for POSTs:
 *     when `navigator.locks` is missing or the request is refused, the
 *     adapter throws the typed `GuestHandoffLockUnavailableError` refusal and
 *     the caller reads the draft without the lock instead of posting
 *     unlocked.
 */

export const EXAM_WORKSPACE_GUEST_HANDOFF_LOCK_NAME =
  "skriptoteket.exam-workspace.guest-handoff";

export class GuestHandoffLockUnavailableError extends Error {
  public constructor(message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = "GuestHandoffLockUnavailableError";
  }
}

export type GuestHandoffLockPort = {
  run<T>(work: () => Promise<T>, signal: AbortSignal): Promise<T>;
};

/** One named exclusive Web Lock shared by every tab of this browser. */
export function createWebGuestHandoffLock(): GuestHandoffLockPort {
  return {
    async run<T>(work: () => Promise<T>, signal: AbortSignal): Promise<T> {
      const locks = typeof navigator === "undefined" ? undefined : navigator.locks;
      if (!locks || typeof locks.request !== "function") {
        throw new GuestHandoffLockUnavailableError(
          "Web Locks are unavailable: the guest handoff stays unposted.",
        );
      }
      let started = false;
      try {
        return await locks.request(
          EXAM_WORKSPACE_GUEST_HANDOFF_LOCK_NAME,
          { mode: "exclusive", signal },
          () => {
            started = true;
            return work();
          },
        );
      } catch (error: unknown) {
        if (started) {
          throw error;
        }
        if (signal.aborted) {
          throw error;
        }
        throw new GuestHandoffLockUnavailableError(
          "Web Locks refused the guest handoff lock.",
          { cause: error },
        );
      }
    },
  };
}

/** A serial promise chain for specs; one instance models two tabs. */
export function createInMemoryGuestHandoffLock(): GuestHandoffLockPort {
  let tail: Promise<unknown> = Promise.resolve();
  return {
    run<T>(work: () => Promise<T>, signal: AbortSignal): Promise<T> {
      const next = tail.then(async () => {
        if (signal.aborted) {
          throw new DOMException("Aborted.", "AbortError");
        }
        return await work();
      });
      tail = next.catch(() => undefined);
      return next;
    },
  };
}
