/**
 * Exam workspace one-question retry under the daily AI limit.
 *
 * Expected behavior:
 *   A retry refused with HTTP 429 AI_DAILY_LIMIT_REACHED marks the refused
 *   limit for the page session and fires no toast. Any other failure keeps
 *   today's toast behavior.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, ref, shallowRef } from "vue";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
  NativeExamItemKind,
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
import type { AiDailyLimit } from "../../../composables/aiDailyLimit";
import { createSyncFence } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceTeacherServices } from "./examWorkspaceStore";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";
import { useExamWorkspaceItemRetry } from "./useExamWorkspaceItemRetry";

const RETRY_FAILURE_COPY = "Det gick inte att konvertera om frågan. Försök igen.";

const retryLimits: AiDailyLimit[] = ["pool", "user_share"];

function retryableDocument(): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000012",
    header: { tags: [] },
    instructions: [],
    items: [
      buildFreeTextItem(1, {
        retry_source: {
          chunks: [],
          context_chunks: [],
          key_chunks: [],
          label_kind: "gap_fill",
          owned_context_anchors: [],
        },
        review: {
          confidence: null,
          parse_origin: "deterministic",
          reasons: [],
          state: "review_required",
        },
      }),
    ],
    origin: { kind: "created" },
    parents: [],
    revision: 1,
    schema_version: "native_exam_document_v11",
    title: "Prov 1",
  };
}

/** Any teacher call the retry path is not meant to make fails loudly. */
const unexpectedTeacherCall = (): Promise<never> =>
  Promise.reject(new Error("unexpected teacher service call"));

function teacherServices(
  retryExamWorkspaceItem: ExamWorkspaceTeacherServices["retryExamWorkspaceItem"],
): ExamWorkspaceTeacherServices {
  return {
    createExamWorkspaceBlank: unexpectedTeacherCall,
    listExamWorkspaceDocuments: unexpectedTeacherCall,
    importExamWorkspaceDocument: unexpectedTeacherCall,
    getExamWorkspaceConversionStatus: unexpectedTeacherCall,
    importExamWorkspaceDigiExam: unexpectedTeacherCall,
    importExamWorkspaceQti: unexpectedTeacherCall,
    copyExamWorkspaceDocument: unexpectedTeacherCall,
    saveExamWorkspaceExport: unexpectedTeacherCall,
    retryExamWorkspaceItem,
    requestExamWorkspaceAnswerKeySuggestions: unexpectedTeacherCall,
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
}

function setup(retryImpl: () => Promise<never>) {
  const fence = createSyncFence();
  const opening: ExamWorkspaceOpening = { lineageId: "lineage-1" };
  const summary: ExamWorkspaceDocumentSummary = {
    course_key: null,
    lineage_id: "lineage-1",
    name: "Prov",
    saved_at: "2026-10-22T00:00:00Z",
    title: "Prov",
    vault_file_id: "vault-1",
    version: 1,
  };
  const document = retryableDocument();
  const teacher = teacherServices(vi.fn(retryImpl));
  const scope = effectScope();
  const retry = scope.run(() =>
    useExamWorkspaceItemRetry({
      workspaceDocument: ref<NativeExamDocument | null>(document),
      serverDocument: ref<NativeExamDocument | null>(document),
      summary: ref<ExamWorkspaceDocumentSummary | null>(summary),
      openExam: shallowRef(opening),
      operationBusy: ref(false),
      isBusy: () => false,
      getFence: () => fence,
      isCurrent: (token) => fence.isCurrent(token),
      teacher,
    }),
  );
  if (!retry) {
    throw new Error("expected the retry");
  }
  return { retry, scope, teacher };
}

function toastMessages(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
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

describe("useExamWorkspaceItemRetry daily AI limit", () => {
  it.each(retryLimits)(
    "marks the retry 429 limit %s and fires no toast",
    async (limit) => {
      const { retry, scope } = setup(async () => {
        throw new ApiError({
          code: "AI_DAILY_LIMIT_REACHED",
          message: "refused",
          status: 429,
          details: { limit },
        });
      });

      const applied = await retry.retryItem("item_001", "matching" satisfies NativeExamItemKind);

      expect(applied).toBe(false);
      expect(aiDailyLimitReached.value).toBe(true);
      expect(aiDailyLimit.value).toBe(limit);
      expect(aiLimitNote(limit)).not.toEqual("");
      expect(toastMessages()).toEqual([]);
      scope.stop();
    },
  );

  it("keeps the retry toast for a failure without the limit code", async () => {
    const { retry, scope } = setup(async () => {
      throw new ApiError({ code: "CONFLICT", message: "Konflikt.", status: 409 });
    });

    const applied = await retry.retryItem("item_001", "matching" satisfies NativeExamItemKind);

    expect(applied).toBe(false);
    expect(aiDailyLimitReached.value).toBe(false);
    expect(toastMessages()).toEqual(["Konflikt."]);
    scope.stop();
  });

  it("keeps the retry copy for a failure without a server message", async () => {
    const { retry, scope } = setup(async () => {
      throw new Error("network down");
    });

    await retry.retryItem("item_001", "matching" satisfies NativeExamItemKind);

    expect(aiDailyLimitReached.value).toBe(false);
    expect(toastMessages()).toEqual([RETRY_FAILURE_COPY]);
    scope.stop();
  });
});
