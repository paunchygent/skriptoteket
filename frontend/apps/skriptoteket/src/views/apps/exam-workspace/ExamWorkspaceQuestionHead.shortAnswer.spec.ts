/**
 * Exam workspace question header, Kort svar entry in Byt frågetyp.
 *
 * Expected behavior:
 *   Byt frågetyp shows a Kort svar entry after Fritext when the question is
 *   a Kort svar or can become one. A Kort svar ticks Kort svar and unticks
 *   Lucktext; choosing Lucktext there emits changeShape gap_fill, choosing
 *   Kort svar on a Kort svar emits nothing. An eligible Lucktext ticks
 *   Lucktext and offers Kort svar unticked; choosing it emits changeShape
 *   short_answer. Every other question shows no Kort svar entry, and any
 *   other choice still emits changeType.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { NativeExamItemKind } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionHead from "./ExamWorkspaceQuestionHead.vue";

const mounted: Array<VueWrapper> = [];

function mountHead(options: {
  kind: NativeExamItemKind;
  shortAnswer: boolean;
  shortAnswerOffered: boolean;
  typeLabel: string;
}): VueWrapper {
  const wrapper = mount(ExamWorkspaceQuestionHead, {
    attachTo: document.body,
    props: {
      child: null,
      converting: false,
      currentParentId: null,
      disabled: false,
      kind: options.kind,
      label: "4",
      moveTargets: [],
      shortAnswer: options.shortAnswer,
      shortAnswerOffered: options.shortAnswerOffered,
      suggestedKind: null,
      typeLabel: options.typeLabel,
      unbuilt: false,
    },
  });
  mounted.push(wrapper);
  return wrapper;
}

async function openTypeMenu(wrapper: VueWrapper): Promise<void> {
  await wrapper.get('[data-test="exam-workspace-type"]').trigger("click");
  await flushPromises();
}

function typeEntry(testId: string): HTMLElement {
  const element = document.querySelector(`[data-test="${testId}"]`);
  if (!(element instanceof HTMLElement)) {
    throw new Error(`missing ${testId}`);
  }
  return element;
}

function typeEntries(): HTMLElement[] {
  return Array.from(
    document.querySelectorAll<HTMLElement>('[data-test="exam-workspace-type-menu"] [role="menuitemradio"]'),
  );
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  document.body.replaceChildren();
});

describe("ExamWorkspaceQuestionHead Kort svar entry", () => {
  it("ticks Kort svar and unticks Lucktext for a Kort svar; Lucktext emits changeShape, Kort svar emits nothing", async () => {
    const wrapper = mountHead({ kind: "gap_fill", shortAnswer: true, shortAnswerOffered: false, typeLabel: "Kort svar" });

    await openTypeMenu(wrapper);

    const shortAnswer = typeEntry("exam-workspace-type-short_answer");
    expect(shortAnswer.getAttribute("aria-checked")).toBe("true");
    expect(typeEntry("exam-workspace-type-gap_fill").getAttribute("aria-checked")).toBe("false");

    shortAnswer.click();
    await flushPromises();
    expect(wrapper.emitted("changeShape")).toBeUndefined();
    expect(wrapper.emitted("changeType")).toBeUndefined();

    await openTypeMenu(wrapper);
    typeEntry("exam-workspace-type-gap_fill").click();
    await flushPromises();
    expect(wrapper.emitted("changeShape")).toEqual([["gap_fill"]]);
    expect(wrapper.emitted("changeType")).toBeUndefined();
  });

  it("offers an unticked Kort svar for an eligible Lucktext and turns it into a Kort svar", async () => {
    const wrapper = mountHead({
      kind: "gap_fill",
      shortAnswer: false,
      shortAnswerOffered: true,
      typeLabel: "Lucktext",
    });

    await openTypeMenu(wrapper);

    const shortAnswer = typeEntry("exam-workspace-type-short_answer");
    expect(shortAnswer.getAttribute("aria-checked")).toBe("false");
    expect(typeEntry("exam-workspace-type-gap_fill").getAttribute("aria-checked")).toBe("true");

    shortAnswer.click();
    await flushPromises();
    expect(wrapper.emitted("changeShape")).toEqual([["short_answer"]]);
    expect(wrapper.emitted("changeType")).toBeUndefined();
  });

  it("shows no Kort svar entry for other questions", async () => {
    const freeText = mountHead({
      kind: "free_text",
      shortAnswer: false,
      shortAnswerOffered: false,
      typeLabel: "Fritext",
    });

    await openTypeMenu(freeText);
    expect(document.querySelector('[data-test="exam-workspace-type-short_answer"]')).toBeNull();
    freeText.unmount();
    mounted.splice(0);
    document.body.replaceChildren();

    mountHead({ kind: "gap_fill", shortAnswer: false, shortAnswerOffered: false, typeLabel: "Lucktext" });
    const twoGap = mounted[0]!;
    await openTypeMenu(twoGap);
    expect(document.querySelector('[data-test="exam-workspace-type-short_answer"]')).toBeNull();
  });

  it("keeps the server change type for other choices made on a Kort svar", async () => {
    const wrapper = mountHead({ kind: "gap_fill", shortAnswer: true, shortAnswerOffered: false, typeLabel: "Kort svar" });

    await openTypeMenu(wrapper);
    typeEntry("exam-workspace-type-single_choice").click();
    await flushPromises();

    expect(wrapper.emitted("changeType")).toEqual([["single_choice"]]);
    expect(wrapper.emitted("changeShape")).toBeUndefined();
  });

  it("lists Kort svar between Fritext and Flerval", async () => {
    const wrapper = mountHead({ kind: "gap_fill", shortAnswer: true, shortAnswerOffered: false, typeLabel: "Kort svar" });

    await openTypeMenu(wrapper);

    const entries = typeEntries();
    expect(entries.length).toBeGreaterThan(2);
    expect(entries[0]!.getAttribute("data-test")).toBe("exam-workspace-type-free_text");
    expect(entries[1]!.getAttribute("data-test")).toBe("exam-workspace-type-short_answer");
    expect(entries[2]!.getAttribute("data-test")).toBe("exam-workspace-type-single_choice");
  });
});
