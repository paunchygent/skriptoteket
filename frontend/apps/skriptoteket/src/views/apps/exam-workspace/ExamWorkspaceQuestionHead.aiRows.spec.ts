/**
 * Exam workspace question head, the AI rows of ⋮ Fler åtgärder.
 *
 * Expected behavior (TASK-SKRIPT-40-04-26 D7, D8):
 *   The three per-question AI controls open the ⋮ Fler åtgärder menu as rows
 *   with words, because a menu row has no tooltip and touch has no hover. The
 *   rows come first, in the order Föreslå facit, Ta bort AI-facit, Gör om
 *   till [typ], and one separator follows them before the built rows. They
 *   render whenever the question has that control, whatever the band; the
 *   stylesheet decides where they show. A disabled row keeps its reason as
 *   `aria-disabled` and the built hint, and a click does nothing; an enabled
 *   row closes the menu and emits its intent, with the suggested kind for
 *   Byt till. No control means no row and no separator.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { NativeExamItem, NativeExamItemKind } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionHead from "./ExamWorkspaceQuestionHead.vue";
import { questionAiControls } from "./examWorkspaceQuestionAi";
import type { QuestionAiContext, QuestionAiControls } from "./examWorkspaceQuestionAi";
import { newTeacherItem } from "./examWorkspaceItemEdits";

const MENU = '[data-test="exam-workspace-more-menu"]';
const SUGGEST = '[data-test="exam-workspace-more-ai-suggest"]';
const UNDO = '[data-test="exam-workspace-more-ai-undo"]';
const CONVERT = '[data-test="exam-workspace-more-ai-convert"]';

/** Nothing to offer: the state a guest or a question with no AI control reads. */
const NO_AI: QuestionAiControls = { convert: null, suggest: null, undo: null };

/** The state a signed-in teacher with an available, unlimited AI door reads. */
const CONTEXT: QuestionAiContext = {
  busy: false,
  guest: false,
  limitNote: null,
  locked: false,
  suggestAvailable: true,
};

type Origin = NativeExamItem["answer_key"]["origin"];

function item(
  origin: Origin = "absent",
  options: { kind?: NativeExamItemKind; suggested?: NativeExamItemKind | null } = {},
): NativeExamItem {
  const base = newTeacherItem("item_001", 1, options.kind ?? "single_choice");
  return {
    ...base,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin },
    suggested_kind: options.suggested ?? null,
  };
}

/** The controls the workspace composable would hand the head for this question. */
function controlsFor(candidate: NativeExamItem, overrides: Partial<QuestionAiContext> = {}): QuestionAiControls {
  return questionAiControls(candidate, { ...CONTEXT, ...overrides });
}

const mounted: Array<VueWrapper> = [];

function mountHead(aiControls?: QuestionAiControls): VueWrapper {
  const props = {
    child: null,
    converting: false,
    currentParentId: null,
    disabled: false,
    kind: "single_choice" as const,
    label: "3",
    moveTargets: [],
    suggestedKind: null,
    typeLabel: "Ett svar",
    unbuilt: false,
  };
  const wrapper = mount(
    ExamWorkspaceQuestionHead,
    aiControls === undefined ? { attachTo: document.body, props } : { attachTo: document.body, props: { ...props, aiControls } },
  );
  mounted.push(wrapper);
  return wrapper;
}

function inDocument(selector: string): HTMLElement | null {
  const element = document.querySelector(selector);
  return element instanceof HTMLElement ? element : null;
}

/** Open ⋮ Fler åtgärder and return its rendered children in document order. */
async function openMore(wrapper: VueWrapper): Promise<HTMLElement[]> {
  await wrapper.get('[data-test="exam-workspace-more"]').trigger("click");
  await flushPromises();
  const menu = inDocument(MENU);
  if (menu === null) {
    throw new Error("the Fler åtgärder menu did not open");
  }
  return Array.from(menu.children).filter((child): child is HTMLElement => child instanceof HTMLElement);
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  document.body.replaceChildren();
});

