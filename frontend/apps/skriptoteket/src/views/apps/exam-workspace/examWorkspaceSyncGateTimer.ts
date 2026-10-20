/**
 * Exam workspace sync-gate timer: the production reload-retry cadence.
 *
 * Domain purpose:
 *   One pending retry at a time: scheduling a run replaces the pending one
 *   and cancelling drops it. The gate retries a failed fresh load through
 *   this after 5 s; specs pass a manual double through the gate deps instead.
 */

/** Delay before a failed fresh load retries. */
export const SYNC_GATE_RELOAD_RETRY_MS = 5000;

/** The 5 s reload-retry timer; production passes `createSyncGateTimer`. */
export type ExamWorkspaceSyncGateTimer = {
  /** Run `run` after `delayMs`; replaces a pending retry. */
  schedule: (run: () => void, delayMs: number) => void;
  /** Drop a pending retry. */
  cancel: () => void;
};

/** The production retry timer: one pending retry at a time. */
export function createSyncGateTimer(): ExamWorkspaceSyncGateTimer {
  let handle: ReturnType<typeof setTimeout> | null = null;
  function cancel(): void {
    if (handle !== null) {
      clearTimeout(handle);
      handle = null;
    }
  }
  function schedule(run: () => void, delayMs: number): void {
    cancel();
    handle = setTimeout(() => {
      handle = null;
      run();
    }, delayMs);
  }
  return { cancel, schedule };
}
