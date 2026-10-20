/**
 * Exam workspace Öppna drawer: a blocked Öppna click gets feedback.
 *
 * Expected behavior (unit D1o):
 *   While the open exam has unsaved changes or another operation runs, a
 *   click (or Enter/Space) on another saved exam does not open it and tells
 *   the teacher to wait until the changes are saved. The feedback reuses the
 *   drawer's workspace-wide toast channel, the same channel an open failure
 *   reports through. Clicking the already open exam stays silent.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceUnreadableDocument } from "../../../api/examWorkspaceUnreadableFiles";
import { listUnreadableExamWorkspaceDocuments } from "../../../api/examWorkspaceUnreadableFiles";
import { useToastStore } from "../../../stores/toast";
import ExamWorkspaceOpenDrawer from "./ExamWorkspaceOpenDrawer.vue";
import ExamWorkspaceUnreadableFiles from "./ExamWorkspaceUnreadableFiles.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";

const unreadableApiMocks = vi.hoisted(() => ({
  downloadSavedExamFile: vi.fn(),
  listUnreadableExamWorkspaceDocuments: vi.fn(),
  removeSavedExamFile: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceUnreadableFiles", () => unreadableApiMocks);

const listUnreadableMock = vi.mocked(listUnreadableExamWorkspaceDocuments);

const BLOCKED_COPY = "Vänta tills ändringarna har sparats.";

const DOCUMENTS = [
  buildSavedExamSummary({ lineage_id: "lineage-a", title: "Prov A" }),
  buildSavedExamSummary({ lineage_id: "lineage-b", title: "Prov B" }),
];

function mountDrawer(options: { currentLineageId: string | null; isBusy: boolean; isDirty: boolean }) {
  setActivePinia(createPinia());
  return mount(ExamWorkspaceOpenDrawer, {
    props: {
      conversionError: null,
      conversionMessage: null,
      conversionProgress: null,
      currentExports: [],
      currentLineageId: options.currentLineageId,
      documents: DOCUMENTS,
      importBlocked: false,
      isBusy: options.isBusy,
      isConverting: false,
      isDirty: options.isDirty,
      notes: [],
      ordering: "newest",
      sourceFileError: null,
    },
    global: {
      plugins: [createPinia(), examWorkspaceProvidersPlugin()],
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

  it("tells the teacher to wait instead of opening while edits are unsaved", async () => {
    const wrapper = mountDrawer({ currentLineageId: "lineage-a", isBusy: false, isDirty: true });

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toContain(BLOCKED_COPY);
  });

  it("tells the teacher to wait instead of opening while another operation runs", async () => {
    const wrapper = mountDrawer({ currentLineageId: "lineage-a", isBusy: true, isDirty: false });

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toContain(BLOCKED_COPY);
  });

  it("opens without feedback when nothing blocks it", async () => {
    const wrapper = mountDrawer({ currentLineageId: "lineage-a", isBusy: false, isDirty: false });

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toEqual([["lineage-b"]]);
    expect(toastMessages()).toEqual([]);
  });

  it("stays silent when the open exam itself is clicked", async () => {
    const wrapper = mountDrawer({ currentLineageId: "lineage-a", isBusy: false, isDirty: true });

    await wrapper.get('[data-test="exam-workspace-open-lineage-a"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toEqual([]);
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
    const wrapper = mountDrawer({ currentLineageId: null, isBusy: false, isDirty: false });
    await flushPromises();

    await wrapper.get('[data-test="exam-workspace-open-lineage-a"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-unreadable-lineage-u"]').trigger("click");
    await flushPromises();

    expect(wrapper.emitted("open")).toEqual([["lineage-a"]]);
  });

  it("hides the empty hint when only an unreadable exam exists", async () => {
    listUnreadableMock.mockResolvedValue({ documents: [buildUnreadable()] });
    setActivePinia(createPinia());
    const wrapper = mount(ExamWorkspaceOpenDrawer, {
      props: {
        conversionError: null,
        conversionMessage: null,
        conversionProgress: null,
        currentExports: [],
        currentLineageId: null,
        documents: [],
        importBlocked: false,
        isBusy: false,
        isConverting: false,
        isDirty: false,
        notes: [],
        ordering: "newest",
        sourceFileError: null,
      },
      global: {
        plugins: [createPinia(), examWorkspaceProvidersPlugin()],
      },
    });
    await flushPromises();

    expect(wrapper.findComponent(ExamWorkspaceUnreadableFiles).exists()).toBe(true);
    expect(wrapper.text()).not.toContain("Inga sparade prov ännu.");
  });

  it("shows the empty hint when no readable or unreadable exam exists", async () => {
    setActivePinia(createPinia());
    const wrapper = mount(ExamWorkspaceOpenDrawer, {
      props: {
        conversionError: null,
        conversionMessage: null,
        conversionProgress: null,
        currentExports: [],
        currentLineageId: null,
        documents: [],
        importBlocked: false,
        isBusy: false,
        isConverting: false,
        isDirty: false,
        notes: [],
        ordering: "newest",
        sourceFileError: null,
      },
      global: {
        plugins: [createPinia(), examWorkspaceProvidersPlugin()],
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("Inga sparade prov ännu.");
  });

  it("renders no unreadable rows and fetches none in guest mode", async () => {
    setActivePinia(createPinia());
    const wrapper = mount(ExamWorkspaceOpenDrawer, {
      props: {
        conversionError: null,
        conversionMessage: null,
        conversionProgress: null,
        currentExports: [],
        currentLineageId: null,
        documents: [],
        importBlocked: false,
        isBusy: false,
        isConverting: false,
        isDirty: false,
        notes: [],
        ordering: "newest",
        sourceFileError: null,
      },
      global: {
        plugins: [
          createPinia(),
          examWorkspaceProvidersPlugin({ store: { ...serverExamWorkspaceStore, teacher: null } }),
        ],
      },
    });
    await flushPromises();

    expect(wrapper.findComponent(ExamWorkspaceUnreadableFiles).exists()).toBe(false);
    expect(listUnreadableMock).not.toHaveBeenCalled();
  });
});
