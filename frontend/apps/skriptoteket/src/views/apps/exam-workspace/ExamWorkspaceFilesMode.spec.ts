/** Course choice belongs to the open import panel and travels with either file input. */
import { createTestingPinia } from "@pinia/testing";
import { flushPromises, shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import ExamCourseCombobox from "./ExamCourseCombobox.vue";
import ExamWorkspaceFilesMode from "./ExamWorkspaceFilesMode.vue";

vi.mock("../../../api/examWorkspace", async (importOriginal) => ({
  ...await importOriginal<typeof import("../../../api/examWorkspace")>(),
  getExamCourseCatalog: vi.fn().mockResolvedValue({ courses: [] }),
}));

function panel(importBlocked = false) {
  return shallowMount(ExamWorkspaceFilesMode, {
    global: { plugins: [createTestingPinia({ createSpy: vi.fn })] },
    props: {
      compact: true,
      enrichmentDisabled: false,
      enrichmentLookupError: null,
      enrichmentMessage: null,
      exportChecklist: [],
      exportNotice: null,
      exportingTarget: null,
      hasDocument: false,
      importBlocked,
      isBusy: false,
      isDirty: false,
      notes: [],
      readiness: [],
      savedDocuments: [],
      sourceFileError: null,
    },
  });
}

describe("course selection at import", () => {
  it("emits the chosen course with a file chosen from the picker", async () => {
    const wrapper = panel();
    const picker = wrapper.getComponent(ExamCourseCombobox);
    picker.vm.$emit("update:modelValue", "SVESVE02");
    const file = new File(["exam"], "Svenska 2.docx");
    const input = wrapper.get('[data-test="exam-workspace-source-file-input"]');
    Object.defineProperty(input.element, "files", { value: [file], configurable: true });
    await input.trigger("change");
    expect(wrapper.emitted("selectFile")).toEqual([[file, "SVESVE02"]]);
  });

  it("drops without a course and without inventing a selection", async () => {
    const wrapper = panel();
    const file = new File(["exam"], "prov.docx");
    await wrapper.get('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
      dataTransfer: { files: [file] },
    });
    expect(wrapper.emitted("dropFiles")).toEqual([[[file], null]]);
  });

  it("forwards a chosen course on drop as well as on picker input", async () => {
    const wrapper = panel();
    wrapper.getComponent(ExamCourseCombobox).vm.$emit("update:modelValue", "GRGRSVE01/7-9");
    const file = new File(["exam"], "prov.docx");
    await wrapper.get('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
      dataTransfer: { files: [file] },
    });
    expect(wrapper.emitted("dropFiles")).toEqual([[[file], "GRGRSVE01/7-9"]]);
  });

  it("does not reuse a previous key after the teacher clears the optional course", async () => {
    const wrapper = panel();
    const picker = wrapper.getComponent(ExamCourseCombobox);
    picker.vm.$emit("update:modelValue", "SVESVE02");
    picker.vm.$emit("update:modelValue", null);
    const file = new File(["exam"], "prov.docx");
    await wrapper.get('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
      dataTransfer: { files: [file] },
    });
    expect(wrapper.emitted("dropFiles")).toEqual([[[file], null]]);
  });

  it("disables the course control during blocked import without clearing the pick", async () => {
    const wrapper = panel();
    const picker = wrapper.getComponent(ExamCourseCombobox);
    picker.vm.$emit("update:modelValue", "SVESVE02");
    await wrapper.setProps({ importBlocked: true });
    expect(picker.props("disabled")).toBe(true);
    expect(picker.props("modelValue")).toBe("SVESVE02");
    await wrapper.setProps({ importBlocked: false });
    expect(picker.props("disabled")).toBe(false);
    expect(picker.props("modelValue")).toBe("SVESVE02");
  });

  it("keeps the pick after a rejected file so the teacher can correct the file", async () => {
    const wrapper = panel();
    const picker = wrapper.getComponent(ExamCourseCombobox);
    picker.vm.$emit("update:modelValue", "SVESVE02");
    await wrapper.get('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
      dataTransfer: { files: [new File(["pdf"], "prov.pdf")] },
    });
    await wrapper.setProps({ sourceFileError: "Välj en .docx-fil." });
    await flushPromises();
    expect(picker.props("modelValue")).toBe("SVESVE02");
  });
});
