/**
 * Exam workspace editing session: clearing the course never loops autosave,
 * and a save outage collapses the backlog into one store of the newest copy.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14, ticks defect):
 *   - Clearing the course drops its Centralt innehåll ticks in the working
 *     copy at once (the backend keeps only `<course_key>:` tags, and none
 *     without a course), so the cleared copy stores exactly once: no
 *     normalisation loop, and the status reads Sparat.
 *   - While every store answers 429, each later edit flushes the newest
 *     working copy instead of replaying owed snapshots, so lifting the limit
 *     stores the final state in exactly one POST and no POST after the outage
 *     carries the stale course.
 *   - While those edits are unstored the save status reads Inte sparat, which
 *     is also what blocks the Öppna drawer, with the status's own reason.
 *   - Choosing the course that is already set creates no edit step and sends
 *     no store.
 *   - Any server normalisation of a store (not only tags) settles after one
 *     POST: the server's stored copy becomes the working copy.
 *
 * Transport doubles wrap the specSupport step store: one applies the backend
 * tag rule and echoes the normalised copy, one answers 429 while limited.
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Plugin } from "vue";

import { ApiError } from "../../../api/client";
import type {
  ExamCourseChoice,
  NativeExamContentTag,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import ExamWorkspaceOpenDrawer from "./ExamWorkspaceOpenDrawer.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import {
  EXAM_WORKSPACE_UNREADABLE_FILES_KEY,
  useExamWorkspaceUnreadableFiles,
} from "./useExamWorkspaceUnreadableFiles";
import { AUTOSAVE_FAILURE_COPY } from "./useExamWorkspaceSaveStatus";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";
import type { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import {
  exam,
  openEditing,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../api/examWorkspaceStructureCommands", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspaceStructureCommands")>()),
  changeExamWorkspaceItemType: api.changeExamWorkspaceItemType,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

type Editing = ReturnType<typeof useExamWorkspaceEditing>;

const realSetTimeout = globalThis.setTimeout;
const realTick = (): Promise<void> => new Promise<void>((resolve) => realSetTimeout(resolve, 0));
async function drain(turns = 400): Promise<void> {
  for (let i = 0; i < turns; i += 1) {
    await realTick();
  }
}

const COURSE: ExamCourseChoice = { key: "SVESVE02", name: "Svenska 2" };

function contentTag(id: string, text: string): NativeExamContentTag {
  return { id, origin: "teacher", question_ids: [], text };
}

function courseBaseline(): NativeExamDocument {
  const base = exam("Prov", 2);
  return {
    ...base,
    header: {
      ...base.header,
      course: COURSE,
      tags: [contentTag("SVESVE02:cen-1", "Centralt 1"), contentTag("SVESVE02:cen-2", "Centralt 2")],
    },
  };
}

function clearedBaseline(): NativeExamDocument {
  const base = exam("Prov", 2);
  return { ...base, header: { ...base.header, course: null, tags: [] } };
}

/** The backend rule, as NativeExamHeader._clear_previous_course_tags applies it. */
function backendRule(document: NativeExamDocument): NativeExamDocument {
  const key = document.header.course?.key ?? null;
  const tags =
    key === null ? [] : document.header.tags.filter((item) => item.id.startsWith(`${key}:`));
  return { ...document, header: { ...document.header, tags } };
}

type PostedRow = {
  course: string | null;
  tags: string[];
  status: number;
};

function rowOf(sent: NativeExamDocument, status: number): PostedRow {
  return {
    course: sent.header.course?.key ?? null,
    tags: sent.header.tags.map((item) => item.id),
    status,
  };
}

function lastRow(rows: PostedRow[]): PostedRow {
  const row = rows[rows.length - 1];
  if (row === undefined) {
    throw new Error("expected a store POST");
  }
  return row;
}

function workingCopy(editing: Editing): NativeExamDocument {
  const document = editing.workspaceDocument.value;
  if (document === null) {
    throw new Error("expected an open exam");
  }
  return document;
}

