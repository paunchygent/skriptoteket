/**
 * Exam workspace header autosave status slot (TASK-SKRIPT-40-04-17, T1).
 *
 * Expected behavior:
 *   The one status slot at the header's right end shows the cloud-check glyph
 *   with the saved text, a spinning loader with `Sparar …` while storing, and
 *   the blocker glyph with `Inte sparat` and the failure reason as its tooltip
 *   after a failed store. There is no Spara button and no Spara menu.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { mountHeader } from "./ExamWorkspaceHeader.specSupport";

beforeEach(() => {
  setActivePinia(createPinia());
});

describe("ExamWorkspaceHeader save state", () => {
  it("shows the saved text with a calm glyph and no tooltip", () => {
    const wrapper = mountHeader({ saveState: "saved", saveText: "Sparat 14:05", saveTitle: null });
    const slot = wrapper.get('[data-test="exam-workspace-save-state"]');
    expect(slot.text()).toBe("Sparat 14:05");
    expect(slot.attributes("title")).toBeUndefined();
    expect(slot.find("svg.xw-spin").exists()).toBe(false);
    wrapper.unmount();
  });

  it("shows Sparar … with a spinning glyph during a write", () => {
    const wrapper = mountHeader({ saveState: "saving", saveText: "Sparar …" });
    const slot = wrapper.get('[data-test="exam-workspace-save-state"]');
    expect(slot.text()).toBe("Sparar …");
    expect(slot.find(".xw-spin").exists()).toBe(true);
    wrapper.unmount();
  });

  it("shows Inte sparat with the failure reason as its tooltip", () => {
    const reason = "Provet sparades inte: frågor som fortfarande konverteras går inte att ändra.";
    const wrapper = mountHeader({ saveState: "unsaved", saveText: "Inte sparat", saveTitle: reason });
    const slot = wrapper.get('[data-test="exam-workspace-save-state"]');
    expect(slot.text()).toBe("Inte sparat");
    expect(slot.attributes("title")).toBe(reason);
    expect(slot.find(".xw-spin").exists()).toBe(false);
    wrapper.unmount();
  });

  it("uses a different glyph for each of the three states in the same slot", () => {
    const glyphs = (["saved", "saving", "unsaved"] as const).map((saveState) => {
      const wrapper = mountHeader({ saveState });
      const html = wrapper.get('[data-test="exam-workspace-save-state"] svg').html();
      wrapper.unmount();
      return html.replace(/\s*class="[^"]*"/, "");
    });
    expect(new Set(glyphs).size).toBe(3);
  });

  it("has no Spara button and no Spara menu", () => {
    const wrapper = mountHeader();
    expect(wrapper.find('[data-test="exam-workspace-save"]').exists()).toBe(false);
    expect(wrapper.find('[aria-haspopup="menu"]').exists()).toBe(false);
    wrapper.unmount();
  });
});
