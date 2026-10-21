/**
 * Exam workspace header Nytt prov command (TASK-SKRIPT-40-04-21, D1).
 *
 * Expected behavior:
 *   Nytt prov is the first file command for a teacher and a guest, before
 *   Öppna, with the file-new glyph and the neighbouring button style. It
 *   emits `newExam` directly and locks while a new exam is being created.
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceHeader from "./ExamWorkspaceHeader.vue";
import type { HeaderProps } from "./ExamWorkspaceHeader.specSupport";
import { headerProps } from "./ExamWorkspaceHeader.specSupport";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";

const guestStore: ExamWorkspaceStore = {
  ...serverExamWorkspaceStore,
  teacher: null,
  guest: { startBlank: vi.fn(), startFromQti: vi.fn() },
};

let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
});

function mountWithStore(store: ExamWorkspaceStore, overrides: Partial<HeaderProps> = {}) {
  setActivePinia(pinia);
  return mount(ExamWorkspaceHeader, {
    props: headerProps(overrides),
    attachTo: document.body,
    slots: { export: '<button data-test="exam-workspace-export" class="xw-cmd">Exportera</button>' },
    global: { plugins: [pinia, examWorkspaceProvidersPlugin({ store })] },
  });
}

/** The file commands in toolbar order, as the teacher and the guest each see them. */
function fileCommandOrder(wrapper: ReturnType<typeof mountWithStore>): (string | undefined)[] {
  const commands = ["exam-workspace-new-exam", "exam-workspace-open", "exam-workspace-save-as-command", "exam-workspace-import"];
  return wrapper
    .findAll("[data-test]")
    .map((element) => element.attributes("data-test"))
    .filter((id) => id !== undefined && commands.includes(id));
}

describe("ExamWorkspaceHeader Nytt prov", () => {
  it("reads Nytt prov first for a teacher, before Öppna, Spara som and Importera", () => {
    const wrapper = mountWithStore(serverExamWorkspaceStore);
    expect(fileCommandOrder(wrapper)).toEqual([
      "exam-workspace-new-exam",
      "exam-workspace-open",
      "exam-workspace-save-as-command",
      "exam-workspace-import",
    ]);
    wrapper.unmount();
  });

  it("reads Nytt prov first for a guest, with no Spara som", () => {
    const wrapper = mountWithStore(guestStore);
    expect(fileCommandOrder(wrapper)).toEqual([
      "exam-workspace-new-exam",
      "exam-workspace-open",
      "exam-workspace-import",
    ]);
    expect(wrapper.find('[data-test="exam-workspace-save-as-command"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("shows the file-new glyph with its label and emits newExam", async () => {
    const wrapper = mountWithStore(serverExamWorkspaceStore);
    const button = wrapper.get('[data-test="exam-workspace-new-exam"]');
    expect(button.attributes("type")).toBe("button");
    expect(button.attributes("class")).toContain("xw-cmd");
    expect(button.attributes("aria-label")).toBe("Nytt prov");
    expect(button.attributes("title")).toBe("Skapa ett nytt prov");
    expect(button.text()).toBe("Nytt prov");
    expect(button.findComponent(UiGlyph).props("meaning")).toBe("file-new");
    await button.trigger("click");
    expect(wrapper.emitted("newExam")).toHaveLength(1);
    wrapper.unmount();
  });

  it("locks the command while a new exam is being created", async () => {
    const wrapper = mountWithStore(serverExamWorkspaceStore, { newExamBusy: true });
    const button = wrapper.get('[data-test="exam-workspace-new-exam"]');
    expect(button.attributes("disabled")).toBeDefined();
    wrapper.unmount();

    const idle = mountWithStore(serverExamWorkspaceStore, { newExamBusy: false });
    expect(idle.get('[data-test="exam-workspace-new-exam"]').attributes("disabled")).toBeUndefined();
    idle.unmount();
  });
});
