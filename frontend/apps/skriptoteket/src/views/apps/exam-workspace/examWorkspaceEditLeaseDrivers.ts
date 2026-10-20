/**
 * Exam workspace edit lease drivers: the server and guest claim transports.
 *
 * Domain purpose:
 *   Claim, renew, request takeover and release the edit lease against the
 *   server lease transport or the guest IndexedDB controller, so one tab at a
 *   time edits an exam (TASK-SKRIPT-40-04-14 behaviour item 7, decision D4).
 *   A live foreign lease opens read-only; any other claim failure is reported
 *   distinctly as `failed`, so only the claim on open stays editable while
 *   every retry claim stays read-only and retries at the next tick or poll.
 *   After a yield the composable restarts its heartbeat, so the first retry
 *   claim happens one full heartbeat after the release instead of racing the
 *   waiting tab's `Ta över` poll. The `pagehide` release goes out with
 *   `keepalive`, so the browser finishes the POST after the page is gone.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceEditLease`, which feeds the tab id into the
 *     history and structure writes, stores the pending edit on a takeover
 *     request and reloads the newest state on acquiring the lease. The
 *     composable retries a refused claim at the heartbeat cadence; the
 *     drivers only run one attempt each.
 *   - The server half runs on the edit-lease transport of
 *     `api/examWorkspace.ts`. The guest half drives
 *     `createGuestEditLeaseController` against the IndexedDB-bound lease slot.
 */

import { isApiError } from "../../../api/client";
import type { ExamWorkspaceEditLeaseResponse } from "../../../api/examWorkspace";
import {
  createGuestEditLeaseController,
  type GuestEditLeaseChannel,
  type GuestEditLeaseStoragePort,
} from "./examWorkspaceGuestEditLease";

export type ExamWorkspaceEditLeaseServer = {
  claim(lineageId: string, tabId: string): Promise<ExamWorkspaceEditLeaseResponse>;
  renew(lineageId: string, tabId: string): Promise<ExamWorkspaceEditLeaseResponse>;
  requestTakeover(lineageId: string, tabId: string): Promise<ExamWorkspaceEditLeaseResponse>;
  release(
    lineageId: string,
    tabId: string,
    options?: { keepalive?: boolean },
  ): Promise<ExamWorkspaceEditLeaseResponse>;
};

export type ExamWorkspaceEditLeaseDriver = {
  readonly tabId: string;
  claim(lineageId: string): Promise<"held" | "readonly" | "failed">;
  /**
   * Report what the renew saw without acting on it: `takeover` means another
   * tab asked to take over. The composable yields only after the fence admits
   * that answer as current, so an obsolete renew never flushes, releases or
   * changes holding before fencing.
   */
  renew(lineageId: string): Promise<"held" | "lost" | "takeover" | "failed">;
  requestTakeover(lineageId: string): Promise<"claimed" | "requested" | "own">;
  release(lineageId: string, options?: { keepalive?: boolean }): Promise<boolean>;
  dispose(): void;
};

export function createServerDriver(
  server: ExamWorkspaceEditLeaseServer,
  tabId: string,
): ExamWorkspaceEditLeaseDriver {
  const driver: ExamWorkspaceEditLeaseDriver = {
    tabId,
    async claim(lineageId) {
      try {
        await server.claim(lineageId, tabId);
        return "held";
      } catch (error) {
        // A live foreign lease opens read-only; any other failure is
        // reported distinctly, so only the claim on open stays editable
        // while every retry claim stays read-only.
        return isEditLeaseHeldError(error) ? "readonly" : "failed";
      }
    },
    async renew(lineageId) {
      try {
        const response = await server.renew(lineageId, tabId);
        // Report the ask without yielding: the composable runs the yield
        // after the fence admits this answer as current.
        if (response.takeover_requested) {
          return "takeover";
        }
        return "held";
      } catch (error) {
        if (isEditLeaseHeldError(error)) {
          return "lost";
        }
        // A transient failure keeps the hold only until the lease TTL dies;
        // the composable turns read-only once no success is within the TTL.
        return "failed";
      }
    },
    async requestTakeover(lineageId) {
      let response: ExamWorkspaceEditLeaseResponse;
      try {
        response = await server.requestTakeover(lineageId, tabId);
      } catch (error) {
        if (isEditLeaseHeldError(error)) {
          return "requested";
        }
        throw error;
      }
      if (response.holder_tab_id === tabId) {
        return "own";
      }
      // A `failed` retry claim stays waiting like a refused one; only the
      // claim on open stays editable.
      return (await driver.claim(lineageId)) === "held" ? "claimed" : "requested";
    },
    async release(lineageId, options) {
      try {
        // Only the `pagehide` release carries options, so the recorded calls
        // of every other release keep their two-argument shape.
        if (options?.keepalive === true) {
          await server.release(lineageId, tabId, options);
        } else {
          await server.release(lineageId, tabId);
        }
        return true;
      } catch {
        return false;
      }
    },
    dispose() {},
  };
  return driver;
}

export function createGuestDriver(
  tabId: string,
  guestStorage: GuestEditLeaseStoragePort,
  openChannel: () => GuestEditLeaseChannel,
  now: (() => number) | undefined,
  onTakeoverRequested: () => Promise<void> | void,
  /** Keeps the heartbeat phase; a refused or expired lease retries on it. */
  noteLostLease: () => void,
  /**
   * Runs after this tab answers a takeover: the composable's yield restart
   * (read-only plus a fresh heartbeat phase), so the first retry claim
   * happens one full heartbeat after the release.
   */
  onYielded: () => void,
): ExamWorkspaceEditLeaseDriver {
  const controller = createGuestEditLeaseController({
    now,
    onTakeoverRequested: async () => {
      await onTakeoverRequested();
      // The controller releases the lease immediately after this callback in
      // the same microtask drain, so no heartbeat tick can interleave: this
      // restart counts as after the release.
      onYielded();
    },
    openChannel,
    storage: guestStorage,
    tabId,
  });
  return {
    tabId,
    claim: () => controller.claim(),
    dispose: () => controller.dispose(),
    release: () => controller.release(),
    renew: async () => {
      // A pure query against the slot: the atomic renew decision renews the
      // record, but answering another tab's ask (flush, release, restart)
      // waits for the composable, which yields only after the fence admits
      // this answer as current. The controller's own heartbeat and channel
      // signal still answer live takeovers immediately, as before.
      const at = now === undefined ? Date.now() : now();
      let held: boolean;
      let asker: string | null;
      try {
        const decided = await guestStorage.renew(tabId, at);
        held = decided.held;
        asker =
          decided.record === null || decided.record.tabId !== tabId
            ? null
            : decided.record.takeoverRequestedBy;
      } catch {
        return "failed";
      }
      if (held) {
        return "held";
      }
      if (asker !== null && asker !== tabId) {
        return "takeover";
      }
      // The controller's own heartbeat calls the controller renew too, so a
      // lost lease turns read-only even when this tab's heartbeat is the one
      // that finds it. A transient storage failure is reported distinctly,
      // like the server driver's, so the composable keeps the hold only
      // until the lease TTL.
      noteLostLease();
      return "lost";
    },
    requestTakeover: () => controller.requestTakeover(),
  };
}

/** A 409 whose code names the edit lease, not a stale cursor. */
export function isEditLeaseHeldError(error: unknown): boolean {
  return isApiError(error) && error.status === 409 && error.code === "EDIT_LEASE_HELD";
}
