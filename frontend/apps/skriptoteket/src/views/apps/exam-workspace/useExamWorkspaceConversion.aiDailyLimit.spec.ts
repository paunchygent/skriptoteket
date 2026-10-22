/**
 * Exam workspace DOCX conversion under the daily AI limit.
 *
 * Expected behavior:
 *   A conversion status that ends with ai_limit set marks the page-session
 *   limit and fires no toast; the note names the first refused limit (the
 *   user's own share, or the app's pool/ceiling). While the limit is marked,
 *   a Word import starts nothing and says that same note instead. A failure
 *   without ai_limit keeps today's behavior.
 */

import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, ref } from "vue";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceConversionStatus,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import type { AiDailyLimit } from "./aiDailyLimit";
import { useAuthStore } from "../../../stores/auth";
import { useToastStore } from "../../../stores/toast";
import {
  aiDailyLimit,
  aiDailyLimitNote,
  aiDailyLimitReached,
  aiLimitNote,
  markAiDailyLimit,
  resetAiDailyLimitForTests,
} from "./aiDailyLimit";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { createSyncFence } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceRouteOpenOutcome } from "./examWorkspaceReplacementTypes";
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

type Role = "admin";

const allLimits: AiDailyLimit[] = ["pool", "user_share", "usd_ceiling"];
const retryLimits: AiDailyLimit[] = ["pool", "user_share"];

function queuedStatus(): ExamWorkspaceConversionStatus {
  return {
    job_id: "job-1",
    lineage_id: "lineage-1",
    state: "queued",
    error_message: null,
    ai_limit: null,
    summary: null,
    document_revision: null,
    questions_total: 0,
    questions_done: 0,
    units: [],
  };
}

function limitStatus(
  ai_limit: AiDailyLimit | null,
): ExamWorkspaceConversionStatus {
  return {
    ...queuedStatus(),
    state: "failed",
    error_message: ai_limit === null ? null : aiLimitNote(ai_limit),
    ai_limit,
  };
}

function binding(): ExamWorkspaceConversionBinding {
  const fence = createSyncFence();
  return {
    isDirty: ref(false),
    serverDocument: ref<NativeExamDocument | null>(null),
    summary: ref(null),
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

function conversionFor(
  openImported: (lineageId: string) => Promise<ExamWorkspaceRouteOpenOutcome> = async () =>
    "installed",
) {
  setActivePinia(createPinia());
  useAuthStore().user = {
    id: "teacher-1",
    email: "teacher@example.test",
    role: "admin" satisfies Role,
    auth_provider: "local",
  };
  resetAiDailyLimitForTests();
  const scope = effectScope();
  scopes.push(scope);
  const conversion = scope.run(() => useExamWorkspaceConversion(() => false, binding(), openImported));
  if (!conversion) {
    throw new Error("conversion did not start");
  }
  return conversion;
}

function toastMessages(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
}

beforeEach(() => {
  for (const mock of Object.values(api)) mock.mockReset();
});

afterEach(() => {
  for (const scope of scopes.splice(0)) scope.stop();
});

describe("useExamWorkspaceConversion daily AI limit", () => {
  it.each(allLimits)(
    "marks the limit and fires no toast for ai_limit %s",
    async (ai_limit) => {
      const conversion = conversionFor();
      // The finished revision is behind, so the status applies without opening.
      api.importExamWorkspaceDocument.mockResolvedValue(queuedStatus());
      api.getExamWorkspaceConversionStatus.mockResolvedValue(limitStatus(ai_limit));

      await conversion.importDocument(new File(["prov"], "NO_Prov_HT25.docx"), null);

      expect(aiDailyLimitReached.value).toBe(true);
      expect(aiDailyLimit.value).toBe(ai_limit);
      expect(conversion.conversionStatus.value?.ai_limit).toBe(ai_limit);
      expect(conversion.conversionMessage.value).toBe(aiLimitNote(ai_limit));
      expect(aiDailyLimitNote.value).toBe(aiLimitNote(ai_limit));
      expect(toastMessages()).toEqual([]);
    },
  );

  it("keeps the first limit when a later refusal names another", async () => {
    const conversion = conversionFor();
    api.importExamWorkspaceDocument.mockResolvedValue(queuedStatus());
    api.getExamWorkspaceConversionStatus.mockResolvedValueOnce(limitStatus("user_share"));
    await conversion.importDocument(new File(["prov"], "NO_Prov_HT25.docx"), null);
    expect(aiDailyLimit.value).toBe("user_share");

    markAiDailyLimit("pool");
    expect(aiDailyLimit.value).toBe("user_share");
    expect(aiDailyLimitNote.value).toBe(aiLimitNote("user_share"));
  });

  it.each(retryLimits)(
    "marks the retry 429 limit %s without a toast",
    async (limit) => {
      const conversion = conversionFor();
      api.importExamWorkspaceDocument.mockResolvedValue(queuedStatus());
      api.getExamWorkspaceConversionStatus.mockRejectedValue(
        new ApiError({
          code: "AI_DAILY_LIMIT_REACHED",
          message: "refused",
          status: 429,
          details: { limit },
        }),
      );

      await conversion.importDocument(new File(["prov"], "NO_Prov_HT25.docx"), null);

      expect(aiDailyLimitReached.value).toBe(true);
      expect(aiDailyLimit.value).toBe(limit);
      expect(conversion.conversionError.value).toBe(aiLimitNote(limit));
      expect(toastMessages()).toEqual([]);
    },
  );

  it("starts no Word import while the limit is marked", async () => {
    const conversion = conversionFor();
    markAiDailyLimit("pool");

    await conversion.importDocument(new File(["prov"], "NO_Prov_HT25.docx"), null);

    expect(api.importExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(conversion.conversionError.value).toBe(aiLimitNote("pool"));
    expect(toastMessages()).toEqual([]);
    expect(conversion.isImporting.value).toBe(false);
  });

  it("still imports Word without a marked limit", async () => {
    const conversion = conversionFor();
    api.importExamWorkspaceDocument.mockResolvedValue(queuedStatus());
    // A queued status with no finished revision keeps polling; settle it as failed without a limit.
    api.getExamWorkspaceConversionStatus.mockResolvedValue({
      ...queuedStatus(),
      state: "failed",
      error_message: "Konverteringen misslyckades.",
    });

    await conversion.importDocument(new File(["prov"], "NO_Prov_HT25.docx"), null);

    expect(api.importExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(aiDailyLimitReached.value).toBe(false);
  });
});
