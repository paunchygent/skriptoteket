/**
 * Exam workspace guest handoff rejection record (TASK-SKRIPT-41-02-05, U2a).
 *
 * Expected behavior:
 *   The in-memory record round-trips a rejection. The localStorage record
 *   round-trips a rejection; invalid JSON, a wrong shape, an extra key and
 *   an unknown reason all read as null; a throwing store never throws out.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createInMemoryGuestHandoffRejectionStorage,
  createLocalStorageGuestHandoffRejectionStorage,
  EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY,
} from "./examWorkspaceGuestHandoffRejection";

beforeEach(() => {
  localStorage.clear();
});

describe("in-memory guest handoff rejection storage", () => {
  it("round-trips a rejection and clears only its own cursor", () => {
    const storage = createInMemoryGuestHandoffRejectionStorage();
    expect(storage.read()).toBeNull();

    storage.write({ cursor: "cursor-1", reason: "permanent" });
    storage.clearIf("cursor-2");
    expect(storage.read()).toEqual({ cursor: "cursor-1", reason: "permanent" });

    storage.clearIf("cursor-1");
    expect(storage.read()).toBeNull();
  });
});

describe("localStorage guest handoff rejection storage", () => {
  it("round-trips a rejection", () => {
    const storage = createLocalStorageGuestHandoffRejectionStorage();
    expect(storage.read()).toBeNull();

    storage.write({ cursor: "cursor-1", reason: "vault_full" });
    expect(storage.read()).toEqual({ cursor: "cursor-1", reason: "vault_full" });

    expect(localStorage.getItem(EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY)).toBe(
      JSON.stringify({ cursor: "cursor-1", reason: "vault_full" }),
    );

    storage.clearIf("cursor-2");
    expect(storage.read()).toEqual({ cursor: "cursor-1", reason: "vault_full" });

    storage.clearIf("cursor-1");
    expect(storage.read()).toBeNull();
    expect(
      localStorage.getItem(EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY),
    ).toBeNull();
  });

  it("reads invalid JSON as null", () => {
    localStorage.setItem(EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY, "{broken");
    expect(createLocalStorageGuestHandoffRejectionStorage().read()).toBeNull();
  });

  it("reads a wrong shape as null", () => {
    localStorage.setItem(
      EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY,
      JSON.stringify({ cursor: "cursor-1" }),
    );
    expect(createLocalStorageGuestHandoffRejectionStorage().read()).toBeNull();

    localStorage.setItem(
      EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY,
      JSON.stringify({ reason: "permanent" }),
    );
    expect(createLocalStorageGuestHandoffRejectionStorage().read()).toBeNull();

    localStorage.setItem(
      EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY,
      JSON.stringify({ cursor: "", reason: "permanent" }),
    );
    expect(createLocalStorageGuestHandoffRejectionStorage().read()).toBeNull();
  });

  it("reads an extra key as null", () => {
    localStorage.setItem(
      EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY,
      JSON.stringify({ cursor: "cursor-1", extra: true, reason: "permanent" }),
    );
    expect(createLocalStorageGuestHandoffRejectionStorage().read()).toBeNull();
  });

  it("reads an unknown reason as null", () => {
    localStorage.setItem(
      EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY,
      JSON.stringify({ cursor: "cursor-1", reason: "transient" }),
    );
    expect(createLocalStorageGuestHandoffRejectionStorage().read()).toBeNull();
  });

  it("never throws out when the store throws", () => {
    const storage = createLocalStorageGuestHandoffRejectionStorage();
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("lagringen är blockerad");
    });
    expect(storage.read()).toBeNull();
    vi.restoreAllMocks();

    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("lagringen är full");
    });
    expect(() =>
      storage.write({ cursor: "cursor-1", reason: "permanent" }),
    ).not.toThrow();
    vi.restoreAllMocks();

    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
      throw new Error("lagringen är blockerad");
    });
    expect(() => storage.clearIf("cursor-1")).not.toThrow();
    vi.restoreAllMocks();
  });
});
