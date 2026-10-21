/**
 * Exam workspace answer-key suggestions under the daily AI limit.
 *
 * Expected behavior:
 *   A suggestion status that ends with ai_limit set (pool, user_share or
 *   usd_ceiling) marks the page-session limit, shows the exact limit note and
 *   fires no toast. A status without ai_limit keeps today's behavior. A
 *   transport failure with AI_DAILY_LIMIT_REACHED marks the limit without a
 *   toast; any other failure still toasts.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, ref } from "vue";
import type { Ref } from "vue";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceAnswerKeySuggestionItem,
  ExamWorkspaceAnswerKeySuggestionsStatus,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useAuthStore } from "../../../stores/auth";
import { useToastStore } from "../../../stores/toast";
import {
  AI_DAILY_LIMIT_NOTE,
  aiDailyLimitReached,
  resetAiDailyLimitForTests,
} from "./aiDailyLimit";
import { useExamWorkspaceEnrichment } from "./useExamWorkspaceEnrichment";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";
import type { ExamWorkspaceTeacherServices } from "./examWorkspaceStore";

function limitStatus(
  ai_limit: ExamWorkspaceAnswerKeySuggestionsStatus["ai_limit"],
): ExamWorkspaceAnswerKeySuggestionsStatus {
  return {
    job_id: "job-1",
    lineage_id: "lineage-a",
    state: "failed",
    ai_limit,
    message: AI_DAILY_LIMIT_NOTE,
    suggestions: [] as ExamWorkspaceAnswerKeySuggestionItem[],
  };
}

function setup(requestImpl: () => Promise<ExamWorkspaceAnswerKeySuggestionsStatus>) {
  const opening = { lineageId: "lineage-a" } as ExamWorkspaceOpening;
  const teacher = {
    requestExamWorkspaceAnswerKeySuggestions: vi.fn(requestImpl),
    getExamWorkspaceAnswerKeySuggestions: vi.fn(),
    findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  } as unknown as ExamWorkspaceTeacherServices;
  const scope = effectScope();
  const enrichment = scope.run(() =>
    useExamWorkspaceEnrichment({
      applySuggestions: () => undefined,
      document: ref({}) as Ref<NativeExamDocument | null>,
      isOpen: () => true,
      openExam: ref(opening),
      savedRevision: ref(1),
      teacher,
    }),
  );
  if (!enrichment) {
    throw new Error("expected the enrichment session");
  }
  return { enrichment, scope, teacher };
}

beforeEach(() => {
  setActivePinia(createPinia());
  useAuthStore().user = {
    id: "teacher-a",
    email: "teacher-a@example.test",
    role: "admin",
    auth_provider: "local",
  };
  resetAiDailyLimitForTests();
});

describe("useExamWorkspaceEnrichment daily AI limit", () => {
  it.each(["pool", "user_share", "usd_ceiling"] as const)(
    "marks the limit, shows the note and fires no toast for ai_limit %s",
    async (ai_limit) => {
      const { enrichment, scope } = setup(async () => limitStatus(ai_limit));
      await enrichment.requestSuggestionsForAll();

      expect(aiDailyLimitReached.value).toBe(true);
      expect(enrichment.enrichmentMessage.value).toBe(AI_DAILY_LIMIT_NOTE);
      expect(useToastStore().toasts).toEqual([]);
      scope.stop();
    },
  );

  it("keeps today's failure behavior for a status without ai_limit", async () => {
    const { enrichment, scope } = setup(async () => ({
      ...limitStatus(null),
      message: "Facitförslaget kunde inte hämtas just nu. Försök igen senare.",
    }));
    await enrichment.requestSuggestionsForAll();

    expect(aiDailyLimitReached.value).toBe(false);
    expect(enrichment.enrichmentMessage.value).toBe(
      "Facitförslaget kunde inte hämtas just nu. Försök igen senare.",
    );
    expect(useToastStore().toasts).toEqual([]);
    scope.stop();
  });

  it("marks the limit without a toast when the request is refused with 429", async () => {
    const { enrichment, scope } = setup(async () => {
      throw new ApiError({
        code: "AI_DAILY_LIMIT_REACHED",
        message: AI_DAILY_LIMIT_NOTE,
        status: 429,
        details: { limit: "pool" },
      });
    });
    await enrichment.requestSuggestionsForAll();

    expect(aiDailyLimitReached.value).toBe(true);
    expect(useToastStore().toasts).toEqual([]);
    scope.stop();
  });

  it("still toasts a transport failure without the limit code", async () => {
    const { enrichment, scope } = setup(async () => {
      throw new Error("network down");
    });
    await enrichment.requestSuggestionsForAll();

    expect(aiDailyLimitReached.value).toBe(false);
    expect(useToastStore().toasts.map((toast) => toast.message)).toEqual([
      "Det gick inte att begära facitförslag. Försök igen.",
    ]);
    scope.stop();
  });
});
