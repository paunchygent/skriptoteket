/**
 * Guest exam workspace edit lease.
 *
 * Domain purpose:
 *   One tab at a time edits a guest exam. Opening the exam claims the edit
 *   lease; the claim fails while another tab holds a live lease, so the
 *   other tab stays read-only. The holder renews the lease every 5 s and a
 *   lease not renewed for 15 s is dead, so a crashed tab stops blocking
 *   after 15 s. `Ta över` asks for the lease: the holder stores its pending
 *   edit and releases, and the waiting tab claims the freed lease. Tabs
 *   signal each other through a `BroadcastChannel`, so a takeover between a
 *   guest's tabs is immediate. A closed tab releases its lease on
 *   `pagehide`.
 *
 * Relationships:
 *   - The lease record lives beside the draft in the browser: unit K8 binds
 *     the storage port to the same IndexedDB database as
 *     `examWorkspaceGuestDraftStorage.ts` (its own object store, one record).
 *     The record is plain JSON data, so it fits IndexedDB directly.
 *   - The narrow interface is claim, renew, request takeover, release and
 *     observe. Unit K8 owns the read-only state: its takeover callback
 *     stores the pending edit, then releases; its observer claims the freed
 *     lease and reloads the newest draft.
 *   - No I/O and no IndexedDB here: the port, the clock and the channel are
 *     injected, and the specs run them in memory with a channel double.
 */

export const GUEST_EDIT_LEASE_HEARTBEAT_MS = 5_000;
export const GUEST_EDIT_LEASE_TTL_MS = 15_000;
export const GUEST_EDIT_LEASE_CHANNEL_NAME = "skriptoteket:guest-edit-lease";

/** One lease record: the holding tab, its last renewal and a waiting tab's takeover ask. */
export type GuestEditLeaseRecord = {
  tabId: string;
  /** Last renewal, as milliseconds since the epoch from the injected clock. */
  renewedAt: number;
  /** The tab that asked to take over, or null when nobody waits. */
  takeoverRequestedBy: string | null;
};

export type GuestEditLeaseStoragePort = {
  load(): Promise<GuestEditLeaseRecord | null>;
  save(record: GuestEditLeaseRecord | null): Promise<void>;
};

/** One in-memory lease slot, shared by every controller that receives it, like two tabs. */
export function createInMemoryGuestEditLeaseStorage(): GuestEditLeaseStoragePort {
  let record: GuestEditLeaseRecord | null = null;
  return {
    async load() {
      return record === null ? null : { ...record };
    },
    async save(next) {
      record = next === null ? null : { ...next };
    },
  };
}

export type GuestEditLeaseMessage =
  | { kind: "takeover-requested"; fromTabId: string; toTabId: string }
  | { kind: "lease-released"; byTabId: string };

/** The narrow channel surface the lease needs; `BroadcastChannel` satisfies it. */
export type GuestEditLeaseChannel = {
  postMessage(message: GuestEditLeaseMessage): void;
  addEventListener(type: "message", listener: (event: { data: GuestEditLeaseMessage }) => void): void;
  removeEventListener(
    type: "message",
    listener: (event: { data: GuestEditLeaseMessage }) => void,
  ): void;
  close(): void;
};

function isLeaseMessage(value: unknown): value is GuestEditLeaseMessage {
  if (typeof value !== "object" || value === null || !("kind" in value)) {
    return false;
  }
  const kind: unknown = value.kind;
  if (kind === "takeover-requested" && "fromTabId" in value && "toTabId" in value) {
    return typeof value.fromTabId === "string" && typeof value.toTabId === "string";
  }
  if (kind === "lease-released" && "byTabId" in value) {
    return typeof value.byTabId === "string";
  }
  return false;
}

/** Open the production channel; specs inject a double through `openChannel` instead. */
export function createGuestEditLeaseChannel(
  name: string = GUEST_EDIT_LEASE_CHANNEL_NAME,
): GuestEditLeaseChannel {
  const channel = new BroadcastChannel(name);
  const wrapped = new Map<
    (event: { data: GuestEditLeaseMessage }) => void,
    (event: MessageEvent) => void
  >();
  return {
    addEventListener(type, listener) {
      const handler = (event: MessageEvent): void => {
        if (isLeaseMessage(event.data)) {
          listener({ data: event.data });
        }
      };
      wrapped.set(listener, handler);
      channel.addEventListener(type, handler);
    },
    close() {
      channel.close();
    },
    postMessage(message) {
      channel.postMessage(message);
    },
    removeEventListener(type, listener) {
      const handler = wrapped.get(listener);
      if (handler !== undefined) {
        wrapped.delete(listener);
        channel.removeEventListener(type, handler);
      }
    },
  };
}

/** A random tab id per page load, mirroring the toast id fallback. */
export function createGuestEditLeaseTabId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export type GuestEditLeaseClaimOutcome = "held" | "readonly";
export type GuestEditLeaseTakeoverOutcome = "claimed" | "requested" | "own";

export type GuestEditLeaseEvent =
  | { kind: "takeover-requested"; fromTabId: string }
  | { kind: "lease-released"; byTabId: string };

export type GuestEditLeaseControllerDeps = {
  storage: GuestEditLeaseStoragePort;
  /** Random per page load; distinguishes this tab from every other. */
  tabId: string;
  now?: () => number;
  openChannel?: () => GuestEditLeaseChannel;
  /**
   * Runs when another tab takes over: store the pending edit, then release.
   * Unit K8 provides this; the controller releases afterwards either way.
   */
  onTakeoverRequested?: () => Promise<void> | void;
};

