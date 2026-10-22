/**
 * The header's "Föreslå facit för frågor som saknar facit" button runs for
 * every signed-in user.
 *
 * Expected behavior:
 *   With role "user" or "contributor" the glyph-only button is enabled, its
 *   title names the suggest action, and no admin-only note text shows
 *   anywhere in the header. The existing busy/disabled reasons still hold.
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useAuthStore } from "../../../stores/auth";
import ExamWorkspaceHeader from "./ExamWorkspaceHeader.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";

const SUGGEST_TITLE = "Föreslå facit för frågor som saknar facit";
/** Distinctive fragment of the removed admin-only note; the full note must not render. */
const REMOVED_ADMIN_NOTE = "bara tillgängliga för administratörer";

type HeaderProps = InstanceType<typeof ExamWorkspaceHeader>["$props"];

function props(overrides: Partial<HeaderProps> = {}): HeaderProps {
  return {
    title: "Prov 1",
    saveState: "saved",
    saveText: "Sparat",
    saveTitle: null,
    courseLabel: null,
    total: 0,
    detailsOpen: false,
    openDrawerOpen: false,
    canRename: true,
    canSaveAs: true,
    suggestBusy: false,
    suggestDisabled: false,
    isPhone: false,
    previewOpen: false,
    newExamBusy: false,
    ...overrides,
  };
}

function mountHeader(pinia: Pinia, overrides: Partial<HeaderProps> = {}) {
  return mount(ExamWorkspaceHeader, {
    props: props(overrides),
    global: {
      plugins: [pinia, examWorkspaceProvidersPlugin()],
    },
  });
}

/** Elements carrying the old admin-only note as their visible text, found without test hooks. */
function noteElements(wrapper: ReturnType<typeof mountHeader>) {
  return wrapper.findAll("*").filter((element) => element.text().trim() === REMOVED_ADMIN_NOTE);
}

let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
});

describe("ExamWorkspaceHeader non-admin AI", () => {
  it.each(["user", "contributor"] as const)(
    "leaves the suggest-all button working without the admin-only note for role %s",
    async (role) => {
      setActivePinia(pinia);
      useAuthStore().user = { id: "u1", email: "u@example.test", role, auth_provider: "local" };
      const wrapper = mountHeader(pinia);

      const button = wrapper.get('[data-test="exam-workspace-suggest-all"]');
      expect(button.attributes("disabled")).toBeUndefined();
      expect(button.attributes("title")).toBe(SUGGEST_TITLE);
      expect(button.attributes("aria-description")).toBeUndefined();
      expect(noteElements(wrapper)).toHaveLength(0);
      await button.trigger("click");
      expect(wrapper.emitted("suggestAll")).toHaveLength(1);
      wrapper.unmount();
    },
  );

  it("keeps a disabled reason when the exam is busy", () => {
    setActivePinia(pinia);
    useAuthStore().user = { id: "u1", email: "u@example.test", role: "user", auth_provider: "local" };
    const wrapper = mountHeader(pinia, { suggestBusy: true });

    const button = wrapper.get('[data-test="exam-workspace-suggest-all"]');
    expect(button.attributes("disabled")).toBeDefined();
    expect(button.attributes("title")).toBe("Facitförslagen tas fram …");
    wrapper.unmount();
  });
});
