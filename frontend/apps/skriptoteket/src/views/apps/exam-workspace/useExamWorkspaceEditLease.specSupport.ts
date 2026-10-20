/**
 * Shared doubles for the `useExamWorkspaceEditLease` server-lease specs.
 *
 * Purpose:
 *   One fake lease server with the production K6 semantics (claim on open,
 *   5 s renew, 15 s death, takeover request, release) plus the effect-scope
 *   setup every split spec opens its composable through, so the
 *   claim/renew/takeover/lifecycle specs share one fake instead of copying it.
 */

import { flushPromises } from "@vue/test-utils";
import { effectScope } from "vue";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceEditLeaseResponse } from "../../../api/examWorkspace";
import { createSyncFence } from "./examWorkspaceSyncFence";
import {
  EXAM_WORKSPACE_EDIT_LEASE_TTL_MS,
  useExamWorkspaceEditLease,
} from "./useExamWorkspaceEditLease";

export const LINEAGE = "00000000-0000-4000-8000-000000000001";
export const OTHER_LINEAGE = "00000000-0000-4000-8000-000000000002";

export function heldError(): ApiError {
  return new ApiError({ code: "EDIT_LEASE_HELD", message: "Provet redigeras i en annan flik.", status: 409 });
}

/** A lease server with the K6 semantics and a test-controlled clock. */
export function createFakeLeaseServer() {
  let nowMs = 1_000_000;
  let holder: string | null = null;
  let renewedAt = 0;
  let waiting: string | null = null;
  const live = () => holder !== null && nowMs - renewedAt < EXAM_WORKSPACE_EDIT_LEASE_TTL_MS;
  const response = (forTab: string): ExamWorkspaceEditLeaseResponse => ({
    holder_tab_id: holder,
    renewed_at: new Date(renewedAt).toISOString(),
    takeover_requested: waiting !== null && waiting !== forTab,
    takeover_requested_by: waiting,
  });
  const server = {
    async claim(_lineage: string, tabId: string) {
      if (live() && holder !== tabId) {
        throw heldError();
      }
      holder = tabId;
      renewedAt = nowMs;
      if (waiting === tabId) {
        waiting = null;
      }
      return response(tabId);
    },
    async renew(_lineage: string, tabId: string) {
      if (!live() || holder !== tabId) {
        throw heldError();
      }
      renewedAt = nowMs;
      return response(tabId);
    },
    async requestTakeover(_lineage: string, tabId: string) {
      if (holder === tabId) {
        return response(tabId);
      }
      waiting = tabId;
      return response(tabId);
    },
    async release(_lineage: string, tabId: string) {
      if (!live() || holder !== tabId) {
        throw heldError();
      }
      holder = null;
      renewedAt = 0;
      return response(tabId);
    },
  };
  return {
    advance: (ms: number) => {
      nowMs += ms;
    },
    server,
    state: () => ({ holder, waiting }),
  };
}

export type LeaseSetup = {
  lineage: string | null;
  flushed: string[];
  acquired: string[];
  lease: ReturnType<typeof useExamWorkspaceEditLease>;
  stop: () => void;
};

export function setupLease(
  fake: ReturnType<typeof createFakeLeaseServer>,
  options: { tabId: string; lineage?: string | null } & Partial<
    Pick<Parameters<typeof useExamWorkspaceEditLease>[0], "onLeaseAcquired" | "onTakeoverRequested">
  >,
): LeaseSetup {
  const scope = effectScope();
  const holder = { lineage: options.lineage ?? LINEAGE };
  const flushed: string[] = [];
  const acquired: string[] = [];
  const lease = scope.run(() =>
    useExamWorkspaceEditLease({
      fence: createSyncFence(),
      lineageId: () => holder.lineage,
      isGuest: () => false,
      server: fake.server,
      tabId: options.tabId,
      onLeaseAcquired: options.onLeaseAcquired ?? (() => {
        acquired.push("reloaded");
      }),
      onLeaseLost: () => undefined,
      onLeaseRefused: () => undefined,
      onTakeoverRequested: options.onTakeoverRequested ?? (async () => {
        flushed.push("stored");
      }),
    }),
  )!;
  lease.openLineage(holder.lineage);
  return {
    acquired,
    flushed,
    lease,
    lineage: holder.lineage,
    stop: () => scope.stop(),
  };
}

export async function settle(): Promise<void> {
  await flushPromises();
}
