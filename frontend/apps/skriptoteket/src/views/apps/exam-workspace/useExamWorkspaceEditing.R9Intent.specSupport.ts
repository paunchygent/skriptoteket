/**
 * Shared harness for the R9 intent-side fail-first specs
 * (TASK-SKRIPT-40-04-14, ledger L13 and L14, design section 5).
 *
 * Every spec drives the production editing session against the existing
 * cursor-aware fake server from `useExamWorkspaceEditing.history.specSupport`.
 * Doubles cover only transport, clock, lease responses and server persistence:
 * the server mutations model the other tab's legitimate writes (only after
 * this tab's lease TTL expired) followed by its release. Timing is truthful:
 * a 5 s heartbeat with a 15 s TTL, driven with fake timers and deferreds,
 * never real waits.
 */

import { flushPromises } from "@vue/test-utils";
import { vi } from "vitest";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceEditLeaseResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import {
  exam,
  fakeServer,
  inScope,
  response,
  type EditingApiMocks,
} from "./useExamWorkspaceEditing.history.specSupport";

export type IntentServer = ReturnType<typeof fakeServer>;
export type IntentEditing = ReturnType<typeof useExamWorkspaceEditing>;

/** This tab's lease state, flipped by the test to model loss and recovery. */
export type IntentLeaseState = {
  holder: string;
  offline: boolean;
};

export function intentLeaseState(): IntentLeaseState {
  return { holder: "A", offline: false };
}

function leaseHeldError(): ApiError {
  return new ApiError({ code: "EDIT_LEASE_HELD", message: "held", status: 409 });
}

function leaseHeldResponse(): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: "A",
    renewed_at: "2026-10-20T06:15:00Z",
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

/** The lease double the FF5 probes use: renewals fail while offline. */
export function intentLeaseDouble(state: IntentLeaseState) {
  return {
    claim: () => {
      if (state.holder !== "A") {
        return Promise.reject(leaseHeldError());
      }
      return Promise.resolve(leaseHeldResponse());
    },
    renew: () => {
      if (state.offline) {
        return Promise.reject(new TypeError("network unavailable"));
      }
      if (state.holder !== "A") {
        return Promise.reject(leaseHeldError());
      }
      return Promise.resolve(leaseHeldResponse());
    },
    release: () => Promise.resolve(leaseHeldResponse()),
    requestTakeover: () => Promise.resolve(leaseHeldResponse()),
  };
}

/** Open the exam editable at points [2, 2] with the confirmed baseline. */
export async function openIntentSession(
  api: EditingApiMocks,
  state: IntentLeaseState,
): Promise<{ editing: IntentEditing; server: IntentServer }> {
  const server = fakeServer(api, exam());
  const editing = inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, {
      server: intentLeaseDouble(state),
      tabId: "A",
    }),
  );
  editing.applyCommandResponse(response(exam(), "step-0"));
  await settleIntent();
  return { editing, server };
}

/** Drain the production microtask chains between timer advances. */
export async function settleIntent(turns = 8): Promise<void> {
  for (let index = 0; index < turns; index += 1) {
    await flushPromises();
  }
}

/**
 * Lose the lease past the 15 s TTL: renewals fail, so the gate turns
 * read-only and captures whatever is unconfirmed.
 */
export async function loseIntentLease(
  editing: IntentEditing,
  state: IntentLeaseState,
): Promise<void> {
  state.offline = true;
  await vi.advanceTimersByTimeAsync(16000);
  await settleIntent();
  expectLeaseReadOnly(editing);
}

function expectLeaseReadOnly(editing: IntentEditing): void {
  if (!editing.leaseReadOnly.value) {
    throw new Error("expected the session to be lease read-only");
  }
}

/**
 * Model the other tab's legitimate write: it holds the lease (this tab is
 * past its TTL), stores one new step on the newest server copy, and releases
 * so this tab can claim again.
 */
export function remoteIntentWrite(
  server: IntentServer,
  stepId: string,
  mutate: (document: NativeExamDocument) => NativeExamDocument,
): void {
  const current = server.documents.get(server.state.position);
  if (current === undefined) {
    throw new Error("expected the served document");
  }
  const newer = mutate({
    ...current,
    items: current.items.map((item) => ({ ...item })),
  });
  server.documents.set(stepId, newer);
  server.state.steps.push(stepId);
  server.state.cursor = stepId;
  server.state.position = stepId;
}

/** Reacquire the lease after the other tab released and settle the load. */
export async function reacquireIntentLease(
  editing: IntentEditing,
  state: IntentLeaseState,
): Promise<void> {
  state.holder = "A";
  state.offline = false;
  await vi.advanceTimersByTimeAsync(4000);
  await settleIntent();
  for (let attempt = 0; attempt < 30 && editing.editingLocked.value; attempt += 1) {
    await vi.advanceTimersByTimeAsync(1000);
    await settleIntent();
  }
  await settleIntent();
}

/** Lose, remotely write, and reacquire in one step (this tab owns nothing new). */
export async function remoteCycle(
  editing: IntentEditing,
  state: IntentLeaseState,
  server: IntentServer,
  stepId: string,
  mutate: (document: NativeExamDocument) => NativeExamDocument,
): Promise<void> {
  await loseIntentLease(editing, state);
  state.holder = "B";
  remoteIntentWrite(server, stepId, mutate);
  await reacquireIntentLease(editing, state);
}

export function pointsOf(document: NativeExamDocument | null): Array<number | null> {
  if (document === null) {
    throw new Error("expected an open document");
  }
  return document.items.map((item) => item.points);
}

export function persistedPointsOf(server: IntentServer): Array<number | null> {
  return pointsOf(server.documents.get(server.state.position) ?? null);
}

export function storeCallsOf(api: EditingApiMocks): number {
  return api.storeExamWorkspaceUndoStep.mock.calls.length;
}

export function resetIntentMocks(api: EditingApiMocks): void {
  for (const mock of Object.values(api)) {
    mock.mockReset();
  }
}
