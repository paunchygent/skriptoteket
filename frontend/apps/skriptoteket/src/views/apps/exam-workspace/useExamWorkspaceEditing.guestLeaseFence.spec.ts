/**
 * Exam workspace editing session: guest lease-fence fail-first ports
 * (TASK-SKRIPT-40-04-14, unit FF3, rereview 6).
 *
 * Ported from the reviewer's failing probes, kept scenario-for-scenario with
 * truthful names. Every test drives the public editing session
 * (`applyCommandResponse`, `openDocument`) and the production in-memory
 * guest bank, as the probes do. Each test fails at 31fbd255 the way the
 * reviewer saw it.
 *
 * Probe source (read-only, not edited):
 *   guest-neighbours.spec.mjs, the four cases behind R6-1, R6-2 (two renew
 *   cases) and R6-3.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceEditLeaseResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import {
  type GuestEditLeaseChannel,
  type GuestEditLeaseClaimResult,
  type GuestEditLeaseRenewResult,
  type GuestEditLeaseStoragePort,
} from "./examWorkspaceGuestEditLease";
import { createInMemoryGuestEditLeaseStorage } from "./examWorkspaceGuestEditLeaseMemory";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { nullRouteProjection } from "./examWorkspaceRouteProjection.specSupport";
import type { ExamWorkspaceEditLeaseServer } from "./examWorkspaceEditLeaseDrivers";
import {
  LINEAGE,
  exam,
  fakeServer,
  inScope,
  response,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";
import { deferred } from "./useExamWorkspaceSyncGate.specSupport";

const api = vi.hoisted(() => ({
  copyExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  retryExamWorkspaceItem: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));
vi.mock("../../../composables/useAiAccess", () => ({ useAiAccess: () => ({ canUseAi: { value: true } }) }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const EXAM_B = "00000000-0000-4000-8000-000000000002";

function reply(
  document: NativeExamDocument,
  cursor = "step-0",
  lineage: string = LINEAGE,
): ExamWorkspaceDocumentResponse {
  const payload = response(document, cursor);
  return { ...payload, summary: { ...payload.summary, lineage_id: lineage, vault_file_id: lineage } };
}

/** The probe's no-op channel seam: takeover answers arrive only via the heartbeat poll. */
function channel(): GuestEditLeaseChannel {
  return {
    addEventListener() {},
    close() {},
    postMessage() {},
    removeEventListener() {},
  };
}

function guestSession(storage: GuestEditLeaseStoragePort): ReturnType<typeof useExamWorkspaceEditing> {
  const store = {
    ...serverExamWorkspaceStore,
    guest: {
      startBlank: () => Promise.resolve(LINEAGE),
      startFromQti: () => Promise.resolve(LINEAGE),
    },
  };
  return inScope(() =>
    useExamWorkspaceEditing(store, nullRouteProjection(), { guestStorage: storage, openGuestChannel: channel, tabId: "tab-a" }),
  );
}

async function openExamB(
  editing: ReturnType<typeof useExamWorkspaceEditing>,
  base: NativeExamDocument,
): Promise<void> {
  api.getExamWorkspaceDocument.mockResolvedValue(reply({ ...base, document_id: EXAM_B, title: "Exam B" }, "step-0", EXAM_B));
  expect(await editing.requestRoute(EXAM_B)).toBe("installed");
  await flushPromises();
  expect(editing.editingLocked.value).toBe(false);
}