describe("ExamWorkspaceQuestionHead AI rows", () => {
  it("renders the three AI rows with words, then a separator, above Flytta till", async () => {
    const wrapper = mountHead(controlsFor(item("absent", { suggested: "gap_fill" })));

    const children = await openMore(wrapper);

    expect(children[0]!.getAttribute("data-test")).toBe("exam-workspace-more-ai-suggest");
    expect(children[1]!.getAttribute("data-test")).toBe("exam-workspace-more-ai-undo");
    expect(children[2]!.getAttribute("data-test")).toBe("exam-workspace-more-ai-convert");
    expect(children[3]!.getAttribute("role")).toBe("separator");
    expect(children[3]!.classList.contains("qai-mi-sep")).toBe(true);
    expect(children[4]!.getAttribute("data-test")).toBe("exam-workspace-move-to");

    for (const row of children.slice(0, 3)) {
      expect(row.getAttribute("role")).toBe("menuitem");
      expect(row.classList.contains("xw-mi")).toBe(true);
      expect(row.classList.contains("qai-mi")).toBe(true);
      expect(row.querySelector("svg.xw-ai")).not.toBeNull();
    }
    expect(children[0]!.textContent).toContain("Föreslå facit");
    expect(children[1]!.textContent).toContain("Ta bort AI-facit");
    expect(children[2]!.textContent).toContain("Byt till Lucktext");
  });

  it("renders no AI row and no separator when the question shows no AI control", async () => {
    const wrapper = mountHead(NO_AI);

    const children = await openMore(wrapper);

    expect(children[0]!.getAttribute("data-test")).toBe("exam-workspace-move-to");
    expect(inDocument(`${MENU} .qai-mi`)).toBeNull();
    expect(inDocument(`${MENU} .qai-mi-sep`)).toBeNull();
    expect(inDocument(`${MENU} [role="separator"]`)).toBeNull();
  });

  it("defaults to no AI rows when the head receives no controls", async () => {
    const wrapper = mountHead();

    const children = await openMore(wrapper);

    expect(children[0]!.getAttribute("data-test")).toBe("exam-workspace-move-to");
    expect(inDocument(`${MENU} .qai-mi`)).toBeNull();
  });

  it("marks a disabled suggest row with aria-disabled and its hint, and emits nothing", async () => {
    const wrapper = mountHead(controlsFor(item("ai_interpreted")));

    await openMore(wrapper);

    const suggest = inDocument(SUGGEST);
    expect(suggest).not.toBeNull();
    expect(suggest!.getAttribute("aria-disabled")).toBe("true");
    const hint = suggest!.querySelector(".xw-mi__hint");
    expect(hint?.textContent).toBe("Har facit");

    suggest!.click();
    await flushPromises();

    expect(wrapper.emitted("aiSuggest")).toBeUndefined();
    expect(inDocument(MENU)).not.toBeNull();
  });

  it("emits aiUndo from the enabled undo row and closes the menu", async () => {
    const wrapper = mountHead(controlsFor(item("machine_proposed")));

    await openMore(wrapper);
    const undo = inDocument(UNDO);
    expect(undo!.getAttribute("aria-disabled")).toBeNull();

    undo!.click();
    await flushPromises();

    expect(wrapper.emitted("aiUndo")).toEqual([[]]);
    expect(inDocument(MENU)).toBeNull();
    expect(wrapper.get('[data-test="exam-workspace-more"]').attributes("aria-expanded")).toBe("false");
  });

  it("names the suggested type in the convert row and emits aiConvert with its kind", async () => {
    const wrapper = mountHead(controlsFor(item("absent", { suggested: "gap_fill" })));

    await openMore(wrapper);
    const convert = inDocument(CONVERT);
    expect(convert!.textContent).toContain("Byt till Lucktext");
    expect(convert!.getAttribute("aria-disabled")).toBeNull();

    convert!.click();
    await flushPromises();

    expect(wrapper.emitted("aiConvert")).toEqual([["gap_fill"]]);
    expect(inDocument(MENU)).toBeNull();
  });
});
