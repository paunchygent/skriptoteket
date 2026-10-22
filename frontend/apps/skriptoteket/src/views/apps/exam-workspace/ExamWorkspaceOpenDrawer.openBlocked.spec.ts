/**
 * Exam workspace Öppna drawer: a blocked Öppna click gets feedback.
 *
 * Expected behavior (CR1 C1/C2):
 *   While the open exam has a pending save, another operation runs, or the
 *   last save failed/was refused, a click (or Enter/Space) on another saved
 *   exam does not open it. The hint, the entry tooltip and the blocked-click
 *   toast all use one reason per state: the pending-save copy while an edit
 *   is not yet stored, the busy copy for another operation without a pending
 *   save, and the save status's own reason when it reads Inte sparat. The
 *   old "Spara det öppna provet …" copy is gone.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Plugin } from "vue";

import type { ExamWorkspaceUnreadableDocument } from "../../../api/examWorkspaceUnreadableFiles";
import { listUnreadableExamWorkspaceDocuments } from "../../../api/examWorkspaceUnreadableFiles";
import { useToastStore } from "../../../stores/toast";
import ExamWorkspaceOpenDrawer from "./ExamWorkspaceOpenDrawer.vue";
import ExamWorkspaceUnreadableFiles from "./ExamWorkspaceUnreadableFiles.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import {
  EXAM_WORKSPACE_UNREADABLE_FILES_KEY,
  useExamWorkspaceUnreadableFiles,
} from "./useExamWorkspaceUnreadableFiles";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";

const unreadableApiMocks = vi.hoisted(() => ({
  downloadSavedExamFile: vi.fn(),
  listUnreadableExamWorkspaceDocuments: vi.fn(),
  removeSavedExamFile: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceUnreadableFiles", () => unreadableApiMocks);

const listUnreadableMock = vi.mocked(listUnreadableExamWorkspaceDocuments);

const PENDING_COPY = "Vänta tills ändringarna har sparats.";
const BUSY_COPY = "En annan åtgärd pågår. Försök igen om en stund.";
const FAILED_REASON = "Ändringen sparades inte eftersom provet redigeras i den andra fliken.";

const DOCUMENTS = [
  buildSavedExamSummary({ lineage_id: "lineage-a", title: "Prov A" }),
  buildSavedExamSummary({ lineage_id: "lineage-b", title: "Prov B" }),
];

type SaveState = "saving" | "saved" | "unsaved";

function mountDrawer(options: {
  currentLineageId: string | null;
  isBusy: boolean;
  isDirty: boolean;
  saveState: SaveState;
  saveDetail: string | null;
}) {
  setActivePinia(createPinia());
  const unreadable = useExamWorkspaceUnreadableFiles();
  const provideUnreadable: Plugin = {
    install(app) {
      app.provide(EXAM_WORKSPACE_UNREADABLE_FILES_KEY, unreadable);
    },
  };
  return mount(ExamWorkspaceOpenDrawer, {
    props: {
      conversionError: null,
      conversionMessage: null,
      conversionElapsed: null,
      conversionProgress: null,
      currentExports: [],
      currentLineageId: options.currentLineageId,
      documents: DOCUMENTS,
      importBlocked: false,
      isBusy: options.isBusy,
      // Every busy case below is another operation, never the drawer's own import or conversion.
      isOpenBlockedByOtherOperation: options.isBusy,
      isConverting: false,
      isImporting: false,
      isDirty: options.isDirty,
      notes: [],
      ordering: "newest",
      saveDetail: options.saveDetail,
      saveState: options.saveState,
      sourceFileError: null,
    },
    global: {
      plugins: [createPinia(), examWorkspaceProvidersPlugin(), provideUnreadable],
    },
  });
}

function toastMessages(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
}

describe("ExamWorkspaceOpenDrawer blocked open", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    listUnreadableMock.mockResolvedValue({ documents: [] });
  });

  it("shows the pending-save copy in the hint, tooltip and toast while an edit is not yet stored", async () => {
    const wrapper = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: false,
      isDirty: true,
      saveDetail: null,
      saveState: "saving",
    });

    expect(wrapper.get('[data-test="exam-workspace-open-dirty-hint"]').text()).toContain(PENDING_COPY);
    expect(
      wrapper.get('[data-test="exam-workspace-open-lineage-b"]').attributes("title"),
    ).toBe(PENDING_COPY);

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toContain(PENDING_COPY);
  });

  it("shows the busy copy when only another operation runs", async () => {
    const wrapper = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: true,
      isDirty: false,
      saveDetail: null,
      saveState: "saved",
    });

    expect(wrapper.get('[data-test="exam-workspace-open-dirty-hint"]').text()).toContain(BUSY_COPY);
    expect(
      wrapper.get('[data-test="exam-workspace-open-lineage-b"]').attributes("title"),
    ).toBe(BUSY_COPY);

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toContain(BUSY_COPY);
  });

  it("shows the save status reason when the last save failed or was refused", async () => {
    const wrapper = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: false,
      isDirty: true,
      saveDetail: FAILED_REASON,
      saveState: "unsaved",
    });

    expect(wrapper.get('[data-test="exam-workspace-open-dirty-hint"]').text()).toContain(FAILED_REASON);
    expect(
      wrapper.get('[data-test="exam-workspace-open-lineage-b"]').attributes("title"),
    ).toBe(FAILED_REASON);

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toContain(FAILED_REASON);
  });

  it("opens without feedback when nothing blocks it", async () => {
    const wrapper = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: false,
      isDirty: false,
      saveDetail: null,
      saveState: "saved",
    });

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toEqual([["lineage-b"]]);
    expect(toastMessages()).toEqual([]);
  });

  it("stays silent when the open exam itself is clicked", async () => {
    const wrapper = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: false,
      isDirty: true,
      saveDetail: null,
      saveState: "saving",
    });

    await wrapper.get('[data-test="exam-workspace-open-lineage-a"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toEqual([]);
  });

  it("never shows the old save-the-open-exam copy", async () => {
    const blocked = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: false,
      isDirty: true,
      saveDetail: null,
      saveState: "saving",
    });
    expect(blocked.html()).not.toContain("Spara det öppna provet");
    blocked.unmount();

    const failed = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: false,
      isDirty: true,
      saveDetail: FAILED_REASON,
      saveState: "unsaved",
    });
    expect(failed.html()).not.toContain("Spara det öppna provet");
    failed.unmount();
  });
});

describe("ExamWorkspaceOpenDrawer unreadable saved exams", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    listUnreadableMock.mockResolvedValue({ documents: [] });
  });

  function buildUnreadable(
    overrides: Partial<ExamWorkspaceUnreadableDocument> = {},
  ): ExamWorkspaceUnreadableDocument {
    return {
      lineage_id: "lineage-u",
      name: "Gammalt prov.provdokument.zip",
      saved_at: "2026-10-11T08:00:00Z",
      title: "Gammalt prov",
      vault_file_id: "vault-u",
      ...overrides,
    };
  }

  it("opens the readable row but not the unreadable row", async () => {
    listUnreadableMock.mockResolvedValue({ documents: [buildUnreadable()] });
    const wrapper = mountDrawer({
      currentLineageId: null,
      isBusy: false,
      isDirty: false,
      saveDetail: null,
      saveState: "saved",
    });
    await flushPromises();

    await wrapper.get('[data-test="exam-workspace-open-lineage-a"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-unreadable-lineage-u"]').trigger("click");
    await flushPromises();

    expect(wrapper.emitted("open")).toEqual([["lineage-a"]]);
  });

  it("hides the empty hint when only an unreadable exam exists", async () => {
    listUnreadableMock.mockResolvedValue({ documents: [buildUnreadable()] });
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
        conversionElapsed: null,
        conversionProgress: null,
        currentExports: [],
        currentLineageId: null,
        documents: [],
        importBlocked: false,
        isBusy: false,
        isConverting: false,
        isImporting: false,
        isDirty: false,
        isOpenBlockedByOtherOperation: false,
        notes: [],
        ordering: "newest",
        saveDetail: null,
        saveState: "saved",
        sourceFileError: null,
      },
      global: {
        plugins: [createPinia(), examWorkspaceProvidersPlugin(), provideUnreadable],
      },
    });
    await flushPromises();

    expect(wrapper.findComponent(ExamWorkspaceUnreadableFiles).exists()).toBe(true);
    expect(wrapper.text()).not.toContain("Inga sparade prov ännu.");
  });

  it("shows the empty hint when no readable or unreadable exam exists", async () => {
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
        conversionElapsed: null,
        conversionProgress: null,
        currentExports: [],
        currentLineageId: null,
        documents: [],
        importBlocked: false,
        isBusy: false,
        isConverting: false,
        isImporting: false,
        isDirty: false,
        isOpenBlockedByOtherOperation: false,
        notes: [],
        ordering: "newest",
        saveDetail: null,
        saveState: "saved",
        sourceFileError: null,
      },
      global: {
        plugins: [createPinia(), examWorkspaceProvidersPlugin(), provideUnreadable],
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("Inga sparade prov ännu.");
  });

  it("renders no unreadable rows and fetches none in guest mode", async () => {
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
        conversionElapsed: null,
        conversionProgress: null,
        currentExports: [],
        currentLineageId: null,
        documents: [],
        importBlocked: false,
        isBusy: false,
        isConverting: false,
        isImporting: false,
        isDirty: false,
        isOpenBlockedByOtherOperation: false,
        notes: [],
        ordering: "newest",
        saveDetail: null,
        saveState: "saved",
        sourceFileError: null,
      },
      global: {
        plugins: [
          createPinia(),
          examWorkspaceProvidersPlugin({ store: { ...serverExamWorkspaceStore, teacher: null } }),
          provideUnreadable,
        ],
      },
    });
    await flushPromises();

    expect(wrapper.findComponent(ExamWorkspaceUnreadableFiles).exists()).toBe(false);
    expect(listUnreadableMock).not.toHaveBeenCalled();
  });
});