/** Wrap the step store with the backend tag rule; record every sent body. */
function installBackendRule(posts: PostedRow[]): void {
  const inner = api.storeExamWorkspaceUndoStep.getMockImplementation();
  if (inner === undefined) {
    throw new Error("expected the step store double from openEditing");
  }
  api.storeExamWorkspaceUndoStep.mockImplementation(
    async (
      lineage: string,
      request: { afterStepId: string | null; document: NativeExamDocument; expectedCursor: string },
    ) => {
      await realTick();
      posts.push(rowOf(request.document, 200));
      const stored = backendRule(request.document);
      return inner(lineage, { ...request, document: stored });
    },
  );
}

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
  stopScopes();
});

describe("clearing the course stores once and never re-stores", () => {
  it("clears SVESVE02 with two ticks in exactly one POST, then stays quiet", async () => {
    vi.useFakeTimers();
    const { editing, server } = await openEditing(api, courseBaseline());
    const posts: PostedRow[] = [];
    installBackendRule(posts);

    editing.setCourse(null);
    await drain();
    vi.advanceTimersByTime(60000);
    await drain();

    expect(posts.length).toBe(1);
    expect(workingCopy(editing).header.course).toBeNull();
    expect(workingCopy(editing).header.tags).toEqual([]);
    const stored = server.documents.get(server.state.cursor);
    if (stored === undefined) {
      throw new Error("expected the stored step");
    }
    expect(stored.header.course).toBeNull();
    expect(stored.header.tags).toEqual([]);
    expect(editing.history.saveText.value.startsWith("Sparat")).toBe(true);
  });

  it("choosing the course that is already set creates no edit step and sends no store", async () => {
    vi.useFakeTimers();
    const { editing } = await openEditing(api, courseBaseline());
    const posts: PostedRow[] = [];
    installBackendRule(posts);

    editing.setCourse({ key: "SVESVE02", name: "Svenska 2" });
    await drain();
    vi.advanceTimersByTime(60000);
    await drain();

    expect(posts.length).toBe(0);
    expect(editing.history.pending.value).toBe(false);
    expect(editing.history.saveText.value.startsWith("Sparat")).toBe(true);
  });

  it("any server normalisation of a store settles after one POST", async () => {
    vi.useFakeTimers();
    const { editing } = await openEditing(api, exam("Prov", 2));
    const posts: PostedRow[] = [];
    const inner = api.storeExamWorkspaceUndoStep.getMockImplementation();
    if (inner === undefined) {
      throw new Error("expected the step store double from openEditing");
    }
    api.storeExamWorkspaceUndoStep.mockImplementation(
      async (
        lineage: string,
        request: { afterStepId: string | null; document: NativeExamDocument; expectedCursor: string },
      ) => {
        await realTick();
        posts.push(rowOf(request.document, 200));
        const stored = { ...request.document, title: request.document.title.trim() };
        return inner(lineage, { ...request, document: stored });
      },
    );

    editing.setTitle("Ny titel ");
    vi.advanceTimersByTime(900);
    await drain();
    vi.advanceTimersByTime(60000);
    await drain();

    expect(posts.length).toBe(1);
    expect(workingCopy(editing).title).toBe("Ny titel");
    expect(editing.history.saveText.value.startsWith("Sparat")).toBe(true);
  });
});

