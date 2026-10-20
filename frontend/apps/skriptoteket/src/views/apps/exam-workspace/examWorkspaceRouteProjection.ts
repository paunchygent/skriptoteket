/**
 * Exam workspace route projection (TASK-SKRIPT-40-04-14, R9-1).
 *
 * Domain purpose:
 *   The router adapter the replacement coordinator publishes through: it
 *   reads the `?document=<lineage_id>` address and writes it, and it watches
 *   address changes for the address adapter. A repeated projection is a
 *   no-op, and a projection acknowledgement carries no application-state
 *   authority: the coordinator's intent slot already owns the decision.
 *
 * Relationships:
 *   - Created once per editing session and shared by the address adapter
 *     (which parses requests) and the coordinator (which alone publishes).
 */

import { onScopeDispose, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

export type ExamWorkspaceRouteProjection = {
  /** The lineage the address names now, if any. */
  current: () => string | null;
  /** Publish the open document into the address; a repeated value is a no-op. */
  project: (lineageId: string | null) => void;
  /** Call back with the named lineage on every address change. */
  watchAddress: (onAddress: (lineageId: string | null) => void) => void;
  /** Resolve once no router navigation is in flight; a same-turn push that
   * started a navigation always lands its intent before this resolves. */
  waitForIdle: () => Promise<void>;
};

export function createRouteProjection(): ExamWorkspaceRouteProjection {
  const route = useRoute();
  const router = useRouter();

  function current(): string | null {
    const value = route.query.document;
    return typeof value === "string" && value.length > 0 ? value : null;
  }

  /** The coordinator's own published values with their echo still in flight. */
  const pendingEchoes = new Set<string>();

  function project(lineageId: string | null): void {
    if (current() === lineageId) {
      return;
    }
    if (lineageId !== null) {
      // The coordinator alone publishes: this projection's own echo is not a
      // new intent. A later genuine navigation to the same value submits
      // again once a newer submit clears the consumed set.
      pendingEchoes.add(lineageId);
    }
    const { document: _dropped, ...rest } = route.query;
    const query = lineageId === null ? rest : { ...rest, document: lineageId };
    // The acknowledgement has no application-state authority: the intent slot
    // already owns the decision, so a rejected projection stays silent.
    // A cancelled or failed projection never echoes, so its entry goes too.
    const forget = () => {
      if (lineageId !== null) {
        pendingEchoes.delete(lineageId);
      }
    };
    void router.replace({ query }).then((failure) => {
      if (failure !== undefined) {
        forget();
      }
    }, forget);
  }

  function watchAddress(onAddress: (lineageId: string | null) => void): void {
    // Synchronous: a back-to-back navigation must record its intent before a
    // settling barrier selects the winner, so the latest request always wins.
    watch(
      () => current(),
      (lineageId) => {
        if (lineageId !== null && pendingEchoes.has(lineageId)) {
          pendingEchoes.delete(lineageId);
          return;
        }
        pendingEchoes.clear();
        onAddress(lineageId);
      },
      { flush: "sync" },
    );
  }

  // A same-turn push starts its navigation long before the route change
  // reaches the watcher above. The barrier waits for that navigation (and its
  // synchronous intent submit) before it settles, so the winner it selects is
  // the latest request rather than the latest submit that beat the race.
  let idle: Promise<void> = Promise.resolve();
  let releaseIdle: (() => void) | null = null;
  const removeBeforeGuard = router.beforeEach(() => {
    if (releaseIdle === null) {
      idle = new Promise<void>((resolve) => {
        releaseIdle = resolve;
      });
    }
  });
  const removeAfterGuard = router.afterEach(() => {
    releaseIdle?.();
    releaseIdle = null;
    idle = Promise.resolve();
  });
  onScopeDispose(() => {
    removeBeforeGuard();
    removeAfterGuard();
  });

  async function waitForIdle(): Promise<void> {
    for (;;) {
      const pending = idle;
      await pending;
      if (idle === pending) {
        return;
      }
    }
  }

  return { current, project, waitForIdle, watchAddress };
}
