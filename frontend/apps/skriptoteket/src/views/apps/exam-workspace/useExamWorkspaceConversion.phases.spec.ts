/**
 * The import names the phase it is in and counts the seconds spent in it
 * (TASK-SKRIPT-39-04-23). The phase line and the m:ss clock follow the status
 * poll's lifecycle: the clock starts with the followed conversion and every
 * way of ending the poll (finish, switching exam, disposal) ends it too.
 */

import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useAuthStore } from "../../../stores/auth";
import { IMPORT_FAILURE_COPY } from "./examWorkspaceConversionShared";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { createSyncFence } from "./examWorkspaceSyncFence";
import {
  useExamWorkspaceConversion,
  type ExamWorkspaceConversionBinding,
} from "./useExamWorkspaceConversion";

const api = vi.hoisted(() => ({
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDigiExam: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceQti: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => ({ ...api }));

const NOW = Date.parse("2026-10-22T10:00:00Z");

type Phase = ExamWorkspaceConversionStatus["phase"];

function running(
  phase: Phase,
  secondsAgo: number,
  counts: { done: number; received: number; total: number } = { done: 0, received: 0, total: 0 },
): ExamWorkspaceConversionStatus {
  return {
    job_id: "job-1",
    lineage_id: "lineage-1",
    state: "running",
    error_message: null,
    summary: null,
    document_revision: null,
    phase,
    phase_started_at: phase === null ? null : new Date(NOW - secondsAgo * 1000).toISOString(),
    questions_total: counts.total,
    questions_done: counts.done,
    questions_received: counts.received,
    units: [],
  };
}

function succeeded(): ExamWorkspaceConversionStatus {
  return { ...running(null, 0), state: "succeeded" };
}

function binding(): ExamWorkspaceConversionBinding {
  const fence = createSyncFence();
  return {
    isDirty: ref(false),
    serverDocument: ref<NativeExamDocument | null>(null),
    summary: ref<ExamWorkspaceDocumentSummary | null>(null),
    workspaceDocument: ref<NativeExamDocument | null>(null),
    beginDocumentRead: () => (response) => response,
    applyResponse: vi.fn(),
    getFence: () => fence,
    isCurrent: (token) => fence.isCurrent(token),
    isSaving: () => false,
    noteImportStarted: vi.fn(),
    store: serverExamWorkspaceStore,
    tabId: () => "20000000-0000-4000-8000-000000000001",
  };
}

const scopes: Array<{ stop: () => void }> = [];

/** An admin's conversion composable inside its own scope, ready to import. */
function startConversion() {
  setActivePinia(createPinia());
  useAuthStore().user = {
    id: "teacher-1",
    email: "teacher@example.test",
    role: "admin",
    auth_provider: "local",
  };
  const scope = effectScope();
  scopes.push(scope);
  const conversion = scope.run(() =>
    useExamWorkspaceConversion(() => false, binding(), async () => "installed"),
  );
  if (!conversion) throw new Error("conversion did not start");
  return { conversion, scope };
}

/** Follow an admin's Word import whose first status is `first`; later polls answer `first` until changed. */
async function followImport(first: ExamWorkspaceConversionStatus) {
  api.importExamWorkspaceDocument.mockResolvedValue(first);
  api.getExamWorkspaceConversionStatus.mockResolvedValue(first);
  const { conversion, scope } = startConversion();
  await conversion.importDocument(new File(["prov"], "Prov.docx"), null);
  return { conversion, scope };
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(NOW);
  for (const mock of Object.values(api)) mock.mockReset();
});

afterEach(() => {
  for (const scope of scopes.splice(0)) scope.stop();
  vi.useRealTimers();
});

describe("conversion phase line", () => {
  it.each<[Exclude<Phase, null>, string]>([
    ["reading", "Läser filen"],
    ["finding", "Hittar frågorna"],
    ["sorting", "Sorterar frågorna efter typ"],
    ["converting", "Konverterar frågorna"],
  ])("names the %s phase as %s", async (phase, copy) => {
    const { conversion } = await followImport(running(phase, 2));

    expect(conversion.isConverting.value).toBe(true);
    expect(conversion.conversionMessage.value).toBe(copy);
  });

  it("counts received AI output before the first saved revision", async () => {
    const first = running("converting", 5, { done: 0, received: 2, total: 9 });
    const { conversion } = await followImport(first);

    expect(first.document_revision).toBeNull();
    expect(conversion.conversionMessage.value).toBe("AI-svar mottagna för 2 av 9 frågor.");
    expect(conversion.conversionProgress.value).toEqual({ received: 2, total: 9 });
    expect(api.getExamWorkspaceDocument).not.toHaveBeenCalled();

    api.getExamWorkspaceConversionStatus.mockResolvedValue({ ...first, questions_received: 5 });
    await vi.advanceTimersByTimeAsync(3000);

    expect(conversion.conversionMessage.value).toBe("AI-svar mottagna för 5 av 9 frågor.");
    expect(conversion.conversionStatus.value?.questions_done).toBe(0);
    expect(conversion.conversionStatus.value?.document_revision).toBeNull();
    expect(api.getExamWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("keeps polling and the elapsed clock running when every question has received output", async () => {
    const { conversion } = await followImport(
      running("converting", 5, { done: 0, received: 3, total: 3 }),
    );

    expect(conversion.conversionMessage.value).toBe("AI-svar mottagna för 3 av 3 frågor.");
    expect(conversion.conversionProgress.value).toEqual({ received: 3, total: 3 });
    expect(conversion.isConverting.value).toBe(true);
    expect(conversion.conversionElapsed.value).toBe("0:05");
    await vi.advanceTimersByTimeAsync(3000);
    expect(conversion.isConverting.value).toBe(true);
    expect(conversion.conversionElapsed.value).toBe("0:08");
    expect(api.getExamWorkspaceConversionStatus).toHaveBeenCalledTimes(2);
  });

  it("ends a successful job without raising receipt to the saved question count", async () => {
    const { conversion } = await followImport(
      running("converting", 5, { done: 0, received: 2, total: 3 }),
    );
    api.getExamWorkspaceConversionStatus.mockResolvedValue({
      ...running(null, 0, { done: 3, received: 2, total: 3 }),
      state: "succeeded",
    });
    await vi.advanceTimersByTimeAsync(3000);

    expect(conversion.isConverting.value).toBe(false);
    expect(conversion.conversionStatus.value?.questions_received).toBe(2);
    expect(conversion.conversionStatus.value?.questions_done).toBe(3);
    expect(conversion.conversionProgress.value).toBeNull();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("shows no count and no bar before the converting phase", async () => {
    const { conversion } = await followImport(running("sorting", 5, { done: 0, received: 0, total: 9 }));

    expect(conversion.conversionMessage.value).toBe("Sorterar frågorna efter typ");
    expect(conversion.conversionProgress.value).toBeNull();
  });

  it("shows received output and no clock while the phase is null", async () => {
    const { conversion } = await followImport(running(null, 0, { done: 1, received: 2, total: 3 }));

    expect(conversion.conversionMessage.value).toBe("AI-svar mottagna för 2 av 3 frågor.");
    expect(conversion.conversionElapsed.value).toBeNull();
  });

  it("keeps the old queued copy while the phase is null and nothing is counted", async () => {
    const { conversion } = await followImport(running(null, 0));

    expect(conversion.conversionMessage.value).toBe("Konverterar provet …");
    expect(conversion.conversionElapsed.value).toBeNull();
  });
});

describe("conversion elapsed clock", () => {
  it("shows the time in the phase as m:ss and ticks every second", async () => {
    const { conversion } = await followImport(running("reading", 7));
    expect(conversion.conversionElapsed.value).toBe("0:07");

    await vi.advanceTimersByTimeAsync(1000);
    expect(conversion.conversionElapsed.value).toBe("0:08");

    await vi.advanceTimersByTimeAsync(1000);
    expect(conversion.conversionElapsed.value).toBe("0:09");
  });

  it.each<[number, string]>([
    [0, "0:00"],
    [59, "0:59"],
    [60, "1:00"],
    [112, "1:52"],
    [723, "12:03"],
  ])("formats %i seconds as %s", async (seconds, text) => {
    const { conversion } = await followImport(running("finding", seconds));

    expect(conversion.conversionElapsed.value).toBe(text);
  });

  it("restarts from the new phase's start time when the phase changes", async () => {
    const { conversion } = await followImport(running("reading", 20));
    expect(conversion.conversionElapsed.value).toBe("0:20");

    // The next poll (3 s) answers a new phase that began 1 s before the browser sees it.
    api.getExamWorkspaceConversionStatus.mockResolvedValue({
      ...running("finding", 0),
      phase_started_at: new Date(NOW + 2000).toISOString(),
    });
    await vi.advanceTimersByTimeAsync(3000);

    expect(conversion.conversionMessage.value).toBe("Hittar frågorna");
    expect(conversion.conversionElapsed.value).toBe("0:01");

    await vi.advanceTimersByTimeAsync(1000);
    expect(conversion.conversionElapsed.value).toBe("0:02");
  });

  it("shows 0:00, never a negative time, when the server's clock is ahead", async () => {
    const { conversion } = await followImport(running("reading", -30));
    expect(conversion.conversionElapsed.value).toBe("0:00");

    await vi.advanceTimersByTimeAsync(1000);
    expect(conversion.conversionElapsed.value).toBe("0:00");
  });

  it("shows no clock for a start time it cannot read", async () => {
    const { conversion } = await followImport({
      ...running("reading", 0),
      phase_started_at: "not a time",
    });

    expect(conversion.conversionElapsed.value).toBeNull();
  });

  it("stops the clock and leaves no timer when the conversion finishes", async () => {
    const { conversion } = await followImport(running("converting", 10, { done: 1, received: 1, total: 2 }));
    expect(vi.getTimerCount()).toBeGreaterThan(0);

    api.getExamWorkspaceConversionStatus.mockResolvedValue(succeeded());
    await vi.advanceTimersByTimeAsync(3000);

    expect(conversion.isConverting.value).toBe(false);
    expect(conversion.conversionElapsed.value).toBeNull();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("stops the clock when another exam is opened", async () => {
    const { conversion } = await followImport(running("sorting", 4));
    expect(vi.getTimerCount()).toBeGreaterThan(0);

    conversion.adoptConversion({ conversion: null });

    expect(conversion.isConverting.value).toBe(false);
    expect(conversion.conversionElapsed.value).toBeNull();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("stops the clock when the page scope is disposed", async () => {
    const { scope } = await followImport(running("sorting", 4));
    expect(vi.getTimerCount()).toBeGreaterThan(0);

    scope.stop();

    expect(vi.getTimerCount()).toBe(0);
  });

  it("keeps a single clock across polls", async () => {
    await followImport(running("reading", 1));

    await vi.advanceTimersByTimeAsync(9000);

    // One poll timer plus one clock interval, however many polls have run.
    expect(vi.getTimerCount()).toBe(2);
  });
});

describe("upload wait before the first status", () => {
  /** The import request stays pending until the test settles it. */
  function pendingImport(fileName: string) {
    let resolve: (status: ExamWorkspaceConversionStatus) => void = () => undefined;
    let reject: (reason: Error) => void = () => undefined;
    api.importExamWorkspaceDocument.mockReturnValue(
      new Promise<ExamWorkspaceConversionStatus>((res, rej) => {
        resolve = res;
        reject = rej;
      }),
    );
    const { conversion, scope } = startConversion();
    const done = conversion.importDocument(new File(["prov"], fileName), null);
    return { conversion, scope, done, resolve, reject };
  }

  it.each(["Prov.docx", "Prov.pdf"])(
    "says %s is uploading while the request is pending, then continues into the queued status",
    async (fileName) => {
      const { conversion, done, resolve } = pendingImport(fileName);
      await vi.advanceTimersByTimeAsync(0);

      expect(conversion.isImporting.value).toBe(true);
      expect(conversion.isConverting.value).toBe(false);
      expect(conversion.conversionMessage.value).toBe("Laddar upp filen");
      expect(conversion.conversionElapsed.value).toBeNull();
      expect(conversion.conversionProgress.value).toBeNull();

      api.getExamWorkspaceConversionStatus.mockResolvedValue(running(null, 0));
      resolve(running(null, 0));
      await done;

      expect(conversion.isConverting.value).toBe(true);
      expect(conversion.conversionMessage.value).toBe("Konverterar provet …");
    },
  );

  it("clears the upload message and shows the failure copy when the request fails", async () => {
    const { conversion, done, reject } = pendingImport("Prov.docx");
    await vi.advanceTimersByTimeAsync(0);
    expect(conversion.conversionMessage.value).toBe("Laddar upp filen");

    reject(new Error("network down"));
    await done;

    expect(conversion.isImporting.value).toBe(false);
    expect(conversion.isConverting.value).toBe(false);
    expect(conversion.conversionMessage.value).toBe(IMPORT_FAILURE_COPY);
  });

  it("clears the upload message when the page scope is disposed during the request", async () => {
    const { conversion, scope, done, resolve } = pendingImport("Prov.docx");
    await vi.advanceTimersByTimeAsync(0);
    expect(conversion.conversionMessage.value).toBe("Laddar upp filen");

    scope.stop();

    expect(conversion.isImporting.value).toBe(false);
    expect(conversion.conversionMessage.value).toBeNull();

    resolve(running(null, 0));
    await done;
    expect(conversion.isConverting.value).toBe(false);
  });
});
