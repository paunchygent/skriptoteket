/**
 * Exam workspace question header, visible type label.
 *
 * Expected behavior:
 *   The type button shows the passed `typeLabel`: a Kort svar reads
 *   "Kort svar" while its `kind` stays gap_fill, so Byt frågetyp still
 *   marks Lucktext.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import ExamWorkspaceQuestionHead from "./ExamWorkspaceQuestionHead.vue";

const mounted: Array<{ unmount: () => void }> = [];

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  document.body.replaceChildren();
});

describe("ExamWorkspaceQuestionHead type label", () => {
  it("shows Kort svar on the type button while gap_fill stays marked Lucktext", async () => {
    const wrapper = mount(ExamWorkspaceQuestionHead, {
      attachTo: document.body,
      props: {
        child: null,
        converting: false,
        currentParentId: null,
        disabled: false,
        kind: "gap_fill",
        label: "4",
        moveTargets: [],
        suggestedKind: null,
        typeLabel: "Kort svar",
        unbuilt: false,
      },
    });
    mounted.push(wrapper);

    expect(wrapper.get('[data-test="exam-workspace-type"]').text()).toContain("Kort svar");

    await wrapper.get('[data-test="exam-workspace-type"]').trigger("click");
    await flushPromises();
    const menu = document.querySelector('[data-test="exam-workspace-type-menu"]')!;
    expect(menu.textContent).toContain("Lucktext");
    expect(
      menu.querySelector('[data-test="exam-workspace-type-gap_fill"]')?.getAttribute("aria-checked"),
    ).toBe("true");
  });
});
