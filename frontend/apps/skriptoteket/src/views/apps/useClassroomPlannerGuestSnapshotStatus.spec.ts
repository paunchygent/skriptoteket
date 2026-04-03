/**
 * Klassrumskartan guest snapshot status tests.
 *
 * These tests verify that the public-shell status controller keeps guest
 * storage lazy and only resolves the browser adapter when the guest flow is
 * actually enabled.
 */

import { mount } from "@vue/test-utils";
import { defineComponent, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";

import {
  useClassroomPlannerGuestSnapshotStatus,
} from "./useClassroomPlannerGuestSnapshotStatus";

function mountStatusHarness(options?: Parameters<typeof useClassroomPlannerGuestSnapshotStatus>[0]) {
  let exposedState: ReturnType<typeof useClassroomPlannerGuestSnapshotStatus> | null = null;

  const Harness = defineComponent({
    setup() {
      exposedState = useClassroomPlannerGuestSnapshotStatus(options);
      return () => null;
    },
  });

  mount(Harness);
  return {
    getState() {
      if (!exposedState) {
        throw new Error("Guest snapshot status harness did not expose state.");
      }
      return exposedState;
    },
  };
}

describe("useClassroomPlannerGuestSnapshotStatus", () => {
  it("does not construct guest storage when disabled", async () => {
    const guestStorageFactory = vi.fn(() => ({
      loadCurrentSnapshot: vi.fn(),
      saveSnapshot: vi.fn(),
      initializeEmptySnapshot: vi.fn(),
      clearCurrentSnapshot: vi.fn(),
    }));

    const harness = mountStatusHarness({
      enabled: false,
      guestStorageFactory,
    });
    await nextTick();

    expect(guestStorageFactory).not.toHaveBeenCalled();
    expect(harness.getState().status.value).toBe("idle");
  });

  it("loads the current snapshot when guest mode is enabled", async () => {
    const loadCurrentSnapshot = vi.fn(async () => ({
      status: "missing" as const,
      snapshot: null,
      summary: null,
    }));
    const guestStorageFactory = vi.fn(() => ({
      loadCurrentSnapshot,
      saveSnapshot: vi.fn(),
      initializeEmptySnapshot: vi.fn(),
      clearCurrentSnapshot: vi.fn(),
    }));

    const harness = mountStatusHarness({
      enabled: true,
      guestStorageFactory,
    });
    await nextTick();
    await Promise.resolve();

    expect(guestStorageFactory).toHaveBeenCalledOnce();
    expect(loadCurrentSnapshot).toHaveBeenCalledOnce();
    expect(harness.getState().status.value).toBe("missing");
  });
});
