/** Metadata edits stay local; a separate rename confirms the vault record name. */
import { createTestingPinia } from "@pinia/testing";
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ExamWorkspaceMetadataDrawer from "./ExamWorkspaceMetadataDrawer.vue";

vi.mock("../../../api/examWorkspace", () => ({
  getExamCourseCatalog: vi.fn().mockResolvedValue({ courses: [] }),
}));
const rename = vi.hoisted(() => vi.fn());

const wrappers: ReturnType<typeof mount>[] = [];
function mountDrawer() {
  const wrapper = mount(ExamWorkspaceMetadataDrawer, {
    attachTo: document.body,
    props: {
      title: "NO-prov HT25",
      header: { course: null, course_hint: null, printed_total: null },
      name: "NO. höst.provdokument.zip",
      vaultFileId: "vault-head-7",
      renameFile: rename,
      renameFailure: null,
      disabled: false,
      layout: "phone",
    },
    global: { plugins: [createTestingPinia({ createSpy: vi.fn })] },
  });
  wrappers.push(wrapper);
  return wrapper;
}

beforeEach(() => rename.mockReset());
afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount();
  document.body.innerHTML = "";
});

describe("ExamWorkspaceMetadataDrawer", () => {
  it("keeps title and filename separate, removing only the package suffix", async () => {
    const wrapper = mountDrawer();
    expect(wrapper.text()).toContain("Provets uppgifter");
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-title"]').element.value)
      .toBe("NO-prov HT25");
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-name"]').element.value)
      .toBe("NO. höst");

    await wrapper.get('[data-test="exam-workspace-metadata-title"]').setValue("Vattnets kretslopp");
    await wrapper.get('[data-test="exam-workspace-metadata-title"]').setValue("");
    expect(wrapper.emitted("update:title")).toEqual([["Vattnets kretslopp"], [""]]);
    expect(rename).not.toHaveBeenCalled();
  });

  it("refuses unchanged and whitespace-only names and waits for the rename reply", async () => {
    const wrapper = mountDrawer();
    const button = wrapper.get('[data-test="exam-workspace-metadata-rename"]');
    const input = wrapper.get('[data-test="exam-workspace-metadata-name"]');
    expect(button.attributes("disabled")).toBeDefined();
    await input.setValue("   ");
    expect(button.attributes("disabled")).toBeDefined();

    let finish!: (value: unknown) => void;
    rename.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    await input.setValue("NO nytt");
    await button.trigger("click");
    expect(rename).toHaveBeenCalledWith("vault-head-7", "NO nytt");
    expect(button.attributes("disabled")).toBeDefined();
    await button.trigger("click");
    expect(rename).toHaveBeenCalledTimes(1);
    finish("NO nytt.provdokument.zip");
    await flushPromises();
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-name"]').element.value)
      .toBe("NO nytt");
    await wrapper.setProps({ name: "NO nytt.provdokument.zip" });
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-name"]').element.value)
      .toBe("NO nytt");
    expect(button.attributes("disabled")).toBeDefined();
  });

  it("shows the backend collision message and lets the teacher correct the stem", async () => {
    const wrapper = mountDrawer();
    rename.mockResolvedValueOnce(null);
    await wrapper.get('[data-test="exam-workspace-metadata-name"]').setValue("NO nytt");
    await wrapper.get('[data-test="exam-workspace-metadata-rename"]').trigger("click");
    await flushPromises();
    await wrapper.setProps({ renameFailure: {
      stem: "NO nytt", message: "En annan fil heter redan NO nytt.provdokument.zip.",
    } });
    expect(wrapper.get('[data-test="exam-workspace-metadata-name-error"]').text())
      .toBe("En annan fil heter redan NO nytt.provdokument.zip.");
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-name"]').element.value)
      .toBe("NO nytt");
    rename.mockResolvedValueOnce("NO eget.provdokument.zip");
    await wrapper.setProps({ renameFailure: null });
    await wrapper.get('[data-test="exam-workspace-metadata-name"]').setValue("NO eget");
    await wrapper.get('[data-test="exam-workspace-metadata-rename"]').trigger("click");
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-metadata-name-error"]').exists()).toBe(false);
    expect(rename).toHaveBeenLastCalledWith("vault-head-7", "NO eget");
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-name"]').element.value)
      .toBe("NO eget");
  });

  it("uses the phone dialog focus contract and restores focus to the title opener", async () => {
    const opener = document.createElement("button");
    opener.dataset.test = "exam-workspace-summary-title";
    document.body.append(opener);
    opener.focus();
    const wrapper = mountDrawer();
    await flushPromises();
    const frame = wrapper.get('[data-test="exam-workspace-metadata-drawer-frame"]');
    expect(frame.attributes("role")).toBe("dialog");
    expect(frame.attributes("aria-modal")).toBe("true");
    expect(frame.element.contains(document.activeElement)).toBe(true);
    await frame.trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toHaveLength(1);
    wrapper.unmount();
    wrappers.splice(wrappers.indexOf(wrapper), 1);
    expect(document.activeElement).toBe(opener);
  });
});
