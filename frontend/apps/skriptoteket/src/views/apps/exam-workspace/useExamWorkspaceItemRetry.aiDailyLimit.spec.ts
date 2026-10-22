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
import {
  aiDailyLimit,
  aiDailyLimitReached,
  aiLimitNote,
  resetAiDailyLimitForTests,
} from "./aiDailyLimit";
import { createSyncFence } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceTeacherServices } from "./examWorkspaceStore";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";
import { useExamWorkspaceItemRetry } from "./useExamWorkspaceItemRetry";

const RETRY_FAILURE_COPY = "Det gick inte att konvertera om frågan. Försök igen.";

function retryableDocument(): NativeExamDocument {
  return {
    revision: 1,
    items: [
      {
        item_id: "item_001",
        retry_source: { label_kind: "gap_fill" },
        review: { state: "review_required" },
      },
    ],
  } as unknown as NativeExamDocument;
}

function setup(retryImpl: (...args: never[]) => Promise<never>) {
  const fence = createSyncFence();
  const opening = { lineageId: "lineage-1" } as ExamWorkspaceOpening;
  const document = retryableDocument();
  const teacher = {
    retryExamWorkspaceItem: vi.fn(retryImpl),
  } as unknown as ExamWorkspaceTeacherServices;
  const scope = effectScope();
  const retry = scope.run(() =>
    useExamWorkspaceItemRetry({
      workspaceDocument: ref<NativeExamDocument | null>(document),
      serverDocument: ref<NativeExamDocument | null>(document),
      summary: ref({ lineage_id: "lineage-1" } as ExamWorkspaceDocumentSummary),
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
  it.each(["pool", "user_share"] as const)(
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
