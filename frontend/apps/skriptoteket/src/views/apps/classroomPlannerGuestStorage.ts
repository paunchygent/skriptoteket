/**
 * Klassrumskartan guest snapshot browser storage.
 *
 * This module makes the browser authoritative for the public guest workspace
 * foundation by persisting versioned snapshots in IndexedDB and keeping only a
 * lightweight current-snapshot pointer in localStorage.
 */

import { openDB, type DBSchema, type IDBPDatabase } from "idb";

import {
  CLASSROOM_PLANNER_GUEST_SNAPSHOT_TTL_DAYS,
  createEmptyClassroomPlannerGuestSnapshot,
  summarizeClassroomPlannerGuestSnapshot,
  type ClassroomPlannerGuestSnapshot,
  type ClassroomPlannerGuestSnapshotLoadResult,
  type ClassroomPlannerGuestSnapshotSummary,
} from "./classroomPlannerGuestSnapshot";

export const CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY =
  "skriptoteket:classroom-planner:public-snapshot-id";
export const CLASSROOM_PLANNER_GUEST_AUTHORING_CLOSED_KEY =
  "skriptoteket:classroom-planner:guest-authoring-closed";

type SnapshotKeyValueStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

type ClassroomPlannerGuestSnapshotRecord = {
  snapshot_id: string;
  snapshot: ClassroomPlannerGuestSnapshot;
};

type SnapshotStoreLike = {
  get(snapshotId: string): Promise<ClassroomPlannerGuestSnapshotRecord | null>;
  list(): Promise<ClassroomPlannerGuestSnapshotRecord[]>;
  put(record: ClassroomPlannerGuestSnapshotRecord): Promise<void>;
  delete(snapshotId: string): Promise<void>;
};

type ClassroomPlannerGuestSnapshotDb = DBSchema & {
  classroom_planner_guest_snapshots: {
    key: string;
    value: ClassroomPlannerGuestSnapshotRecord;
  };
};

const DB_NAME = "skriptoteket_curated_apps";
const DB_VERSION = 1;

let dbPromise: Promise<IDBPDatabase<ClassroomPlannerGuestSnapshotDb>> | null = null;

function getDb(): Promise<IDBPDatabase<ClassroomPlannerGuestSnapshotDb>> {
  if (!dbPromise) {
    dbPromise = openDB<ClassroomPlannerGuestSnapshotDb>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains("classroom_planner_guest_snapshots")) {
          db.createObjectStore("classroom_planner_guest_snapshots", {
            keyPath: "snapshot_id",
          });
        }
      },
    });
  }
  return dbPromise;
}

async function createIndexedDbSnapshotStore(): Promise<SnapshotStoreLike> {
  const db = await getDb();
  return {
    async get(snapshotId) {
      return (await db.get("classroom_planner_guest_snapshots", snapshotId)) ?? null;
    },
    async list() {
      return await db.getAll("classroom_planner_guest_snapshots");
    },
    async put(record) {
      await db.put("classroom_planner_guest_snapshots", record);
    },
    async delete(snapshotId) {
      await db.delete("classroom_planner_guest_snapshots", snapshotId);
    },
  };
}

function addDays(timestampMs: number, days: number): number {
  return timestampMs + days * 24 * 60 * 60 * 1000;
}

function parseIsoTimestamp(value: string): number {
  return Date.parse(value);
}

function buildSummary(snapshot: ClassroomPlannerGuestSnapshot): ClassroomPlannerGuestSnapshotSummary {
  return summarizeClassroomPlannerGuestSnapshot(snapshot);
}

function snapshotSortTimestamp(snapshot: ClassroomPlannerGuestSnapshot): number {
  return parseIsoTimestamp(snapshot.updated_at) || parseIsoTimestamp(snapshot.created_at) || 0;
}

