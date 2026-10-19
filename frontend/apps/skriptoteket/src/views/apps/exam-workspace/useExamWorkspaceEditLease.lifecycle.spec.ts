/**
 * Exam workspace edit lease, lifecycle: pagehide, dispose and lineage moves.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour item 7, decision D4,
 * unit K8):
 *   A closed tab releases its lease on `pagehide` with `keepalive`, so the
 *   release reaches the server after the page is gone and a waiting tab
 *   claims at once. Changing exams releases the old exam and claims the new
 *   one. A tab told the lease is lost turns read-only while its pending edit
 *   stays visible.
 */

import { flushPromises } from "@vue/test-utils";
import { effectScope, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useExamWorkspaceEditLease } from "./useExamWorkspaceEditLease";
import {
  createFakeLeaseServer,
  LINEAGE,
  OTHER_LINEAGE,
  setupLease,
} from "./useExamWorkspaceEditLease.specSupport";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useExamWorkspaceEditLease lifecycle", () => {
  it("releases on pagehide so a waiting tab claims at once", async () => {
    const fake = createFakeLeaseServer();
    const release = vi.spyOn(fake.server, "release");
    const first = setupLease(fake, { tabId: "tab-a" });
    const second = setupLease(fake, { tabId: "tab-b" });
    try {
      await flushPromises();
      window.dispatchEvent(new Event("pagehide"));
      await flushPromises();
      // The unload release must survive the page teardown, so it goes out
      // with `keepalive`; a plain fetch is cancelled and the lease lingers.
      expect(release).toHaveBeenCalledWith(LINEAGE, "tab-a", { keepalive: true });

      const taking = second.lease.requestTakeover();
      await taking;
      expect(second.lease.readOnly.value).toBe(false);
    } finally {
      first.stop();
      second.stop();
    }
  });

  it("releases the old exam and claims the new one when the lineage changes", async () => {
    const fake = createFakeLeaseServer();
    const release = vi.spyOn(fake.server, "release");
    const claim = vi.spyOn(fake.server, "claim");
    const scope = effectScope();
    const lineage = ref<string | null>(LINEAGE);
    const lease = scope.run(() =>
      useExamWorkspaceEditLease({
        isGuest: () => false,
        lineageId: () => lineage.value,
        onAcquired: () => Promise.resolve(),
        onTakeoverRequested: () => Promise.resolve(),
        server: fake.server,
        tabId: "tab-a",
      }),
    )!;
    try {
      await flushPromises();
      expect(lease.readOnly.value).toBe(false);
      lineage.value = OTHER_LINEAGE;
      await flushPromises();
      expect(release).toHaveBeenCalledWith(LINEAGE, "tab-a");
      expect(claim).toHaveBeenCalledWith(OTHER_LINEAGE, "tab-a");
      expect(lease.readOnly.value).toBe(false);

      lineage.value = null;
      await flushPromises();
      expect(release).toHaveBeenCalledWith(OTHER_LINEAGE, "tab-a");
      expect(lease.readOnly.value).toBe(true);
    } finally {
      scope.stop();
    }
  });

  it("turns read-only when told the lease is lost, keeping the pending edit", async () => {
    const fake = createFakeLeaseServer();
    const first = setupLease(fake, { tabId: "tab-a" });
    try {
      await flushPromises();
      expect(first.lease.readOnly.value).toBe(false);
      first.lease.noteLostLease();
      expect(first.lease.readOnly.value).toBe(true);
      expect(first.flushed).toEqual([]);
      expect(first.acquired).toEqual([]);
    } finally {
      first.stop();
    }
  });
});
