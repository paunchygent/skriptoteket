import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceNoteLine from "./ExamWorkspaceNoteLine.vue";
import type { ExamWorkspaceNoteLineAction } from "./ExamWorkspaceNoteLine.vue";

const ACTIONS: ExamWorkspaceNoteLineAction[] = [
  { dataTest: "exam-workspace-printed-total-change", key: "change", label: "Godta frågornas summa, 67 p", meaning: "confirm" },
  { dataTest: "exam-workspace-printed-total-show", key: "show", label: "Visa frågorna", meaning: "continue" },
];

const LINE_TEST_ID = "exam-workspace-printed-total-line";

function mountLine(disabled: boolean) {
  return mount(ExamWorkspaceNoteLine, {
    attrs: { "data-test": LINE_TEST_ID },
    props: { actions: ACTIONS, disabled, text: "Provtexten säger 70 p, frågorna ger 67 p." },
  });
}

describe("ExamWorkspaceNoteLine", () => {
  it("renders the text and one glyph-only button per action", () => {
    const wrapper = mountLine(false);
    const line = wrapper.get(`[data-test="${LINE_TEST_ID}"]`);
    expect(line.attributes("role")).toBe("group");
    expect(line.attributes("aria-label")).toBe("Provtexten säger 70 p, frågorna ger 67 p.");
    expect(line.get(".note-line__text").text()).toBe("Provtexten säger 70 p, frågorna ger 67 p.");
    expect(line.get(".note-line__text").attributes("title")).toBe("Provtexten säger 70 p, frågorna ger 67 p.");

    const buttons = wrapper.findAll("button");
    expect(buttons).toHaveLength(2);
    expect(buttons[0]!.attributes("data-test")).toBe("exam-workspace-printed-total-change");
    expect(buttons[0]!.attributes("title")).toBe("Godta frågornas summa, 67 p");
    expect(buttons[0]!.attributes("aria-label")).toBe("Godta frågornas summa, 67 p");
    expect(buttons[0]!.text()).toBe("");
    expect(buttons[0]!.findComponent(UiGlyph).props("meaning")).toBe("confirm");
    expect(buttons[1]!.attributes("data-test")).toBe("exam-workspace-printed-total-show");
    expect(buttons[1]!.attributes("title")).toBe("Visa frågorna");
    expect(buttons[1]!.attributes("aria-label")).toBe("Visa frågorna");
    expect(buttons[1]!.text()).toBe("");
    expect(buttons[1]!.findComponent(UiGlyph).props("meaning")).toBe("continue");
    wrapper.unmount();
  });

  it("emits the action key on click", async () => {
    const wrapper = mountLine(false);
    await wrapper.findAll("button")[1]!.trigger("click");
    expect(wrapper.emitted("action")).toEqual([["show"]]);
    wrapper.unmount();
  });

  it("disables every button while the workspace is busy", () => {
    const wrapper = mountLine(true);
    for (const button of wrapper.findAll("button")) {
      expect(button.attributes("disabled")).toBeDefined();
    }
    wrapper.unmount();
  });
});
