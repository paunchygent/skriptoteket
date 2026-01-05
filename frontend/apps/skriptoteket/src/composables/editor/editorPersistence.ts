import { openDB, type DBSchema, type IDBPDatabase } from "idb";

export type EditorWorkingCopyFields = {
  entrypoint: string;
  sourceCode: string;
  settingsSchemaText: string;
  inputSchemaText: string;
  usageInstructions: string;
};

export type WorkingCopyHeadRecord = {
  user_id: string;
  tool_id: string;
  base_version_id: string | null;
  entrypoint: string;
  source_code: string;
  settings_schema: string;
  input_schema: string;
  usage_instructions: string;
  updated_at: number;
  expires_at: number;
};

export type CheckpointKind = "auto" | "pinned";

export type CheckpointRecord = {
  user_id: string;
  tool_id: string;
  checkpoint_id: string;
  kind: CheckpointKind;
  label: string | null;
  base_version_id: string | null;
  entrypoint: string;
  source_code: string;
  settings_schema: string;
  input_schema: string;
  usage_instructions: string;
  created_at: number;
  expires_at: number | null;
};

type WorkingCopyKey = [string, string];
type CheckpointKey = [string, string, string];
type ChatThreadKey = [string, string];

export type ChatThreadRecord = {
  user_id: string;
  tool_id: string;
  updated_at: number;
};

type EditorPersistenceDb = DBSchema & {
  working_copy_heads: {
    key: WorkingCopyKey;
    value: WorkingCopyHeadRecord;
    indexes: { by_expires_at: number };
  };
  checkpoints: {
    key: CheckpointKey;
    value: CheckpointRecord;
    indexes: {
      by_user_tool_created_at: [string, string, number];
      by_user_tool_kind_created_at: [string, string, CheckpointKind, number];
    };
  };
  chat_threads: {
    key: ChatThreadKey;
    value: ChatThreadRecord;
    indexes: { by_updated_at: number };
  };
};

const DB_NAME = "skriptoteket_editor";
const DB_VERSION = 2;

export const WORKING_COPY_HEAD_TTL_DAYS = 30;
export const AUTO_CHECKPOINT_TTL_DAYS = 7;
export const AUTO_CHECKPOINT_CAP = 20;
export const PINNED_CHECKPOINT_CAP = 20;

let dbPromise: Promise<IDBPDatabase<EditorPersistenceDb>> | null = null;

function getDb(): Promise<IDBPDatabase<EditorPersistenceDb>> {
  if (!dbPromise) {
    dbPromise = openDB<EditorPersistenceDb>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains("working_copy_heads")) {
          const store = db.createObjectStore("working_copy_heads", {
            keyPath: ["user_id", "tool_id"],
          });
          store.createIndex("by_expires_at", "expires_at");
        }

        if (!db.objectStoreNames.contains("checkpoints")) {
          const store = db.createObjectStore("checkpoints", {
            keyPath: ["user_id", "tool_id", "checkpoint_id"],
          });
          store.createIndex("by_user_tool_created_at", ["user_id", "tool_id", "created_at"]);
          store.createIndex("by_user_tool_kind_created_at", [
            "user_id",
            "tool_id",
            "kind",
            "created_at",
          ]);
        }

        if (!db.objectStoreNames.contains("chat_threads")) {
          const store = db.createObjectStore("chat_threads", { keyPath: ["user_id", "tool_id"] });
          store.createIndex("by_updated_at", "updated_at");
        } else {
          db.deleteObjectStore("chat_threads");
          const store = db.createObjectStore("chat_threads", { keyPath: ["user_id", "tool_id"] });
          store.createIndex("by_updated_at", "updated_at");
        }
      },
    });
  }

  return dbPromise;
}

function nowMs(): number {
  return Date.now();
}

function addDays(timestampMs: number, days: number): number {
  return timestampMs + days * 24 * 60 * 60 * 1000;
}

function asWorkingCopyKey(userId: string, toolId: string): WorkingCopyKey {
  return [userId, toolId];
}

function asCheckpointKey(record: CheckpointRecord): CheckpointKey {
  return [record.user_id, record.tool_id, record.checkpoint_id];
}

function isExpired(expiresAt: number | null | undefined, now: number): boolean {
  if (!expiresAt) return false;
  return expiresAt <= now;
}

function normalizeFields(fields: EditorWorkingCopyFields) {
  return {
    entrypoint: fields.entrypoint,
    source_code: fields.sourceCode,
    settings_schema: fields.settingsSchemaText,
    input_schema: fields.inputSchemaText,
    usage_instructions: fields.usageInstructions,
  };
}

export function checkpointFieldsFromRecord(record: CheckpointRecord): EditorWorkingCopyFields {
  return {
    entrypoint: record.entrypoint,
    sourceCode: record.source_code,
    settingsSchemaText: record.settings_schema,
    inputSchemaText: record.input_schema,
    usageInstructions: record.usage_instructions,
  };
}

