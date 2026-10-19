/**
 * "Föreslå innehåll" results belong to the exam opening, the saved revision and
 * the course that were in front of the teacher when the job started
 * (TASK-SKRIPT-40-04-03, review finding F8).
 *
 * Expected behavior:
 *   A result for another opening is dropped silently. A result for a changed
 *   revision or course writes no tags and says so in the drawer. A current
 *   result ticks only suggestions that still cite questions of the open copy.
 */

import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import type {
  ExamWorkspaceContentSuggestions,
  NativeExamContentTag,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useAuthStore } from "../../../stores/auth";
import { useToastStore } from "../../../stores/toast";
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

const STALE_COPY = "Provet ändrades medan innehållet föreslogs. Föreslå innehåll igen.";

/** Seed the signed-in actor the AI gate reads (TASK-SKRIPT-REP-0044 L3). */
function signInAs(role: "user" | "contributor" | "admin" | "superuser"): void {
  useAuthStore().user = { id: "teacher-a", email: "teacher-a@example.test", role, auth_provider: "local" };
}

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
  if (!content) throw new Error("expected the composable");
  return { content, scope, setTags, state };
}

/** Start a job that is still running, then let the next poll deliver `final`. */
async function runJob(
  harness: ReturnType<typeof setup>,
  final: ExamWorkspaceContentSuggestions,
  whileRunning: () => void = () => {},
) {
  apiMocks.requestExamWorkspaceContentSuggestions.mockResolvedValue(response("running"));
  apiMocks.getExamWorkspaceContentSuggestions.mockResolvedValue(final);
  await harness.content.suggest();
  whileRunning();
  await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_CONTENT_POLL_MS);
}

function toastMessages(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  setActivePinia(createPinia());
  signInAs("admin");
  for (const mock of Object.values(apiMocks)) mock.mockReset();
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
});

describe("useExamWorkspaceContentSuggestions", () => {
  it("ticks the suggestions of a current result", async () => {
    const harness = setup();
    await runJob(harness, response("succeeded", { suggestions: [tag("t1", ["q1"])] }));
    expect(harness.setTags).toHaveBeenCalledTimes(1);
    expect(harness.setTags.mock.calls[0][0]).toEqual([tag("t1", ["q1"])]);
    expect(harness.content.busy.value).toBe(false);
    expect(harness.content.message.value).toBeNull();
  });

  it("drops a result silently when another exam opened while the job ran", async () => {
    const harness = setup();
    await runJob(harness, response("succeeded", { suggestions: [tag("t1", ["q1"])] }), () => {
      harness.state.opening = { lineageId: "lineage-a" };
    });
    expect(harness.setTags).not.toHaveBeenCalled();
    expect(harness.content.message.value).toBeNull();
    expect(toastMessages()).toEqual([]);
    expect(harness.content.busy.value).toBe(false);
  });

  it("does not toast a failure for an opening that is gone", async () => {
    const harness = setup();
    await runJob(harness, response("failed"), () => {
      harness.state.opening = null;
    });
    expect(toastMessages()).toEqual([]);
    expect(harness.content.busy.value).toBe(false);
  });

  it("toasts a failure while the opening is still open", async () => {
    const harness = setup();
    await runJob(harness, response("failed", { message: "Modellen svarade inte." }));
    expect(toastMessages()).toEqual(["Modellen svarade inte."]);
    expect(harness.setTags).not.toHaveBeenCalled();
  });

  it("writes no tags when a save changed the revision during the job", async () => {
    const harness = setup();
    await runJob(harness, response("succeeded", { suggestions: [tag("t1", ["q1"])] }), () => {
      harness.state.revision = 2;
    });
    expect(harness.setTags).not.toHaveBeenCalled();
    expect(harness.content.message.value).toBe(STALE_COPY);
    expect(toastMessages()).toEqual([]);
  });

  it("writes no tags when the course changed during the job", async () => {
    const harness = setup();
    await runJob(harness, response("succeeded", { suggestions: [tag("t1", ["q1"])] }), () => {
      harness.state.document = documentWith(["q1", "q2"], "mat1");
    });
    expect(harness.setTags).not.toHaveBeenCalled();
    expect(harness.content.message.value).toBe(STALE_COPY);
  });

  it("removes deleted question ids and drops suggestions that cite only deleted questions", async () => {
    const harness = setup();
    await runJob(
      harness,
      response("succeeded", {
        suggestions: [tag("t1", ["q1", "q2"]), tag("t2", ["q2"])],
      }),
      () => {
        harness.state.document = documentWith(["q1"], "eng5");
      },
    );
    expect(harness.setTags).toHaveBeenCalledTimes(1);
    expect(harness.setTags.mock.calls[0][0]).toEqual([tag("t1", ["q1"])]);
  });

  it("says nothing was found when every cited question is gone", async () => {
    const harness = setup();
    await runJob(harness, response("succeeded", { suggestions: [tag("t2", ["q2"])] }), () => {
      harness.state.document = documentWith(["q1"], "eng5");
    });
    expect(harness.setTags).not.toHaveBeenCalled();
    expect(harness.content.message.value).toBe(
      "Inget centralt innehåll kunde föreslås för provets frågor.",
    );
  });
});

describe("useExamWorkspaceContentSuggestions admin gate (TASK-SKRIPT-REP-0044 L3)", () => {
  it.each(["user", "contributor"] as const)(
    "sends no request and stays idle for role %s",
    async (role) => {
      signInAs(role);
      const harness = setup();
      await harness.content.suggest();

      expect(apiMocks.requestExamWorkspaceContentSuggestions).not.toHaveBeenCalled();
      expect(apiMocks.getExamWorkspaceContentSuggestions).not.toHaveBeenCalled();
      expect(harness.content.busy.value).toBe(false);
    },
  );

  it("sends the request for an admin", async () => {
    signInAs("admin");
    const harness = setup();
    apiMocks.requestExamWorkspaceContentSuggestions.mockResolvedValue(response("running"));
    apiMocks.getExamWorkspaceContentSuggestions.mockResolvedValue(response("succeeded"));

    await harness.content.suggest();

    expect(apiMocks.requestExamWorkspaceContentSuggestions).toHaveBeenCalledTimes(1);
    expect(apiMocks.requestExamWorkspaceContentSuggestions).toHaveBeenCalledWith("lineage-a");
  });
});
