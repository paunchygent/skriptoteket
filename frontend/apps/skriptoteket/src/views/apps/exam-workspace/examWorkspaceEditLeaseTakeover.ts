/**
 * Exam workspace edit lease takeover wait: the `Ta över` poll.
 *
 * Domain purpose:
 *   `Ta över` records the request and claims the lease once the holder has
 *   released or its lease has expired, then the caller reads the newest
 *   state. The wait claims at once when the lease is already free and polls
 *   the claim otherwise, staying read-only while waiting; a poll claim that
 *   fails stays waiting like a refused one. The wait is tied to the
 *   composable's acquisition identity (lineage plus acquisition epoch): the
 *   caller rechecks it after every await, a late success for a stale
 *   identity is released and changes nothing, and cancelling wakes a
 *   sleeping poll so the wait always settles.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceEditLease`, which keeps the read-only state,
 *     the acquisition epoch, the waiting flag and the heartbeat, and passes
 *     them in as hooks; this module owns only the request, the poll sleeps
 *     and their cancellation.
 *   - Runs one attempt per poll through the drivers in
 *     `examWorkspaceEditLeaseDrivers.ts`; the composable retries a refused
 *     claim at the heartbeat cadence outside the wait.
 */

import type { ExamWorkspaceEditLeaseDriver } from "./examWorkspaceEditLeaseDrivers";

export type EditLeaseTakeoverHooks = {
  /** The wait's identity (lineage, epoch, scope) is still current. */
  isCurrent: () => boolean;
  /** The tab still waits: the waiting flag is set and it holds nothing. */
  shouldWait: () => boolean;
  /** The fast path: the tab already holds the lease. Runs only if current. */
  noteOwn: () => void;
  /** A successful poll claim for a current identity. Guards itself again. */
  noteAcquired: (lineageId: string) => Promise<void>;
  /** Best-effort release of a late success for a stale identity. */
  release: (lineageId: string) => Promise<void>;
};

/** The cancellable `Ta över` poll sleeps and request for one lineage. */
export function createTakeoverPoll(pollMs: number) {
  let timer: ReturnType<typeof setTimeout> | null = null;
  let wake: (() => void) | null = null;

  /** Wake a sleeping poll so cancellation always settles the wait. */
  function cancel(): void {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
    const resume = wake;
    wake = null;
    if (resume !== null) {
      resume();
    }
  }

  function sleep(): Promise<void> {
    return new Promise<void>((resolve) => {
      wake = resolve;
      timer = setTimeout(() => {
        timer = null;
        wake = null;
        resolve();
      }, pollMs);
    });
  }

  /**
   * `Ta över`: record the request, claim at once when the lease is already
   * free, else poll the claim until the holder releases or its lease dies.
   * While waiting the tab stays read-only.
   */
  async function run(
    driver: ExamWorkspaceEditLeaseDriver,
    lineageId: string,
    hooks: EditLeaseTakeoverHooks,
  ): Promise<void> {
    let outcome: "claimed" | "requested" | "own";
    try {
      outcome = await driver.requestTakeover(lineageId);
    } catch {
      outcome = "requested";
    }
    if (!hooks.isCurrent()) {
      if (outcome === "claimed" || outcome === "own") {
        await hooks.release(lineageId);
      }
      return;
    }
    if (outcome === "own") {
      hooks.noteOwn();
      return;
    }
    if (outcome === "claimed") {
      await hooks.noteAcquired(lineageId);
      return;
    }
    while (hooks.shouldWait() && hooks.isCurrent()) {
      await sleep();
      if (!hooks.shouldWait() || !hooks.isCurrent()) {
        return;
      }
      let next: "held" | "readonly" | "failed";
      try {
        next = await driver.claim(lineageId);
      } catch {
        continue;
      }
      // A `failed` poll claim keeps waiting read-only; only the claim on
      // open stays editable on such a failure.
      if (!hooks.shouldWait() || !hooks.isCurrent()) {
        if (next === "held") {
          await hooks.release(lineageId);
        }
        return;
      }
      if (next === "held") {
        await hooks.noteAcquired(lineageId);
        return;
      }
    }
  }

  return { cancel, run };
}