export function workingCopyFieldsFromRecord(record: WorkingCopyHeadRecord): EditorWorkingCopyFields {
  return {
    entrypoint: record.entrypoint,
    sourceCode: record.source_code,
    settingsSchemaText: record.settings_schema,
    inputSchemaText: record.input_schema,
    usageInstructions: record.usage_instructions,
  };
}

export async function getWorkingCopyHead(params: {
  userId: string;
  toolId: string;
  now?: number;
}): Promise<WorkingCopyHeadRecord | null> {
  const db = await getDb();
  const key = asWorkingCopyKey(params.userId, params.toolId);
  const record = await db.get("working_copy_heads", key);
  if (!record) return null;

  const now = params.now ?? nowMs();
  if (isExpired(record.expires_at, now)) {
    await db.delete("working_copy_heads", key);
    return null;
  }

  return record;
}

export async function saveWorkingCopyHead(params: {
  userId: string;
  toolId: string;
  baseVersionId: string | null;
  fields: EditorWorkingCopyFields;
  now?: number;
}): Promise<WorkingCopyHeadRecord> {
  const db = await getDb();
  const now = params.now ?? nowMs();
  const record: WorkingCopyHeadRecord = {
    user_id: params.userId,
    tool_id: params.toolId,
    base_version_id: params.baseVersionId,
    ...normalizeFields(params.fields),
    updated_at: now,
    expires_at: addDays(now, WORKING_COPY_HEAD_TTL_DAYS),
  };
  await db.put("working_copy_heads", record);
  return record;
}

export async function clearWorkingCopyData(params: {
  userId: string;
  toolId: string;
}): Promise<void> {
  const db = await getDb();
  const key = asWorkingCopyKey(params.userId, params.toolId);

  const tx = db.transaction(["working_copy_heads", "checkpoints"], "readwrite");
  await tx.objectStore("working_copy_heads").delete(key);

  const checkpointStore = tx.objectStore("checkpoints");
  const range = IDBKeyRange.bound(
    [params.userId, params.toolId, 0],
    [params.userId, params.toolId, Number.POSITIVE_INFINITY],
  );
  const keys = await checkpointStore.index("by_user_tool_created_at").getAllKeys(range);
  for (const checkpointKey of keys) {
    await checkpointStore.delete(checkpointKey as CheckpointKey);
  }

  await tx.done;
}

export async function listCheckpoints(params: {
  userId: string;
  toolId: string;
  now?: number;
}): Promise<CheckpointRecord[]> {
  const db = await getDb();
  const now = params.now ?? nowMs();

  const tx = db.transaction("checkpoints", "readwrite");
  const store = tx.objectStore("checkpoints");
  const range = IDBKeyRange.bound(
    [params.userId, params.toolId, 0],
    [params.userId, params.toolId, Number.POSITIVE_INFINITY],
  );
  const records = await store.index("by_user_tool_created_at").getAll(range);
  const active: CheckpointRecord[] = [];

  for (const record of records) {
    if (isExpired(record.expires_at, now)) {
      await store.delete(asCheckpointKey(record));
    } else {
      active.push(record);
    }
  }

  await tx.done;
  return active.sort((a, b) => b.created_at - a.created_at);
}

function createCheckpointId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `checkpoint-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export async function createCheckpoint(params: {
  userId: string;
  toolId: string;
  baseVersionId: string | null;
  fields: EditorWorkingCopyFields;
  kind: CheckpointKind;
  label?: string | null;
  expiresAt?: number | null;
  now?: number;
}): Promise<CheckpointRecord> {
  const db = await getDb();
  const now = params.now ?? nowMs();
  const record: CheckpointRecord = {
    user_id: params.userId,
    tool_id: params.toolId,
    checkpoint_id: createCheckpointId(),
    kind: params.kind,
    label: params.label ?? null,
    base_version_id: params.baseVersionId,
    ...normalizeFields(params.fields),
    created_at: now,
    expires_at: params.expiresAt ?? null,
  };

  await db.add("checkpoints", record);
  return record;
}

export async function deleteCheckpoint(params: {
  userId: string;
  toolId: string;
  checkpointId: string;
}): Promise<void> {
  const db = await getDb();
  await db.delete("checkpoints", [params.userId, params.toolId, params.checkpointId]);
}

export async function trimAutoCheckpoints(params: {
  userId: string;
  toolId: string;
  cap: number;
}): Promise<void> {
  const db = await getDb();
  const tx = db.transaction("checkpoints", "readwrite");
  const store = tx.objectStore("checkpoints");
  const range = IDBKeyRange.bound(
    [params.userId, params.toolId, "auto", 0],
    [params.userId, params.toolId, "auto", Number.POSITIVE_INFINITY],
  );
  const records = await store.index("by_user_tool_kind_created_at").getAll(range);
  if (records.length > params.cap) {
    const sorted = [...records].sort((a, b) => a.created_at - b.created_at);
    const toDelete = sorted.slice(0, records.length - params.cap);
    for (const record of toDelete) {
      await store.delete(asCheckpointKey(record));
    }
  }
  await tx.done;
}
