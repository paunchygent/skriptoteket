/**
 * Exam workspace history departure lifecycle.
 *
 * Domain purpose:
 *   A sign-in exit departs through `depart(leave)`, which runs the settle flush inside the
 *   same `replaceCopy` editing lock and only then calls `leave`; when `leave`
 *   succeeds the lock stays held while the navigation runs, so no edit typed
 *   or pasted after the redirect starts is stored past it and lost; a
 *   departure that meets a replacing read resolves false and keeps the
 *   working copy mounted.
 *
 *   No `beforeunload` handler is mounted on the exam-workspace routes:
 *   `composables/editor/useUnsavedChangesGuards.ts` is the SPA's only one
 *   and the exam workspace does not use it, so no cancelled navigation can
 *   strand the held departing lock. The lock is released when the page comes
 *   back (`pageshow`, for example from the back-forward cache) or when the
 *   history's scope is disposed on unmount.
 *
 * Relationships:
 *   - Built by `useExamWorkspaceHistory`, which stays the only history
 *     authority; the history passes explicit deps (`flush`, `pending`,
 *     `isNavigating`, `isReplacing`, `replaceCopy`, `isDisposed`) and
 *     re-exports `depart`, so no caller changes.
 *   - The history's `onScopeDispose` marks disposed, clears the typing timer
 *     and then calls this module's `dispose()`, which releases a held
 *     departure lock; that order matches the previous inline disposal.
 */

export type ExamWorkspaceHistoryDepartureDeps = {
  /** Store the pending edit now; `depart` always settles before leaving. */
  flush: (settle?: boolean) => Promise<boolean>;
  /** True while the working copy differs from the standing step. */
  pending: () => boolean;
  /** True while an undo or redo holds the replacing lock. */
  isNavigating: () => boolean;
  /** Another undo, redo or server command is replacing the copy; departure waits by refusing. */
  isReplacing: () => boolean;
  /** Run a read that replaces the copy: locks editing and keeps arrivals that land meanwhile. */
  replaceCopy: <T>(run: () => Promise<T>) => Promise<T>;
  /** True once the history's scope is disposed: a pending departure must not leave. */
  isDisposed: () => boolean;
};

export function useExamWorkspaceHistoryDeparture(deps: ExamWorkspaceHistoryDepartureDeps) {
  /** Release the held departing lock; set only while a departure navigation runs. */
  let releaseDeparted: (() => void) | null = null;

  /**
   * Depart through `leave` under the held editing lock: refuse while another
   * undo, redo or server command holds the copy, otherwise run the settle
   * flush inside the `replaceCopy` editing lock undo uses, so no edit typed
   * while the departure write runs is lost past it, and only then call
   * `leave`. When `leave` returns false or throws, the lock is released and
   * departure resolves false. When `leave` succeeds, departure resolves true
   * but the lock stays held while the navigation runs, so an edit typed or
   * pasted after the redirect starts is refused instead of being accepted and
   * abandoned on unload. The held lock is released when the page comes back
   * (`pageshow`) or when the history's scope is disposed on unmount; no
   * `beforeunload` handler can cancel the navigation on these routes. A
   * departure whose scope is disposed before the flush finishes never calls
   * `leave`; one disposed while `leave` runs releases without installing the
   * `pageshow` hold and resolves false, so navigation that already started is
   * not overridden and the lock does not outlive the scope.
   */
  async function depart(leave: () => boolean | Promise<boolean>): Promise<boolean> {
    if (deps.isDisposed() || deps.isReplacing() || deps.isNavigating()) {
      return false;
    }
    let releaseDeparting!: () => void;
    const departingHeld = new Promise<void>((resolve) => {
      releaseDeparting = resolve;
    });
    let resolveDeparted!: (departed: boolean) => void;
    const departed = new Promise<boolean>((resolve) => {
      resolveDeparted = resolve;
    });
    const run = deps.replaceCopy(async (): Promise<void> => {
      const settled = await deps.flush(true);
      if (deps.isDisposed()) {
        resolveDeparted(false);
        return;
      }
      if (!(settled && !deps.pending())) {
        resolveDeparted(false);
        return;
      }
      let left: boolean;
      try {
        left = await leave();
      } catch {
        resolveDeparted(false);
        return;
      }
      if (deps.isDisposed()) {
        resolveDeparted(false);
        return;
      }
      if (!left) {
        resolveDeparted(false);
        return;
      }
      const onPageShow = (): void => {
        releaseDeparting();
      };
      window.addEventListener("pageshow", onPageShow);
      releaseDeparted = () => {
        window.removeEventListener("pageshow", onPageShow);
        releaseDeparted = null;
        releaseDeparting();
      };
      resolveDeparted(true);
      await departingHeld;
      window.removeEventListener("pageshow", onPageShow);
      releaseDeparted = null;
    });
    void run.then(
      () => undefined,
      () => resolveDeparted(false),
    );
    return departed;
  }

  /**
   * Release a held departure lock without installing anything new; the
   * history calls this from its own `onScopeDispose` after marking disposed
   * and clearing the typing timer, preserving the previous disposal order.
   */
  function dispose(): void {
    releaseDeparted?.();
  }

  return { depart, dispose };
}
