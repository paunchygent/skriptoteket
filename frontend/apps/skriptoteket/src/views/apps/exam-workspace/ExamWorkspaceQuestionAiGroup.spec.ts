/**
 * Exam workspace question AI group in the question-text toolbar.
 *
 * Expected behavior (TASK-SKRIPT-40-04-26 D2-D6):
 *   The group is the toolbar's last child after its own separator, so a
 *   pinned group keeps its left edge. It shows Föreslå facit (glyph only, the
 *   word in title and aria-label), Ta bort AI-facit (glyph only) and Gör om
 *   till [typ] (glyph and, at the wide band, the type name). It renders the
 *   controls it is handed and asks for nothing itself: a click emits
 *   `suggest`, `undo` or `convert` with the suggested kind, and the editor
 *   routes them. While a suggestion runs the suggest glyph spins with the busy
 *   meaning and Byt till is disabled. Without an AI provider the controls
 *   carry no suggestion, and a guest's controls are all null, so the group is
 *   absent.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem, NativeExamItemKind } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import { AI_APP_LIMIT_NOTE } from "../../../composables/aiDailyLimit";
import ExamWorkspaceQuestionAiGroup from "./ExamWorkspaceQuestionAiGroup.vue";
import { questionAiControls } from "./examWorkspaceQuestionAi";
import type { QuestionAiContext, QuestionAiControls } from "./examWorkspaceQuestionAi";
import { newTeacherItem } from "./examWorkspaceItemEdits";

const GROUP = '[role="group"][aria-label="AI-förslag för frågan"]';
const SUGGEST = '[data-test="exam-workspace-ai-suggest"]';
const UNDO = '[data-test="exam-workspace-ai-undo"]';
const CONVERT = '[data-test="exam-workspace-suggested-type"]';

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
  options: { kind?: NativeExamItemKind; retry?: NativeExamItem["answer_key_retry"]; suggested?: NativeExamItemKind | null } = {},
): NativeExamItem {
  const base = newTeacherItem("item_001", 1, options.kind ?? "single_choice");
  return {
    ...base,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin },
    answer_key_retry: options.retry ?? "none",
    suggested_kind: options.suggested ?? null,
  };
}

/** The controls the workspace composable would hand the group for this question. */
function controlsFor(candidate: NativeExamItem = item(), overrides: Partial<QuestionAiContext> = {}): QuestionAiControls {
  return questionAiControls(candidate, { ...CONTEXT, ...overrides });
}

function mountGroup(controls: QuestionAiControls) {
  return mount(ExamWorkspaceQuestionAiGroup, { props: { controls } });
}

function group(wrapper: ReturnType<typeof mountGroup>) {
  return wrapper.findComponent(ExamWorkspaceQuestionAiGroup);
}

describe("ExamWorkspaceQuestionAiGroup composition", () => {
  it("puts its separator first and one glyph tool per offered control", () => {
    const wrapper = mountGroup(controlsFor(item("absent", { suggested: "gap_fill" })));

    const root = wrapper.get(GROUP);
    expect(root.classes()).toContain("xw-tools");
    expect(root.element.children[0]!.classList.contains("xw-toolsep")).toBe(true);
    expect(root.element.children[0]!.getAttribute("aria-hidden")).toBe("true");
    expect(wrapper.find(SUGGEST).exists()).toBe(true);
    expect(wrapper.find(UNDO).exists()).toBe(true);
    expect(wrapper.find(CONVERT).exists()).toBe(true);
    for (const selector of [SUGGEST, UNDO, CONVERT]) {
      expect(wrapper.get(selector).classes()).toContain("xw-tool");
    }
    wrapper.unmount();
  });

  it("carries the type name on the convert face with the full title", () => {
    const wrapper = mountGroup(controlsFor(item("absent", { suggested: "gap_fill" })));

    const convert = wrapper.get(CONVERT);
    expect(convert.classes()).toContain("xw-tool--word");
    expect(convert.text()).toBe("Lucktext");
    expect(convert.attributes("aria-label")).toBe("Byt till Lucktext");
    expect(convert.attributes("title")).toBe("Byt till Lucktext");
    expect(convert.find(".qai__name").text()).toBe("Lucktext");
    wrapper.unmount();
  });

  it("renders nothing at all for a guest", () => {
    const wrapper = mountGroup(controlsFor(item("machine_proposed", { suggested: "gap_fill" }), { guest: true }));

    expect(wrapper.find(GROUP).exists()).toBe(false);
    expect(wrapper.findAll("button")).toHaveLength(0);
    wrapper.unmount();
  });

  it("shows no suggest control without an AI provider", () => {
    const wrapper = mountGroup(controlsFor(item("absent"), { suggestAvailable: false }));

    expect(wrapper.find(GROUP).exists()).toBe(true);
    expect(wrapper.find(SUGGEST).exists()).toBe(false);
    expect(wrapper.find(UNDO).exists()).toBe(true);
    wrapper.unmount();
  });
});

