/**
 * Exam workspace item drawer behavior.
 *
 * Expected behavior:
 *   On phone the drawer is a modal dialog: focus moves into it on open, Tab
 *   and Shift+Tab cycle inside it, and focus returns to the opener when it
 *   closes. On tablet focus moves in and returns, without trapping Tab. On
 *   desktop the drawer leaves focus where it was. A review question with a
 *   stored conversion source shows the labeler's first type in a selector
 *   and a "Konvertera igen" button that emits the kept or changed type.
 */

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceItemDrawer from "./ExamWorkspaceItemDrawer.vue";
import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";

const ITEM: NativeExamItem = {
  ai_suggestion: null,
  facit_text: null,
  marking_guide: null,
  printed_label: null,
  retry_source: null,
  answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
  body: [{ segments: [{ kind: "text", text: "Beskriv vattnets kretslopp." }] }],
  choices: [],
  gaps: [],
  item_id: "item_001",
  kind: "free_text",
  match_left: [],
  match_right: [],
  points: 2,
  points_estimated: false,
  review: {
    confidence: 0.9,
    parse_origin: "deterministic",
    reasons: [],
    state: "review_complete",
  },
  sequence: 1,
  source_anchor: null,
};

const RETRY_SOURCE: NonNullable<NativeExamItem["retry_source"]> = {
  chunks: [
    {
      anchor: "body:0001",
      images: [],
      missing_images: [],
      kind: "question",
      marked_text: "Beskriv vattnets kretslopp.",
      text: "Beskriv vattnets kretslopp.",
    },
  ],
  context_chunks: [],
  key_chunks: [],
  label_kind: "gap_fill",
};

const RETRY_ITEM: NativeExamItem = {
  ...ITEM,
  review: {
    confidence: 0.4,
    parse_origin: "llm_parsed",
    reasons: ["osäker tolkning"],
    state: "review_required",
  },
  retry_source: RETRY_SOURCE,
};

let opener: HTMLButtonElement | null = null;

async function mountDrawer(
  layout: ExamWorkspaceLayout,
  overrides: Partial<{ disabled: boolean; item: NativeExamItem }> = {},
) {
  opener = document.createElement("button");
  document.body.append(opener);
  opener.focus();
  const wrapper = mount(ExamWorkspaceItemDrawer, {
    attachTo: document.body,
    props: {
      disabled: false,
      item: ITEM,
      ...overrides,
      layout,
      readiness: [],
      serverBlockers: [],
    },
  });
  await nextTick();
  return wrapper;
}

function pressTab(shiftKey = false): KeyboardEvent {
  const event = new KeyboardEvent("keydown", {
    bubbles: true,
    cancelable: true,
    key: "Tab",
    shiftKey,
  });
  document.activeElement?.dispatchEvent(event);
  return event;
}

afterEach(() => {
  opener?.remove();
  opener = null;
});