export type GuestEditLeaseController = {
  readonly tabId: string;
  claim(): Promise<GuestEditLeaseClaimOutcome>;
  renew(): Promise<boolean>;
  requestTakeover(): Promise<GuestEditLeaseTakeoverOutcome>;
  release(): Promise<boolean>;
  observe(listener: (event: GuestEditLeaseEvent) => void): () => void;
  dispose(): void;
};

export function createGuestEditLeaseController(
  deps: GuestEditLeaseControllerDeps,
): GuestEditLeaseController {
  const now = deps.now ?? (() => Date.now());
  const channel = (deps.openChannel ?? createGuestEditLeaseChannel)();
  const observers = new Set<(event: GuestEditLeaseEvent) => void>();
  let heartbeat: ReturnType<typeof setInterval> | null = null;
  /** True while this tab answers a takeover, so a channel ping and a heartbeat poll answer once. */
  let answering = false;

  function isExpired(record: GuestEditLeaseRecord, at: number): boolean {
    return at - record.renewedAt > GUEST_EDIT_LEASE_TTL_MS;
  }

  function stopHeartbeat(): void {
    if (heartbeat !== null) {
      clearInterval(heartbeat);
      heartbeat = null;
    }
  }

  function notify(event: GuestEditLeaseEvent): void {
    for (const listener of [...observers]) {
      listener(event);
    }
  }

  async function releaseLease(): Promise<boolean> {
    const record = await deps.storage.load();
    stopHeartbeat();
    if (record === null || record.tabId !== deps.tabId) {
      return false;
    }
    await deps.storage.save(null);
    channel.postMessage({ byTabId: deps.tabId, kind: "lease-released" });
    notify({ byTabId: deps.tabId, kind: "lease-released" });
    return true;
  }

  async function answerTakeover(): Promise<void> {
    if (answering) {
      return;
    }
    answering = true;
    try {
      await deps.onTakeoverRequested?.();
      await releaseLease();
    } finally {
      answering = false;
    }
  }

  function onChannelMessage(event: { data: GuestEditLeaseMessage }): void {
    const message = event.data;
    if (message.kind === "takeover-requested" && message.toTabId === deps.tabId) {
      notify({ fromTabId: message.fromTabId, kind: "takeover-requested" });
      void answerTakeover();
    } else if (message.kind === "lease-released" && message.byTabId !== deps.tabId) {
      notify({ byTabId: message.byTabId, kind: "lease-released" });
    }
  }

  channel.addEventListener("message", onChannelMessage);

  function handlePagehide(): void {
    void releaseLease();
  }
  const hasWindow = typeof window !== "undefined";
  if (hasWindow) {
    window.addEventListener("pagehide", handlePagehide);
  }

  async function renew(): Promise<boolean> {
    const record = await deps.storage.load();
    if (record === null || record.tabId !== deps.tabId) {
      stopHeartbeat();
      return false;
    }
    // The takeover poll fallback: the holder answers at its next heartbeat
    // even when the channel ping never arrived.
    if (record.takeoverRequestedBy !== null && record.takeoverRequestedBy !== deps.tabId) {
      await answerTakeover();
      return false;
    }
    await deps.storage.save({ ...record, renewedAt: now() });
    return true;
  }

  function startHeartbeat(): void {
    if (heartbeat !== null) {
      return;
    }
    heartbeat = setInterval(() => {
      void renew().then((held) => {
        if (!held) {
          stopHeartbeat();
        }
      });
    }, GUEST_EDIT_LEASE_HEARTBEAT_MS);
  }

  return {
    tabId: deps.tabId,
    async claim() {
      const record = await deps.storage.load();
      const at = now();
      if (record !== null && record.tabId !== deps.tabId && !isExpired(record, at)) {
        return "readonly";
      }
      // A self-claim refreshes the renewal and keeps a waiting tab's ask,
      // which the next heartbeat answers.
      const takeoverRequestedBy =
        record !== null && record.tabId === deps.tabId ? record.takeoverRequestedBy : null;
      await deps.storage.save({ renewedAt: at, tabId: deps.tabId, takeoverRequestedBy });
      startHeartbeat();
      return "held";
    },
    dispose() {
      stopHeartbeat();
      channel.removeEventListener("message", onChannelMessage);
      channel.close();
      if (hasWindow) {
        window.removeEventListener("pagehide", handlePagehide);
      }
      observers.clear();
    },
    observe(listener) {
      observers.add(listener);
      return () => {
        observers.delete(listener);
      };
    },
    async release() {
      return await releaseLease();
    },
    renew,
    async requestTakeover() {
      const record = await deps.storage.load();
      const at = now();
      if (record !== null && record.tabId === deps.tabId) {
        return "own";
      }
      if (record === null || isExpired(record, at)) {
        await deps.storage.save({ renewedAt: at, tabId: deps.tabId, takeoverRequestedBy: null });
        startHeartbeat();
        return "claimed";
      }
      await deps.storage.save({ ...record, takeoverRequestedBy: deps.tabId });
      channel.postMessage({
        fromTabId: deps.tabId,
        kind: "takeover-requested",
        toTabId: record.tabId,
      });
      return "requested";
    },
  };
}