describe("ExamWorkspaceQuestionAiGroup actions", () => {
  it("emits suggest for the owner to route to this question", async () => {
    const wrapper = mountGroup(controlsFor());

    await wrapper.get(SUGGEST).trigger("click");

    expect(group(wrapper).emitted("suggest")).toEqual([[]]);
    wrapper.unmount();
  });

  it("emits undo and the suggested kind", async () => {
    const wrapper = mountGroup(controlsFor(item("machine_proposed", { suggested: "gap_fill" })));

    await wrapper.get(UNDO).trigger("click");
    await wrapper.get(CONVERT).trigger("click");

    expect(group(wrapper).emitted("undo")).toEqual([[]]);
    expect(group(wrapper).emitted("convert")).toEqual([["gap_fill"]]);
    wrapper.unmount();
  });

  it("disables the suggest and convert controls on a question that already has a key and a lock", () => {
    const wrapper = mountGroup(controlsFor(item("ai_interpreted", { suggested: "gap_fill" }), { locked: true }));

    expect(wrapper.get(SUGGEST).attributes("disabled")).toBeDefined();
    expect(wrapper.get(UNDO).attributes("disabled")).toBeDefined();
    expect(wrapper.get(CONVERT).attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });
});

describe("ExamWorkspaceQuestionAiGroup busy and limit states", () => {
  it("spins the suggest glyph with the busy meaning and disables convert while a suggestion runs", async () => {
    const wrapper = mountGroup(controlsFor(item("absent", { suggested: "gap_fill" })));

    expect(wrapper.get(SUGGEST).findComponent(UiGlyph).props("meaning")).toBe("ai-assist");
    expect(wrapper.get(SUGGEST).find("svg").classes()).not.toContain("xw-spin");
    expect(wrapper.get(SUGGEST).attributes("title")).toBe("Föreslå facit för frågan");

    await wrapper.setProps({ controls: controlsFor(item("absent", { suggested: "gap_fill" }), { busy: true }) });

    const glyph = wrapper.get(SUGGEST).findComponent(UiGlyph);
    expect(glyph.props("meaning")).toBe("busy");
    expect(glyph.classes()).toContain("xw-spin");
    expect(wrapper.get(SUGGEST).attributes("disabled")).toBeDefined();
    expect(wrapper.get(SUGGEST).attributes("title")).toBe("Facitförslaget tas fram …");
    expect(wrapper.get(CONVERT).attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });

  it("disables the suggest control with the door's note once the daily limit is reached", () => {
    const wrapper = mountGroup(controlsFor(item(), { limitNote: AI_APP_LIMIT_NOTE }));

    const suggest = wrapper.get(SUGGEST);
    expect(suggest.attributes("disabled")).toBeDefined();
    expect(suggest.attributes("title")).toBe(AI_APP_LIMIT_NOTE);
    expect(suggest.attributes("aria-description")).toBe(AI_APP_LIMIT_NOTE);
    wrapper.unmount();
  });
});