describe("the guest lease fence fail-first ports", () => {
  it("a stale guest claim for A must not release the shared slot now held for B", async () => {
    vi.useFakeTimers();
    const base = exam();
    fakeServer(api, base);
    const storage = createInMemoryGuestEditLeaseStorage();
    const old = deferred<GuestEditLeaseClaimResult>();
    let first = true;
    let grant: GuestEditLeaseClaimResult | undefined = undefined;
    const port: GuestEditLeaseStoragePort = {
      ...storage,
      claim: async (...args: Parameters<GuestEditLeaseStoragePort["claim"]>) => {
        const decided = await storage.claim(...args);
        if (first) {
          first = false;
          grant = decided;
          return old.promise;
        }
        return decided;
      },
    };
    const editing = guestSession(port);
    editing.applyCommandResponse(reply(base));
    await flushPromises();
    expect((await storage.load())?.tabId).toBe("tab-a");
    await openExamB(editing, base);
    if (grant === undefined) {
      throw new Error("expected the delayed claim grant");
    }
    old.resolve(grant);
    await flushPromises();
    await flushPromises();
    const other = await storage.claim("tab-b", Date.now());
    expect({ holder: (await storage.load())?.tabId, editableB: !editing.editingLocked.value, otherHeld: other.held }).toEqual({
      holder: "tab-a",
      editableB: true,
      otherHeld: false,
    });
  });

  it("the guest driver must not apply an obsolete lost renew before the fence", async () => {
    vi.useFakeTimers();
    const base = exam();
    fakeServer(api, base);
    const storage = createInMemoryGuestEditLeaseStorage();
    const old = deferred<GuestEditLeaseRenewResult>();
    let renews = 0;
    let lost: GuestEditLeaseRenewResult | undefined = undefined;
    const port: GuestEditLeaseStoragePort = {
      ...storage,
      renew: async (...args: Parameters<GuestEditLeaseStoragePort["renew"]>) => {
        renews += 1;
        if (renews === 2) {
          await storage.release("tab-a");
          lost = await storage.renew(...args);
          return old.promise;
        }
        return storage.renew(...args);
      },
    };
    const editing = guestSession(port);
    editing.applyCommandResponse(reply(base));
    await flushPromises();
    await vi.advanceTimersByTimeAsync(5000);
    expect(renews).toBe(2);
    await openExamB(editing, base);
    if (lost === undefined) {
      throw new Error("expected the delayed lost renew");
    }
    old.resolve(lost);
    await flushPromises();
    expect({
      holder: (await storage.load())?.tabId,
      locked: editing.editingLocked.value,
      title: editing.workspaceDocument.value?.title,
    }).toEqual({ holder: "tab-a", locked: false, title: "Exam B" });
  });

  it("the guest controller must date a takeover result before awaiting its renew decision", async () => {
    vi.useFakeTimers();
    const base = exam();
    fakeServer(api, base);
    const storage = createInMemoryGuestEditLeaseStorage();
    const old = deferred<GuestEditLeaseRenewResult>();
    let renews = 0;
    let ask: GuestEditLeaseRenewResult | undefined = undefined;
    const port: GuestEditLeaseStoragePort = {
      ...storage,
      renew: async (...args: Parameters<GuestEditLeaseStoragePort["renew"]>) => {
        renews += 1;
        if (renews === 1) {
          await storage.requestTakeover("tab-b", Date.now());
          ask = await storage.renew(...args);
          return old.promise;
        }
        return storage.renew(...args);
      },
    };
    const editing = guestSession(port);
    editing.applyCommandResponse(reply(base));
    await flushPromises();
    await vi.advanceTimersByTimeAsync(5000);
    expect(renews).toBe(2);
    // The owner's outer heartbeat also sees the ask, legitimately yielding A.
    // B then claims a clean slot before the controller's earlier answer lands.
    await flushPromises();
    await openExamB(editing, base);
    expect((await storage.load())?.takeoverRequestedBy).toBe(null);
    if (ask === undefined) {
      throw new Error("expected the delayed takeover answer");
    }
    old.resolve(ask);
    await flushPromises();
    await flushPromises();
    expect({ holder: (await storage.load())?.tabId, locked: editing.editingLocked.value }).toEqual({
      holder: "tab-a",
      locked: false,
    });
  });

  it("pagehide must retire a pending initial claim even though holding was never true", async () => {
    const events = new EventTarget();
    vi.stubGlobal("window", events);
    const base = exam();
    fakeServer(api, base);
    const readHistory = api.getExamWorkspaceHistory.getMockImplementation();
    if (readHistory === undefined) {
      throw new Error("expected the history double");
    }
    const claim = deferred<ExamWorkspaceEditLeaseResponse>();
    const history = deferred<unknown>();
    api.getExamWorkspaceHistory.mockReturnValue(history.promise);
    const held: ExamWorkspaceEditLeaseResponse = {
      holder_tab_id: "A",
      renewed_at: "2026-10-20T07:00:00Z",
      takeover_requested: false,
      takeover_requested_by: null,
    };
    const driver: ExamWorkspaceEditLeaseServer = {
      claim: () => claim.promise,
      release: () => Promise.resolve({ ...held, holder_tab_id: null }),
      renew: () => Promise.resolve(held),
      requestTakeover: () => Promise.resolve(held),
    };
    const editing = inScope(() => useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), { server: driver, tabId: "A" }));
    editing.applyCommandResponse(reply(base));
    await flushPromises();
    expect(editing.editingLocked.value).toBe(true);
    events.dispatchEvent(new Event("pagehide"));
    claim.resolve(held);
    history.resolve(await readHistory(LINEAGE));
    await flushPromises();
    await flushPromises();
    expect({ locked: editing.editingLocked.value, position: editing.history.position.value }).toEqual({
      locked: true,
      position: null,
    });
  });

  it("pagehide while the initial claim is pending stays recoverable through the next heartbeat", async () => {
    const events = new EventTarget();
    vi.stubGlobal("window", events);
    vi.useFakeTimers();
    const base = exam();
    fakeServer(api, base);
    const readHistory = api.getExamWorkspaceHistory.getMockImplementation();
    if (readHistory === undefined) {
      throw new Error("expected the history double");
    }
    const claim = deferred<ExamWorkspaceEditLeaseResponse>();
    const history = deferred<unknown>();
    api.getExamWorkspaceHistory.mockReturnValue(history.promise);
    const held: ExamWorkspaceEditLeaseResponse = {
      holder_tab_id: "A",
      renewed_at: "2026-10-20T07:00:00Z",
      takeover_requested: false,
      takeover_requested_by: null,
    };
    const driver: ExamWorkspaceEditLeaseServer = {
      claim: () => claim.promise,
      release: () => Promise.resolve({ ...held, holder_tab_id: null }),
      renew: () => Promise.resolve(held),
      requestTakeover: () => Promise.resolve(held),
    };
    const editing = inScope(() => useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), { server: driver, tabId: "A" }));
    editing.applyCommandResponse(reply(base));
    await flushPromises();
    expect(editing.editingLocked.value).toBe(true);
    events.dispatchEvent(new Event("pagehide"));
    claim.resolve(held);
    history.resolve(await readHistory(LINEAGE));
    await flushPromises();
    await flushPromises();
    expect({ locked: editing.editingLocked.value, position: editing.history.position.value }).toEqual({
      locked: true,
      position: null,
    });
    // The stale claim dropped, so the running heartbeat retries the claim and
    // the gate's fresh load installs the document: the session ends editable.
    api.getExamWorkspaceHistory.mockImplementation(readHistory);
    await vi.advanceTimersByTimeAsync(5_000);
    await flushPromises();
    await flushPromises();
    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect({
      locked: editing.editingLocked.value,
      position: editing.history.position.value,
      title: workspace.title,
    }).toEqual({ locked: false, position: "step-0", title: "Original" });
  });

  it("pagehide must retire a pending heartbeat claim while the gate was already readonly", async () => {
    vi.useFakeTimers();
    const events = new EventTarget();
    vi.stubGlobal("window", events);
    const base = exam();
    fakeServer(api, base);
    const claim = deferred<ExamWorkspaceEditLeaseResponse>();
    let claims = 0;
    const held: ExamWorkspaceEditLeaseResponse = {
      holder_tab_id: "A",
      renewed_at: "2026-10-20T07:00:00Z",
      takeover_requested: false,
      takeover_requested_by: null,
    };
    const driver: ExamWorkspaceEditLeaseServer = {
      claim: () => {
        claims += 1;
        if (claims === 1) {
          return Promise.reject(new ApiError({ code: "EDIT_LEASE_HELD", message: "held", status: 409 }));
        }
        return claim.promise;
      },
      release: () => Promise.resolve({ ...held, holder_tab_id: null }),
      renew: () => Promise.resolve(held),
      requestTakeover: () => Promise.resolve(held),
    };
    const editing = inScope(() => useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), { server: driver, tabId: "A" }));
    editing.applyCommandResponse(reply(base));
    await flushPromises();
    expect(editing.leaseReadOnly.value).toBe(true);
    await vi.advanceTimersByTimeAsync(5000);
    expect(claims).toBe(2);
    api.getExamWorkspaceDocument.mockResolvedValue(
      reply({
        ...base,
        items: base.items.map((item) => (item.item_id === "item_002" ? { ...item, points: 9 } : item)),
      }),
    );
    events.dispatchEvent(new Event("pagehide"));
    claim.resolve(held);
    await flushPromises();
    await flushPromises();
    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect({ locked: editing.editingLocked.value, points: workspace.items[1]?.points }).toEqual({
      locked: true,
      points: 2,
    });
  });
});
