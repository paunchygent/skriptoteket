/**
 * Exam workspace edit lease drivers: the server and guest claim transports.
 *
 * Domain purpose:
 *   Claim, renew, request takeover and release the edit lease against the
 *   server lease transport or the guest IndexedDB controller, so one tab at a
 *   time edits an exam (TASK-SKRIPT-40-04-14 behaviour item 7, decision D4).
 *   A live foreign lease opens read-only; any other claim failure stays
 *   editable, since the write guard is authoritative and refuses a tab
 *   without the lease. The `pagehide` release goes out with `keepalive`, so
 *   the browser finishes the POST after the page is gone.
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
  claim(lineageId: string): Promise<"held" | "readonly">;
  renew(lineageId: string): Promise<boolean>;
  requestTakeover(lineageId: string): Promise<"claimed" | "requested" | "own">;
  release(lineageId: string, options?: { keepalive?: boolean }): Promise<boolean>;
  dispose(): void;
};

export function createServerDriver(
  server: ExamWorkspaceEditLeaseServer,
  tabId: string,
  yieldLease: (lineageId: string) => Promise<void>,
): ExamWorkspaceEditLeaseDriver {
  const driver: ExamWorkspaceEditLeaseDriver = {
    tabId,
    async claim(lineageId) {
      try {
        await server.claim(lineageId, tabId);
        return "held";
      } catch (error) {
        // A live foreign lease opens read-only; any other failure stays
        // editable, since the write guard refuses a tab without the lease.
        return isEditLeaseHeldError(error) ? "readonly" : "held";
      }
    },
    async renew(lineageId) {
      try {
        const response = await server.renew(lineageId, tabId);
        if (response.takeover_requested) {
          await yieldLease(lineageId);
          return false;
        }
        return true;
      } catch (error) {
        if (isEditLeaseHeldError(error)) {
          return false;
        }
        // A transient failure keeps the hold; the write guard stays authoritative.
        return true;
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
  noteLostLease: () => void,
): ExamWorkspaceEditLeaseDriver {
  const controller = createGuestEditLeaseController({
    now,
    onTakeoverRequested: async () => {
      await onTakeoverRequested();
      noteLostLease();
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
      // The controller's own heartbeat calls this too, so a lost lease turns
      // read-only even when this tab's heartbeat is the one that finds it.
      const held = await controller.renew();
      if (!held) {
        noteLostLease();
      }
      return held;
    },
    requestTakeover: () => controller.requestTakeover(),
  };
}

/** A 409 whose code names the edit lease, not a stale cursor. */
export function isEditLeaseHeldError(error: unknown): boolean {
  return isApiError(error) && error.status === 409 && error.code === "EDIT_LEASE_HELD";
}
