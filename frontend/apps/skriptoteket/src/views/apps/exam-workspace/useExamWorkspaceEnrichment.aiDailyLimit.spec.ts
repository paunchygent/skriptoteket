/**
 * Exam workspace answer-key suggestions under the daily AI limit.
 *
 * Expected behavior:
 *   A suggestion status that ends with ai_limit set marks the page-session
 *   limit, shows that limit's note and fires no toast. A status without
 *   ai_limit keeps today's behavior. A transport failure with
 *   AI_DAILY_LIMIT_REACHED marks the refused limit without a toast; any other
 *   failure still toasts.
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
  aiDailyLimit,
  aiDailyLimitReached,
  aiLimitNote,
  resetAiDailyLimitForTests,
} from "./aiDailyLimit";
import { useExamWorkspaceEnrichment } from "./useExamWorkspaceEnrichment";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";
import type { ExamWorkspaceTeacherServices } from "./examWorkspaceStore";
import type { AiDailyLimit } from "./aiDailyLimit";

function limitStatus(
  ai_limit: AiDailyLimit | null,
): ExamWorkspaceAnswerKeySuggestionsStatus {
  return {
    job_id: "job-1",
    lineage_id: "lineage-a",
    state: "failed",
    ai_limit,
    message: ai_limit === null ? null : aiLimitNote(ai_limit),
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
  it.each([
    ["pool", aiLimitNote("pool")],
    ["user_share", aiLimitNote("user_share")],
    ["usd_ceiling", aiLimitNote("usd_ceiling")],
  ] as Array<[AiDailyLimit, string]>)(
    "marks the limit, shows the note and fires no toast for ai_limit %s",
    async (ai_limit, note) => {
      const { enrichment, scope } = setup(async () => limitStatus(ai_limit));
      await enrichment.requestSuggestionsForAll();

      expect(aiDailyLimitReached.value).toBe(true);
      expect(aiDailyLimit.value).toBe(ai_limit);
      expect(enrichment.enrichmentMessage.value).toBe(note);
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

  it.each(["pool", "user_share"] as const)(
    "marks the request 429 limit %s without a toast",
    async (limit) => {
      const { enrichment, scope } = setup(async () => {
        throw new ApiError({
          code: "AI_DAILY_LIMIT_REACHED",
          message: "refused",
          status: 429,
          details: { limit },
        });
      });
      await enrichment.requestSuggestionsForAll();

      expect(aiDailyLimitReached.value).toBe(true);
      expect(aiDailyLimit.value).toBe(limit);
      expect(useToastStore().toasts).toEqual([]);
      scope.stop();
    },
  );

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
