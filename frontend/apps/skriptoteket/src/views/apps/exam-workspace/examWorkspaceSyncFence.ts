/**
 * Exam workspace sync fence (TASK-SKRIPT-40-04-14, F1).
 *
 * Domain purpose:
 *   One generation owner for the sync gate's async effects: every result
 *   carries the generation it started in, and anything older is dropped
 *   before it can touch state. `begin` hands out a branded token for the
 *   current generation; `settle` resolves each outstanding wait as `stale`
 *   the moment a bump retires its generation, even while the transport
 *   promise never settles. A later settlement of a stale token still yields
 *   `stale`, and a stale rejection is swallowed so it never surfaces as an
 *   unhandled rejection.
 */

const fenceBrand: unique symbol = Symbol("examWorkspaceSyncFence");

/** The generation an async result started in; only the fence mints it. */
export type FenceToken = {
  readonly [fenceBrand]: number;
};

/** A settled fenced wait: a current value, a current failure, or a retired generation. */
export type Settled<T> = { kind: "current"; value: T } | { kind: "failed"; error: unknown } | { kind: "stale" };

export type SyncFence = {
  /** A token for the current generation. */
  begin: () => FenceToken;
  /** Resolve `promise`, or `stale` when a bump retires the token first. */
  settle: <T>(token: FenceToken, promise: Promise<T>) => Promise<Settled<T>>;
  /** True while the token's generation is still current. */
  isCurrent: (token: FenceToken) => boolean;
  /** Retire the current generation: every outstanding settle resolves `stale` at once. */
  retire: () => void;
};

export function createSyncFence(): SyncFence {
  let generation = 0;
  const waiting = new Set<() => void>();

  function begin(): FenceToken {
    return { [fenceBrand]: generation };
  }

  function isCurrent(token: FenceToken): boolean {
    return token[fenceBrand] === generation;
  }

  function retire(): void {
    generation += 1;
    const stale = [...waiting];
    waiting.clear();
    for (const resolveStale of stale) {
      resolveStale();
    }
  }

  function settle<T>(token: FenceToken, promise: Promise<T>): Promise<Settled<T>> {
    if (!isCurrent(token)) {
      // Already retired: swallow the outcome so a late rejection stays silent.
      promise.then(undefined, () => undefined);
      return Promise.resolve({ kind: "stale" });
    }
    return new Promise<Settled<T>>((resolve) => {
      const resolveStale = (): void => {
        resolve({ kind: "stale" });
      };
      waiting.add(resolveStale);
      promise.then(
        (value) => {
          waiting.delete(resolveStale);
          resolve(isCurrent(token) ? { kind: "current", value } : { kind: "stale" });
        },
        (error: unknown) => {
          waiting.delete(resolveStale);
          resolve(isCurrent(token) ? { kind: "failed", error } : { kind: "stale" });
        },
      );
    });
  }

  return { begin, isCurrent, retire, settle };
}