describe("ExamWorkspaceItemDrawer focus", () => {
  it("moves focus into the phone dialog, keeps Tab inside, and returns focus on close", async () => {
    const wrapper = await mountDrawer("phone");
    const frame = wrapper.get('[data-test="exam-workspace-item-drawer-frame"]').element;
    const close = wrapper.get('[data-test="exam-workspace-item-drawer-close"]').element;

    expect(document.activeElement).toBe(frame);

    (close as HTMLElement).focus();
    const forward = pressTab();
    expect(forward.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(close);

    const backward = pressTab(true);
    expect(backward.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(close);

    wrapper.unmount();
    expect(document.activeElement).toBe(opener);
  });

  it("moves focus into the tablet overlay without trapping Tab", async () => {
    const wrapper = await mountDrawer("tablet");
    const frame = wrapper.get('[data-test="exam-workspace-item-drawer-frame"]').element;

    expect(document.activeElement).toBe(frame);
    expect(pressTab().defaultPrevented).toBe(false);

    wrapper.unmount();
    expect(document.activeElement).toBe(opener);
  });

  it("returns focus to the Detaljer toggle when the opener held no focus", async () => {
    const toggle = document.createElement("button");
    toggle.setAttribute("data-test", "exam-workspace-item-details-toggle");
    document.body.append(toggle);
    (document.activeElement as HTMLElement | null)?.blur();
    const wrapper = mount(ExamWorkspaceItemDrawer, {
      attachTo: document.body,
      props: {
        disabled: false,
        item: ITEM,
        layout: "tablet",
        readiness: [],
        serverBlockers: [],
      },
    });
    await nextTick();
    const frame = wrapper.get('[data-test="exam-workspace-item-drawer-frame"]').element;
    expect(document.activeElement).toBe(frame);

    frame.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Escape" }));
    expect(wrapper.emitted("close")).toHaveLength(1);
    wrapper.unmount();

    expect(document.activeElement).toBe(toggle);
    toggle.remove();
  });

  it("starts the focus contract when the layout changes from desktop to tablet", async () => {
    const wrapper = await mountDrawer("desktop");
    expect(document.activeElement).toBe(opener);

    await wrapper.setProps({ layout: "tablet" });
    await nextTick();
    const frame = wrapper.get('[data-test="exam-workspace-item-drawer-frame"]').element;
    expect(frame.getAttribute("tabindex")).toBe("-1");
    expect(document.activeElement).toBe(frame);

    wrapper.unmount();
    expect(document.activeElement).toBe(opener);
  });

  it("answers Tab as a modal when the layout changes to phone", async () => {
    const wrapper = await mountDrawer("tablet");
    expect(pressTab().defaultPrevented).toBe(false);

    await wrapper.setProps({ layout: "phone" });
    expect(wrapper.get('[data-test="exam-workspace-item-drawer-frame"]').attributes("role")).toBe(
      "dialog",
    );
    (wrapper.get('[data-test="exam-workspace-item-drawer-close"]').element as HTMLElement).focus();
    expect(pressTab().defaultPrevented).toBe(true);
    wrapper.unmount();
  });

  it("paints the tablet and phone overlays with an opaque surface", async () => {
    for (const layout of ["tablet", "phone"] as const) {
      const wrapper = await mountDrawer(layout);
      const classes = wrapper.get('[data-test="exam-workspace-item-drawer-frame"]').classes();
      expect(classes).toContain("bg-modal");
      expect(classes).not.toContain("bg-panel");
      wrapper.unmount();
    }
  });

  it("names the parse notes by review state", async () => {
    const reasons = { ...ITEM.review, reasons: ["machine_proposed_answer_key"] };
    const required = await mountDrawer("desktop", {
      item: { ...ITEM, review: { ...reasons, state: "review_required" } },
    });
    expect(required.text()).toContain("Att granska");
    required.unmount();

    const reviewed = await mountDrawer("desktop", {
      item: { ...ITEM, review: { ...reasons, state: "review_complete" } },
    });
    expect(reviewed.text()).not.toContain("Att granska");
    expect(reviewed.text()).toContain("Anteckningar från inläsningen");
    expect(reviewed.get('[data-test="exam-workspace-review-reasons"]').text()).toContain(
      "Facit är ett maskinellt förslag",
    );
    reviewed.unmount();
  });

  it("leaves focus where it was on desktop", async () => {
    const wrapper = await mountDrawer("desktop");

    expect(document.activeElement).toBe(opener);
    wrapper.unmount();
  });
});

describe("ExamWorkspaceItemDrawer retry control", () => {
  it("shows the labeler's first type and emits it with the question id", async () => {
    const wrapper = await mountDrawer("desktop", { item: RETRY_ITEM });

    const select = wrapper.get<HTMLSelectElement>('[data-test="exam-workspace-retry-kind"]');
    expect(select.element.value).toBe("gap_fill");

    await wrapper.get('[data-test="exam-workspace-retry-button"]').trigger("click");

    expect(wrapper.emitted("retry")).toEqual([["item_001", "gap_fill"]]);
  });

  it("offers the five converter types with the Swedish type labels", async () => {
    const wrapper = await mountDrawer("desktop", { item: RETRY_ITEM });

    const options = wrapper.findAll<HTMLOptionElement>(
      '[data-test="exam-workspace-retry-kind"] option',
    );
    expect(options.map((option) => [option.element.value, option.text()])).toEqual([
      ["free_text", "Fritext"],
      ["single_choice", "Flerval: ett val"],
      ["multiple_response", "Flerval: flera val"],
      ["gap_fill", "Lucktext"],
      ["matching", "Matchning"],
    ]);
  });

  it("emits the type the teacher changes to", async () => {
    const wrapper = await mountDrawer("desktop", { item: RETRY_ITEM });

    await wrapper.get('[data-test="exam-workspace-retry-kind"]').setValue("multiple_response");
    await wrapper.get('[data-test="exam-workspace-retry-button"]').trigger("click");

    expect(wrapper.emitted("retry")).toEqual([["item_001", "multiple_response"]]);
  });

  it("keeps the chosen type when a reply replaces the same question", async () => {
    const wrapper = await mountDrawer("desktop", { item: RETRY_ITEM });

    await wrapper.get('[data-test="exam-workspace-retry-kind"]').setValue("matching");
    await wrapper.setProps({ item: { ...RETRY_ITEM, kind: "free_text" } });

    expect(
      wrapper.get<HTMLSelectElement>('[data-test="exam-workspace-retry-kind"]').element.value,
    ).toBe("matching");
  });

  it("resets to the next question's label type", async () => {
    const wrapper = await mountDrawer("desktop", { item: RETRY_ITEM });

    await wrapper.get('[data-test="exam-workspace-retry-kind"]').setValue("matching");
    await wrapper.setProps({
      item: {
        ...RETRY_ITEM,
        item_id: "item_002",
        retry_source: { ...RETRY_SOURCE, label_kind: "single_choice" },
      },
    });

    expect(
      wrapper.get<HTMLSelectElement>('[data-test="exam-workspace-retry-kind"]').element.value,
    ).toBe("single_choice");
  });

  it("shows no retry control without a stored source or outside review", async () => {
    const withoutSource = await mountDrawer("desktop", {
      item: { ...RETRY_ITEM, retry_source: null },
    });
    expect(withoutSource.find('[data-test="exam-workspace-retry"]').exists()).toBe(false);
    withoutSource.unmount();

    const reviewed = await mountDrawer("desktop", {
      item: { ...RETRY_ITEM, review: { ...RETRY_ITEM.review, state: "review_complete" } },
    });
    expect(reviewed.find('[data-test="exam-workspace-retry"]').exists()).toBe(false);
    reviewed.unmount();

    const plain = await mountDrawer("desktop");
    expect(plain.find('[data-test="exam-workspace-retry"]').exists()).toBe(false);
  });

  it("disables the selector and button while the drawer is disabled and emits nothing", async () => {
    const wrapper = await mountDrawer("desktop", { disabled: true, item: RETRY_ITEM });

    expect(
      wrapper.get('[data-test="exam-workspace-retry-kind"]').attributes("disabled"),
    ).toBeDefined();
    const button = wrapper.get('[data-test="exam-workspace-retry-button"]');
    expect(button.attributes("disabled")).toBeDefined();

    await button.trigger("click");

    expect(wrapper.emitted("retry")).toBeUndefined();
  });
});
