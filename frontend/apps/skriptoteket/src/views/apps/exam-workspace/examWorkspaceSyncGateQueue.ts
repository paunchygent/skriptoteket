/**
 * Exam workspace sync gate write queue (TASK-SKRIPT-40-04-14, F1).
 *
 * Domain purpose:
 *   The single ordered queue every save goes through, one generation at a
 *   time. Outside `editing` an entry resolves `refused` at once, without
 *   touching the tail. Otherwise the entry captures the current token and
 *   runs only when its turn comes while the token is still current and the
 *   phase is still `editing`; each generation has its own tail, so a current
 *   write never waits behind a retired one. A rejection from `run` reaches
 *   this entry's caller but never breaks later entries.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceSyncGate`, which discards the tail on every
 *     generation retire and reads the live phase through `isEditing`.
 */

import type { FenceToken, SyncFence } from "./examWorkspaceSyncFence";

export type ExamWorkspaceSyncGateQueueDeps = {
  /** The gate's fence: every queued write captures and rechecks its token. */
  fence: SyncFence;
  /** True once the gate is torn down; every entry resolves `refused`. */
  isDisposed: () => boolean;
  /** True while the gate phase admits writes. */
  isEditing: () => boolean;
};

export function createSyncGateQueue(deps: ExamWorkspaceSyncGateQueueDeps) {
  /** The current generation's tail, so writes run one at a time in order. */
  let tail: Promise<void> = Promise.resolve();

  /** Drop the retired generation's tail: the next write starts fresh. */
  function discard(): void {
    tail = Promise.resolve();
  }

  function enqueueWrite<T>(run: (token: FenceToken) => Promise<T>, refused: T): Promise<T> {
    if (deps.isDisposed() || !deps.isEditing()) {
      return Promise.resolve(refused);
    }
    const token = deps.fence.begin();
    const queue = tail;
    const task = queue.then(() => {
      if (deps.isDisposed() || !deps.fence.isCurrent(token) || !deps.isEditing()) {
        return refused;
      }
      return run(token);
    });
    tail = task.then(
      () => undefined,
      () => undefined,
    );
    return task;
  }

  return { discard, enqueueWrite };
}
