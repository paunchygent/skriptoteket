/**
 * Klassrumskartan guest storage tests.
 *
 * These tests verify that the browser-owned guest snapshot adapter handles the
 * current pointer, TTL expiry, initialization, and reset semantics without
 * relying on server-owned state.
 */

import { describe, expect, it } from "vitest";

import {
  CLASSROOM_PLANNER_GUEST_AUTHORING_CLOSED_KEY,
  CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY,
  createClassroomPlannerGuestStorage,
} from "./classroomPlannerGuestStorage";
import {
  createEmptyClassroomPlannerGuestSnapshot,
} from "./classroomPlannerGuestSnapshot";

function createMemoryStorage(): Storage {
  const data = new Map<string, string>();
  return {
    get length() {
      return data.size;
    },
    clear() {
      data.clear();
    },
    getItem(key: string) {
      return data.has(key) ? (data.get(key) ?? null) : null;
    },
    key(index: number) {
      return Array.from(data.keys())[index] ?? null;
    },
    removeItem(key: string) {
      data.delete(key);
    },
    setItem(key: string, value: string) {
      data.set(key, value);
    },
  };
}

function createMemorySnapshotStore() {
  const records = new Map<string, { snapshot_id: string; snapshot: ReturnType<typeof createEmptyClassroomPlannerGuestSnapshot> }>();
  return {
    records,
    async get(snapshotId: string) {
      return records.get(snapshotId) ?? null;
    },
    async list() {
      return Array.from(records.values());
    },
    async put(record: { snapshot_id: string; snapshot: ReturnType<typeof createEmptyClassroomPlannerGuestSnapshot> }) {
      records.set(record.snapshot_id, record);
    },
    async delete(snapshotId: string) {
      records.delete(snapshotId);
    },
  };
}

describe("classroomPlannerGuestStorage", () => {
  it("initializes an empty guest snapshot and tracks it as current", async () => {
    const storage = createMemoryStorage();
    const snapshotStore = createMemorySnapshotStore();
    const guestStorage = createClassroomPlannerGuestStorage({
      storage,
      snapshotStore,
      nowMs: () => Date.parse("2026-04-04T08:00:00.000Z"),
      createSnapshotId: () => "guest-snapshot-1",
    });

    const result = await guestStorage.initializeEmptySnapshot();

    expect(result.status).toBe("ready");
    expect(result.summary?.snapshot_id).toBe("guest-snapshot-1");
    expect(storage.getItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY)).toBe("guest-snapshot-1");
    expect(snapshotStore.records.size).toBe(1);
  });

  it("returns missing when no current guest snapshot exists", async () => {
    const guestStorage = createClassroomPlannerGuestStorage({
      storage: createMemoryStorage(),
      snapshotStore: createMemorySnapshotStore(),
    });

    const result = await guestStorage.loadCurrentSnapshot();

    expect(result).toEqual({
      status: "missing",
      snapshot: null,
      summary: null,
    });
  });

  it("repairs an orphaned current pointer when the IndexedDB record is gone", async () => {
    const storage = createMemoryStorage();
    storage.setItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY, "guest-snapshot-orphan");
    const snapshotStore = createMemorySnapshotStore();
    const guestStorage = createClassroomPlannerGuestStorage({
      storage,
      snapshotStore,
    });

    const result = await guestStorage.loadCurrentSnapshot();

    expect(result).toEqual({
      status: "missing",
      snapshot: null,
      summary: null,
    });
    expect(storage.getItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY)).toBeNull();
  });

  it("returns expired and clears the current pointer when the snapshot TTL has passed", async () => {
    const storage = createMemoryStorage();
    const snapshotStore = createMemorySnapshotStore();
    const expiredSnapshot = createEmptyClassroomPlannerGuestSnapshot({
      snapshotId: "guest-snapshot-1",
      nowIso: "2026-03-01T08:00:00.000Z",
      expiresAtIso: "2026-03-10T08:00:00.000Z",
    });
    await snapshotStore.put({
      snapshot_id: expiredSnapshot.snapshot_id,
      snapshot: expiredSnapshot,
    });
    storage.setItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY, expiredSnapshot.snapshot_id);

    const guestStorage = createClassroomPlannerGuestStorage({
      storage,
      snapshotStore,
      nowMs: () => Date.parse("2026-04-04T08:00:00.000Z"),
    });

    const result = await guestStorage.loadCurrentSnapshot();

    expect(result.status).toBe("expired");
    expect(result.summary?.snapshot_id).toBe("guest-snapshot-1");
    expect(storage.getItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY)).toBeNull();
    expect(snapshotStore.records.size).toBe(0);
  });

  it("repairs an orphaned current pointer to the most recently updated valid snapshot", async () => {
    const storage = createMemoryStorage();
    const snapshotStore = createMemorySnapshotStore();
    const olderSnapshot = createEmptyClassroomPlannerGuestSnapshot({
      snapshotId: "guest-snapshot-old",
      nowIso: "2026-04-01T08:00:00.000Z",
      expiresAtIso: "2026-04-18T08:00:00.000Z",
    });
    const newerSnapshot = createEmptyClassroomPlannerGuestSnapshot({
      snapshotId: "guest-snapshot-new",
      nowIso: "2026-04-04T08:00:00.000Z",
      expiresAtIso: "2026-04-18T08:00:00.000Z",
    });
    await snapshotStore.put({
      snapshot_id: olderSnapshot.snapshot_id,
      snapshot: olderSnapshot,
    });
    await snapshotStore.put({
      snapshot_id: newerSnapshot.snapshot_id,
      snapshot: newerSnapshot,
    });
    storage.setItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY, "guest-snapshot-missing");

    const guestStorage = createClassroomPlannerGuestStorage({
      storage,
      snapshotStore,
      nowMs: () => Date.parse("2026-04-04T09:00:00.000Z"),
    });

    const result = await guestStorage.loadCurrentSnapshot();

    expect(result.status).toBe("ready");
    expect(result.summary?.snapshot_id).toBe("guest-snapshot-new");
    expect(storage.getItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY)).toBe("guest-snapshot-new");
  });

  it("clears the current guest snapshot and pointer", async () => {
    const storage = createMemoryStorage();
    const snapshotStore = createMemorySnapshotStore();
    const snapshot = createEmptyClassroomPlannerGuestSnapshot({
      snapshotId: "guest-snapshot-1",
      nowIso: "2026-04-04T08:00:00.000Z",
      expiresAtIso: "2026-04-18T08:00:00.000Z",
    });
    await snapshotStore.put({
      snapshot_id: snapshot.snapshot_id,
      snapshot,
    });
    storage.setItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY, snapshot.snapshot_id);

    const guestStorage = createClassroomPlannerGuestStorage({
      storage,
      snapshotStore,
    });

    await guestStorage.clearCurrentSnapshot();

    expect(storage.getItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY)).toBeNull();
    expect(snapshotStore.records.size).toBe(0);
  });

  it("tracks when guest authoring is closed in this browser", async () => {
    const storage = createMemoryStorage();
    const guestStorage = createClassroomPlannerGuestStorage({
      storage,
      snapshotStore: createMemorySnapshotStore(),
    });

    expect(await guestStorage.isGuestAuthoringClosed?.()).toBe(false);

    await guestStorage.markGuestAuthoringClosed?.();

    expect(storage.getItem(CLASSROOM_PLANNER_GUEST_AUTHORING_CLOSED_KEY)).toBe("true");
    expect(await guestStorage.isGuestAuthoringClosed?.()).toBe(true);
  });
});
