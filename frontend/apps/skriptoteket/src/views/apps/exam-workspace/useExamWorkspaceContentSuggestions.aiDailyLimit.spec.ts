/**
 * Exam workspace content suggestions under the daily AI limit.
 *
 * Expected behavior:
 *   A suggestion job that ends with ai_limit set (pool, user_share or
 *   usd_ceiling) marks the page-session limit, says the exact limit note in
 *   the drawer and fires no toast. A failure without ai_limit keeps today's
 *   toast behavior.
 */

import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import type {
  ExamWorkspaceContentSuggestions,
  NativeExamContentTag,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { ApiError } from "../../../api/client";
import { useAuthStore } from "../../../stores/auth";
import { useToastStore } from "../../../stores/toast";
import {
  AI_DAILY_LIMIT_NOTE,
  aiDailyLimitReached,
  resetAiDailyLimitForTests,
} from "./aiDailyLimit";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";
import {
  EXAM_WORKSPACE_CONTENT_POLL_MS,
  useExamWorkspaceContentSuggestions,
} from "./useExamWorkspaceContentSuggestions";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceContentSuggestions: vi.fn(),
  requestExamWorkspaceContentSuggestions: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

type Tag = NativeExamContentTag;

function tag(id: string, questionIds: string[]): Tag {
  return { id, origin: "suggested", question_ids: questionIds, text: id };
}

function documentWith(itemIds: string[], courseKey: string): NativeExamDocument {
  return {
    header: { course: { key: courseKey, name: courseKey }, tags: [] },
    items: itemIds.map((item_id) => ({ item_id })),
  } as unknown as NativeExamDocument;
}

function response(
  state: ExamWorkspaceContentSuggestions["state"],
  overrides: Partial<ExamWorkspaceContentSuggestions> = {},
): ExamWorkspaceContentSuggestions {
  return {
    course_key: "eng5",
    document_revision: 1,
    job_id: "job-1",
    lineage_id: "lineage-a",
    state,
    suggestions: [],
    ...overrides,
  };
}

function setup() {
  const state = {
    opening: { lineageId: "lineage-a" } as ExamWorkspaceOpening | null,
    document: documentWith(["q1", "q2"], "eng5") as NativeExamDocument | null,
    revision: 1 as number | null,
  };
  const setTags = vi.fn();
  const scope = effectScope();
  const content = scope.run(() =>
    useExamWorkspaceContentSuggestions({
      document: () => state.document,
      isOpen: (opening) => state.opening === opening,
      openExam: () => state.opening,
      savedRevision: () => state.revision,
      setTags,
      teacher: serverExamWorkspaceStore.teacher,
    }),
  );
  if (!content) {
    throw new Error("expected the content suggestions");
  }
  return { content, scope, setTags, state };
}

/** Start a job that is still running, then let the next poll deliver `final`. */
async function runJob(
  harness: ReturnType<typeof setup>,
  final: ExamWorkspaceContentSuggestions,
) {
  apiMocks.requestExamWorkspaceContentSuggestions.mockResolvedValue(response("running"));
  apiMocks.getExamWorkspaceContentSuggestions.mockResolvedValue(final);
  await harness.content.suggest();
  await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_CONTENT_POLL_MS);
}

function toastMessages(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  setActivePinia(createPinia());
  useAuthStore().user = {
    id: "teacher-a",
    email: "teacher-a@example.test",
    role: "admin",
    auth_provider: "local",
  };
  resetAiDailyLimitForTests();
  for (const mock of Object.values(apiMocks)) mock.mockReset();
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
});

describe("useExamWorkspaceContentSuggestions daily AI limit", () => {
  it.each(["pool", "user_share", "usd_ceiling"] as const)(
    "says the limit note and fires no toast for ai_limit %s",
    async (ai_limit) => {
      const harness = setup();
      await runJob(
        harness,
        response("failed", { ai_limit, message: AI_DAILY_LIMIT_NOTE }),
      );

      expect(aiDailyLimitReached.value).toBe(true);
      expect(harness.content.message.value).toBe(AI_DAILY_LIMIT_NOTE);
      expect(harness.setTags).not.toHaveBeenCalled();
      expect(toastMessages()).toEqual([]);
      expect(harness.content.busy.value).toBe(false);
    },
  );

  it("keeps the failure toast for a failure without ai_limit", async () => {
    const harness = setup();
    await runJob(harness, response("failed", { message: "Modellen svarade inte." }));

    expect(aiDailyLimitReached.value).toBe(false);
    expect(toastMessages()).toEqual(["Modellen svarade inte."]);
    expect(harness.content.message.value).toBeNull();
  });

  it("marks the limit without a toast when the request is refused with 429", async () => {
    const harness = setup();
    apiMocks.requestExamWorkspaceContentSuggestions.mockRejectedValue(
      new ApiError({
        code: "AI_DAILY_LIMIT_REACHED",
        message: AI_DAILY_LIMIT_NOTE,
        status: 429,
        details: { limit: "pool" },
      }),
    );

    await harness.content.suggest();

    expect(aiDailyLimitReached.value).toBe(true);
    expect(harness.content.message.value).toBe(AI_DAILY_LIMIT_NOTE);
    expect(toastMessages()).toEqual([]);
    expect(harness.content.busy.value).toBe(false);
  });

  it("still ticks a current result that carries no limit", async () => {
    const harness = setup();
    await runJob(
      harness,
      response("succeeded", { suggestions: [tag("t1", ["q1"])] }),
    );

    expect(aiDailyLimitReached.value).toBe(false);
    expect(harness.setTags).toHaveBeenCalledTimes(1);
  });
});
