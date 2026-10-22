/**
 * Exam workspace content suggestions under the daily AI limit.
 *
 * Expected behavior:
 *   A suggestion job that ends with ai_limit set marks the page-session
 *   limit, says that limit's note in the drawer and fires no toast. A failure
 *   without ai_limit keeps today's toast behavior.
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
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import {
  aiDailyLimit,
  aiDailyLimitReached,
  aiLimitNote,
  resetAiDailyLimitForTests,
} from "../../../composables/aiDailyLimit";
import type { AiDailyLimit } from "../../../composables/aiDailyLimit";
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

const TRY_AGAIN_SENTENCE = "AI-hjälpen har många förfrågningar just nu. Försök igen om en stund.";

const requestLimits: AiDailyLimit[] = ["pool", "user_share"];

function tag(id: string, questionIds: string[]): Tag {
  return { id, origin: "suggested", question_ids: questionIds, text: id };
}

function documentWith(itemIds: string[], courseKey: string): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000011",
    header: { course: { key: courseKey, name: courseKey }, tags: [] },
    instructions: [],
    items: itemIds.map((item_id, index) => buildFreeTextItem(index + 1, { item_id })),
    origin: { kind: "created" },
    parents: [],
    revision: 1,
    schema_version: "native_exam_document_v11",
    title: courseKey,
  };
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
  const state: {
    opening: ExamWorkspaceOpening | null;
    document: NativeExamDocument;
    revision: number | null;
  } = {
    opening: { lineageId: "lineage-a" },
    document: documentWith(["q1", "q2"], "eng5"),
    revision: 1,
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
  it.each([
    ["pool", aiLimitNote("pool")],
    ["user_share", aiLimitNote("user_share")],
    ["usd_ceiling", aiLimitNote("usd_ceiling")],
  ] satisfies Array<[AiDailyLimit, string]>)(
    "says the limit note and fires no toast for ai_limit %s",
    async (ai_limit, note) => {
      const harness = setup();
      await runJob(
        harness,
        response("failed", { ai_limit, message: note }),
      );

      expect(aiDailyLimitReached.value).toBe(true);
      expect(aiDailyLimit.value).toBe(ai_limit);
      expect(harness.content.message.value).toBe(note);
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

  it.each(requestLimits)(
    "marks the request 429 limit %s without a toast",
    async (limit) => {
      const harness = setup();
      apiMocks.requestExamWorkspaceContentSuggestions.mockRejectedValue(
        new ApiError({
          code: "AI_DAILY_LIMIT_REACHED",
          message: "refused",
          status: 429,
          details: { limit },
        }),
      );

      await harness.content.suggest();

      expect(aiDailyLimitReached.value).toBe(true);
      expect(aiDailyLimit.value).toBe(limit);
      expect(harness.content.message.value).toBe(aiLimitNote(limit));
      expect(toastMessages()).toEqual([]);
      expect(harness.content.busy.value).toBe(false);
    },
  );

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

describe("useExamWorkspaceContentSuggestions busy AI door", () => {
  function tryAgainError(): ApiError {
    return new ApiError({
    code: "AI_TRY_AGAIN",
    message: TRY_AGAIN_SENTENCE,
    status: 429,
    details: { retry_after_seconds: 5 },
  });
  }

  it("says the sentence in the drawer for a request refused with AI_TRY_AGAIN and clears it on the next success", async () => {
    const harness = setup();
    apiMocks.requestExamWorkspaceContentSuggestions.mockRejectedValueOnce(tryAgainError());

    await harness.content.suggest();

    expect(harness.content.message.value).toBe(TRY_AGAIN_SENTENCE);
    expect(toastMessages()).toEqual([]);
    expect(aiDailyLimitReached.value).toBe(false);
    expect(harness.content.busy.value).toBe(false);

    await runJob(harness, response("succeeded", { suggestions: [tag("t1", ["q1"])] }));

    expect(harness.content.message.value).toBeNull();
    expect(harness.setTags).toHaveBeenCalledTimes(1);
    expect(aiDailyLimitReached.value).toBe(false);
  });

  it("says the sentence in the drawer for a poll refused with AI_TRY_AGAIN", async () => {
    const harness = setup();
    apiMocks.requestExamWorkspaceContentSuggestions.mockResolvedValue(response("running"));
    apiMocks.getExamWorkspaceContentSuggestions.mockRejectedValue(tryAgainError());

    await harness.content.suggest();
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_CONTENT_POLL_MS);

    expect(harness.content.message.value).toBe(TRY_AGAIN_SENTENCE);
    expect(toastMessages()).toEqual([]);
    expect(aiDailyLimitReached.value).toBe(false);
    expect(harness.content.busy.value).toBe(false);
  });

  it("toasts a failed job's own try-again sentence without a limit", async () => {
    const harness = setup();
    await runJob(harness, response("failed", { message: TRY_AGAIN_SENTENCE }));

    expect(toastMessages()).toEqual([TRY_AGAIN_SENTENCE]);
    expect(aiDailyLimitReached.value).toBe(false);
  });
});
