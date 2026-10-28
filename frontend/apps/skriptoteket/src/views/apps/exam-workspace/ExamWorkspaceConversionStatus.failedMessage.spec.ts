/**
 * Exam workspace import status: a failed import's message is read in full
 * (TASK-SKRIPT-39-10-03). The running phase line stays one line cut with an
 * ellipsis; the failure message wraps, so the Word/PDF guidance is on screen
 * and not only in a tooltip.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamWorkspaceConversionStatus from "./ExamWorkspaceConversionStatus.vue";

const MESSAGE = '[data-test="exam-workspace-conversion-message"]';
const FAILURE =
  "Det gick inte att läsa in texten i PDF-filen. Spara provet som Word-fil eller som en PDF med textlager och välj filen igen.";

function mountStatus(state: { isConverting: boolean; isImporting: boolean; message: string }) {
  return mount(ExamWorkspaceConversionStatus, {
    props: { elapsed: null, error: null, progress: null, ...state },
  });
}

describe("ExamWorkspaceConversionStatus failed message", () => {
  it("shows a failed import's whole message, wrapping, with no ellipsis or tooltip", () => {
    const wrapper = mountStatus({ isConverting: false, isImporting: false, message: FAILURE });
    const message = wrapper.get(MESSAGE);

    expect(message.text()).toBe(FAILURE);
    expect(message.classes()).toContain("prog__message--full");
    expect(message.attributes("title")).toBeUndefined();
  });

  it("keeps the running phase line on one line with the full text in the tooltip", () => {
    const wrapper = mountStatus({ isConverting: true, isImporting: false, message: "Hittar frågorna" });
    const message = wrapper.get(MESSAGE);

    expect(message.classes()).not.toContain("prog__message--full");
    expect(message.attributes("title")).toBe("Hittar frågorna");
  });
});