describe("a save outage collapses the backlog into one store of the newest copy", () => {
  function installLimiter(posts: PostedRow[]): { lift: () => void } {
    const inner = api.storeExamWorkspaceUndoStep.getMockImplementation();
    if (inner === undefined) {
      throw new Error("expected the step store double from openEditing");
    }
    let limited = true;
    api.storeExamWorkspaceUndoStep.mockImplementation(
      async (
        lineage: string,
        request: { afterStepId: string | null; document: NativeExamDocument; expectedCursor: string },
      ) => {
        await realTick();
        if (limited) {
          posts.push(rowOf(request.document, 429));
          throw new ApiError({
            code: "TOO_MANY_REQUESTS",
            message: "För många förfrågningar.",
            status: 429,
          });
        }
        posts.push(rowOf(request.document, 200));
        const stored = backendRule(request.document);
        return inner(lineage, { ...request, document: stored });
      },
    );
    return {
      lift: () => {
        limited = false;
      },
    };
  }

  it("three edits during 429s store once with the final state and never replay course null", async () => {
    vi.useFakeTimers();
    const { editing } = await openEditing(api, clearedBaseline());
    const posts: PostedRow[] = [];
    const limiter = installLimiter(posts);

    editing.setCourse(COURSE);
    await drain();
    editing.setTags([contentTag("SVESVE02:cen-1", "Centralt 1")]);
    await drain();
    editing.setTags([
      contentTag("SVESVE02:cen-1", "Centralt 1"),
      contentTag("SVESVE02:cen-2", "Centralt 2"),
    ]);
    await drain();

    limiter.lift();
    vi.advanceTimersByTime(6000);
    await drain();

    const succeeded = posts.filter((row) => row.status === 200);
    expect(succeeded.length).toBe(1);
    const final = lastRow(succeeded);
    expect(final.course).toBe("SVESVE02");
    expect(final.tags).toEqual(["SVESVE02:cen-1", "SVESVE02:cen-2"]);
    expect(succeeded.some((row) => row.course === null)).toBe(false);
    expect(lastRow(posts)).toEqual(final);
    expect(posts.slice(0, -1).every((row) => row.status === 429)).toBe(true);
  });

  it("shows Inte sparat while the outage edits are unstored", async () => {
    vi.useFakeTimers();
    const { editing } = await openEditing(api, clearedBaseline());
    const posts: PostedRow[] = [];
    installLimiter(posts);

    editing.setCourse(COURSE);
    await drain();

    expect(editing.history.saveText.value).toBe("Inte sparat");
    expect(editing.history.saveStatus.value).toStrictEqual({
      state: "unsaved",
      detail: AUTOSAVE_FAILURE_COPY,
    });
  });

  it("the Öppna drawer blocks on the failed save with the status's own reason", async () => {
    vi.useFakeTimers();
    const { editing } = await openEditing(api, clearedBaseline());
    const posts: PostedRow[] = [];
    installLimiter(posts);

    editing.setCourse(COURSE);
    await drain();

    const status = editing.history.saveStatus.value;
    if (status.state !== "unsaved") {
      throw new Error("expected Inte sparat after the failed store");
    }
    setActivePinia(createPinia());
    const unreadable = useExamWorkspaceUnreadableFiles();
    const provideUnreadable: Plugin = {
      install(app) {
        app.provide(EXAM_WORKSPACE_UNREADABLE_FILES_KEY, unreadable);
      },
    };
    const wrapper = mount(ExamWorkspaceOpenDrawer, {
      props: {
        conversionError: null,
        conversionMessage: null,
        conversionProgress: null,
        currentExports: [],
        currentLineageId: "lineage-a",
        documents: [
          buildSavedExamSummary({ lineage_id: "lineage-a", title: "Prov A" }),
          buildSavedExamSummary({ lineage_id: "lineage-b", title: "Prov B" }),
        ],
        importBlocked: false,
        isBusy: false,
        isConverting: false,
        isDirty: true,
        isOpenBlockedByOtherOperation: false,
        notes: [],
        ordering: "newest",
        saveDetail: status.detail,
        saveState: "unsaved",
        sourceFileError: null,
      },
      global: {
        plugins: [createPinia(), examWorkspaceProvidersPlugin(), provideUnreadable],
      },
    });

    expect(wrapper.get('[data-test="exam-workspace-open-dirty-hint"]').text()).toContain(
      AUTOSAVE_FAILURE_COPY,
    );
    expect(wrapper.get('[data-test="exam-workspace-open-lineage-b"]').attributes("title")).toBe(
      AUTOSAVE_FAILURE_COPY,
    );
    toast.failure.mockClear();

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toast.failure).toHaveBeenCalledTimes(1);
    expect(toast.failure).toHaveBeenCalledWith(AUTOSAVE_FAILURE_COPY);
  });
});
