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

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceAnswerKeySuggestionsStatus,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useAuthStore } from "../../../stores/auth";
import { useToastStore } from "../../../stores/toast";
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import {
  aiDailyLimit,
  aiDailyLimitReached,
  aiLimitNote,
  resetAiDailyLimitForTests,
} from "../../../composables/aiDailyLimit";
import { useExamWorkspaceEnrichment } from "./useExamWorkspaceEnrichment";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";
import type { ExamWorkspaceTeacherServices } from "./examWorkspaceStore";
import type { AiDailyLimit } from "../../../composables/aiDailyLimit";

const requestLimits: AiDailyLimit[] = ["pool", "user_share"];

function limitStatus(
  ai_limit: AiDailyLimit | null,
): ExamWorkspaceAnswerKeySuggestionsStatus {
  return {
    job_id: "job-1",
    lineage_id: "lineage-a",
    state: "failed",
    ai_limit,
    message: ai_limit === null ? null : aiLimitNote(ai_limit),
    suggestions: [],
  };
}

function savedDocument(): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000013",
    header: { tags: [] },
    instructions: [],
    items: [buildFreeTextItem(1)],
    origin: { kind: "created" },
    parents: [],
    revision: 1,
    schema_version: "native_exam_document_v11",
    title: "Prov 1",
  };
}

/** Any teacher call the enrichment path is not meant to make fails loudly. */
const unexpectedTeacherCall = (): Promise<never> =>
  Promise.reject(new Error("unexpected teacher service call"));

function setup(requestImpl: () => Promise<ExamWorkspaceAnswerKeySuggestionsStatus>) {
  const opening: ExamWorkspaceOpening = { lineageId: "lineage-a" };
  const teacher: ExamWorkspaceTeacherServices = {
    createExamWorkspaceBlank: unexpectedTeacherCall,
    listExamWorkspaceDocuments: unexpectedTeacherCall,
    importExamWorkspaceDocument: unexpectedTeacherCall,
    getExamWorkspaceConversionStatus: unexpectedTeacherCall,
    importExamWorkspaceDigiExam: unexpectedTeacherCall,
    importExamWorkspaceQti: unexpectedTeacherCall,
    copyExamWorkspaceDocument: unexpectedTeacherCall,
    saveExamWorkspaceExport: unexpectedTeacherCall,
    retryExamWorkspaceItem: unexpectedTeacherCall,
    requestExamWorkspaceAnswerKeySuggestions: vi.fn(requestImpl),
    getExamWorkspaceAnswerKeySuggestions: unexpectedTeacherCall,
    findExamWorkspaceAnswerKeySuggestions: unexpectedTeacherCall,
    requestExamWorkspaceContentSuggestions: unexpectedTeacherCall,
    getExamWorkspaceContentSuggestions: unexpectedTeacherCall,
    getExamCourseContent: unexpectedTeacherCall,
    updateExamListOrdering: unexpectedTeacherCall,
    renameVaultFile: unexpectedTeacherCall,
    importExamWorkspaceGuestDraft: unexpectedTeacherCall,
    fetchExamWorkspacePrintPreview: unexpectedTeacherCall,
  };
  const scope = effectScope();
  const enrichment = scope.run(() =>
    useExamWorkspaceEnrichment({
      applySuggestions: () => undefined,
      document: ref<NativeExamDocument | null>(savedDocument()),
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
  ] satisfies Array<[AiDailyLimit, string]>)(
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

  it.each(requestLimits)(
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