function defaultCreateSnapshotId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `guest-snapshot-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export type ClassroomPlannerGuestStoragePort = {
  loadCurrentSnapshot: () => Promise<ClassroomPlannerGuestSnapshotLoadResult>;
  saveSnapshot: (snapshot: ClassroomPlannerGuestSnapshot) => Promise<void>;
  initializeEmptySnapshot: () => Promise<ClassroomPlannerGuestSnapshotLoadResult>;
  clearCurrentSnapshot: () => Promise<void>;
  isGuestAuthoringClosed?: () => Promise<boolean>;
  markGuestAuthoringClosed?: () => Promise<void>;
};

export function createClassroomPlannerGuestStorage(deps?: {
  nowMs?: () => number;
  storage?: SnapshotKeyValueStorage;
  snapshotStore?: SnapshotStoreLike;
  createSnapshotId?: () => string;
}) {
  const nowMs = deps?.nowMs ?? (() => Date.now());
  const storage = deps?.storage ?? window.localStorage;
  const createSnapshotId = deps?.createSnapshotId ?? defaultCreateSnapshotId;

  async function getSnapshotStore(): Promise<SnapshotStoreLike> {
    return deps?.snapshotStore ?? (await createIndexedDbSnapshotStore());
  }

  async function loadCurrentSnapshot(): Promise<ClassroomPlannerGuestSnapshotLoadResult> {
    const snapshotId = storage.getItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY);
    if (!snapshotId) {
      return { status: "missing", snapshot: null, summary: null };
    }

    const store = await getSnapshotStore();
    const record = await store.get(snapshotId);
    if (!record) {
      const repairedSnapshot = await repairOrphanedCurrentPointer(store);
      if (repairedSnapshot) {
        return repairedSnapshot;
      }
      storage.removeItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY);
      return { status: "missing", snapshot: null, summary: null };
    }

    const summary = buildSummary(record.snapshot);
    const isExpired = parseIsoTimestamp(record.snapshot.expires_at) <= nowMs();
    if (isExpired) {
      await store.delete(snapshotId);
      storage.removeItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY);
      return {
        status: "expired",
        snapshot: null,
        summary,
      };
    }

    return {
      status: "ready",
      snapshot: record.snapshot,
      summary,
    };
  }

  async function repairOrphanedCurrentPointer(
    store: SnapshotStoreLike,
  ): Promise<ClassroomPlannerGuestSnapshotLoadResult | null> {
    const snapshots = await store.list();
    const validCandidates = snapshots
      .map((record) => record.snapshot)
      .filter((snapshot) => parseIsoTimestamp(snapshot.expires_at) > nowMs())
      .sort((left, right) => snapshotSortTimestamp(right) - snapshotSortTimestamp(left));

    const repairedSnapshot = validCandidates[0] ?? null;
    if (!repairedSnapshot) {
      return null;
    }

    storage.setItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY, repairedSnapshot.snapshot_id);
    return {
      status: "ready",
      snapshot: repairedSnapshot,
      summary: buildSummary(repairedSnapshot),
    };
  }

  async function saveSnapshot(snapshot: ClassroomPlannerGuestSnapshot): Promise<void> {
    const store = await getSnapshotStore();
    await store.put({
      snapshot_id: snapshot.snapshot_id,
      snapshot,
    });
    storage.setItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY, snapshot.snapshot_id);
  }

  async function initializeEmptySnapshot(): Promise<ClassroomPlannerGuestSnapshotLoadResult> {
    const snapshotId = createSnapshotId();
    const createdAtMs = nowMs();
    const snapshot = createEmptyClassroomPlannerGuestSnapshot({
      snapshotId,
      nowIso: new Date(createdAtMs).toISOString(),
      expiresAtIso: new Date(
        addDays(createdAtMs, CLASSROOM_PLANNER_GUEST_SNAPSHOT_TTL_DAYS),
      ).toISOString(),
    });
    await saveSnapshot(snapshot);
    return {
      status: "ready",
      snapshot,
      summary: buildSummary(snapshot),
    };
  }

  async function clearCurrentSnapshot(): Promise<void> {
    const snapshotId = storage.getItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY);
    storage.removeItem(CLASSROOM_PLANNER_GUEST_SNAPSHOT_POINTER_KEY);
    if (!snapshotId) {
      return;
    }
    const store = await getSnapshotStore();
    await store.delete(snapshotId);
  }

  async function isGuestAuthoringClosed(): Promise<boolean> {
    return storage.getItem(CLASSROOM_PLANNER_GUEST_AUTHORING_CLOSED_KEY) === "true";
  }

  async function markGuestAuthoringClosed(): Promise<void> {
    storage.setItem(CLASSROOM_PLANNER_GUEST_AUTHORING_CLOSED_KEY, "true");
  }

  return {
    loadCurrentSnapshot,
    saveSnapshot,
    initializeEmptySnapshot,
    clearCurrentSnapshot,
    isGuestAuthoringClosed,
    markGuestAuthoringClosed,
  };
}
