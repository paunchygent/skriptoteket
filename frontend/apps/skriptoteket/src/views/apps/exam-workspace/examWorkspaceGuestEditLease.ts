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
  /**
   * A read-only peek at the slot: tests, the store's lenient pre-check and
   * observers may look, but no claim path decides on what it returns. Every
   * decision below runs atomically inside one step (one IndexedDB readwrite
   * transaction in production, one synchronous decision in memory), and the
   * controller returns the outcome of that atomic decision, never a prior
   * read.
   */
  load(): Promise<GuestEditLeaseRecord | null>;
  /**
   * Claim the slot when it is free, held by this tab, or expired. Returns the
   * resulting record and whether this tab holds the lease afterwards.
   */
  claim(tabId: string, now: number): Promise<GuestEditLeaseClaimResult>;
  /**
   * Renew the slot only while this tab holds it and nobody else asked to take
   * over. Returns the resulting record (null when the slot is empty) and
   * whether this tab still holds the lease.
   */
  renew(tabId: string, now: number): Promise<GuestEditLeaseRenewResult>;
  /** Release the slot only while this tab holds it. */
  release(tabId: string): Promise<boolean>;
  /**
   * Ask to take over: `own` when this tab already holds the slot, `claimed`
   * when the slot is free or expired (this tab takes it at once), else record
   * this tab's ask and return `requested` with the resulting record, whose
   * holder is the tab to signal.
   */
  requestTakeover(tabId: string, now: number): Promise<GuestEditLeaseTakeoverResult>;
};

/** The outcome of one atomic claim decision: the record to keep and who holds it. */
export type GuestEditLeaseClaimResult = {
  record: GuestEditLeaseRecord;
  held: boolean;
};

/** The outcome of one atomic renew decision: the record to keep and who holds it. */
export type GuestEditLeaseRenewResult = {
  record: GuestEditLeaseRecord | null;
  held: boolean;
};

/** The outcome of one atomic takeover decision: what happened and the record to keep. */
export type GuestEditLeaseTakeoverResult = {
  outcome: GuestEditLeaseTakeoverOutcome;
  record: GuestEditLeaseRecord;
};

function isLeaseExpired(record: GuestEditLeaseRecord, at: number): boolean {
  return at - record.renewedAt > GUEST_EDIT_LEASE_TTL_MS;
}

/**
 * The pure claim decision both adapters run inside one atomic step: a live
 * foreign lease refuses, everything else stores the returned record for this
 * tab. A self-claim refreshes the renewal and keeps a waiting tab's ask,
 * which the next heartbeat answers.
 */
export function decideGuestEditLeaseClaim(
  current: GuestEditLeaseRecord | null,
  tabId: string,
  at: number,
): GuestEditLeaseClaimResult {
  if (current !== null && current.tabId !== tabId && !isLeaseExpired(current, at)) {
    return { held: false, record: { ...current } };
  }
  if (current !== null && current.tabId === tabId) {
    return { held: true, record: { ...current, renewedAt: at } };
  }
  return { held: true, record: { renewedAt: at, tabId, takeoverRequestedBy: null } };
}

/**
 * The pure renew decision both adapters run inside one atomic step: only the
 * holding tab renews, and a waiting tab's ask pauses renewal so the holder
 * answers the takeover instead.
 */
export function decideGuestEditLeaseRenew(
  current: GuestEditLeaseRecord | null,
  tabId: string,
  at: number,
): GuestEditLeaseRenewResult {
  if (current === null || current.tabId !== tabId) {
    return { held: false, record: current === null ? null : { ...current } };
  }
  if (current.takeoverRequestedBy !== null && current.takeoverRequestedBy !== tabId) {
    return { held: false, record: { ...current } };
  }
  return { held: true, record: { ...current, renewedAt: at } };
}

/**
 * The pure takeover decision both adapters run inside one atomic step: the
 * holder sees `own`, a free or expired slot is taken at once, otherwise this
 * tab's ask is recorded on the live record.
 */
export function decideGuestEditLeaseTakeover(
  current: GuestEditLeaseRecord | null,
  tabId: string,
  at: number,
): GuestEditLeaseTakeoverResult {
  if (current !== null && current.tabId === tabId) {
    return { outcome: "own", record: { ...current } };
  }
  if (current === null || isLeaseExpired(current, at)) {
    return { outcome: "claimed", record: { renewedAt: at, tabId, takeoverRequestedBy: null } };
  }
  return { outcome: "requested", record: { ...current, takeoverRequestedBy: tabId } };
}

/**
 * The pure release check both adapters run inside one atomic step: only the
 * holding tab frees the slot, so a stale release never clears a new owner.
 */
export function ownsGuestEditLease(
  current: GuestEditLeaseRecord | null,
  tabId: string,
): boolean {
  return current !== null && current.tabId === tabId;
}

/** One in-memory lease slot, shared by every controller that receives it, like two tabs. */
export function createInMemoryGuestEditLeaseStorage(): GuestEditLeaseStoragePort {
  let record: GuestEditLeaseRecord | null = null;
  return {
    async load() {
      return record === null ? null : { ...record };
    },
    async claim(tabId, at) {
      // No await runs between the read and the write below, so concurrent
      // claims against this slot decide one after another, like IndexedDB
      // serializes one readwrite transaction per tab.
      const decided = decideGuestEditLeaseClaim(record, tabId, at);
      if (decided.held) {
        record = { ...decided.record };
      }
      return { held: decided.held, record: { ...decided.record } };
    },
    async renew(tabId, at) {
      const decided = decideGuestEditLeaseRenew(record, tabId, at);
      if (decided.held && decided.record !== null) {
        record = { ...decided.record };
      }
      return {
        held: decided.held,
        record: decided.record === null ? null : { ...decided.record },
      };
    },
    async release(tabId) {
      if (!ownsGuestEditLease(record, tabId)) {
        return false;
      }
      record = null;
      return true;
    },
    async requestTakeover(tabId, at) {
      const decided = decideGuestEditLeaseTakeover(record, tabId, at);
      if (decided.outcome !== "own") {
        record = { ...decided.record };
      }
      return { outcome: decided.outcome, record: { ...decided.record } };
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
    stopHeartbeat();
    const released = await deps.storage.release(deps.tabId);
    if (!released) {
      return false;
    }
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
    const decided = await deps.storage.renew(deps.tabId, now());
    if (!decided.held) {
      stopHeartbeat();
      // The takeover poll fallback: the holder answers at its next heartbeat
      // even when the channel ping never arrived.
      const record = decided.record;
      if (
        record !== null &&
        record.tabId === deps.tabId &&
        record.takeoverRequestedBy !== null &&
        record.takeoverRequestedBy !== deps.tabId
      ) {
        await answerTakeover();
      }
      return false;
    }
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
      // The atomic claim decides and stores in one step: the outcome below
      // is that decision, never a prior read.
      const decided = await deps.storage.claim(deps.tabId, now());
      if (!decided.held) {
        return "readonly";
      }
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
      // The atomic takeover decides and stores in one step: the outcome
      // below is that decision, never a prior read.
      const decided = await deps.storage.requestTakeover(deps.tabId, now());
      if (decided.outcome === "own") {
        return "own";
      }
      if (decided.outcome === "claimed") {
        startHeartbeat();
        return "claimed";
      }
      channel.postMessage({
        fromTabId: deps.tabId,
        kind: "takeover-requested",
        toTabId: decided.record.tabId,
      });
      return "requested";
    },
  };
}
