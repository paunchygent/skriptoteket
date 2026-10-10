/**
 * Exam workspace item drawer focus handling.
 *
 * Expected behavior:
 *   On phone the drawer is a modal dialog: focus moves into it on open, Tab
 *   and Shift+Tab cycle inside it, and focus returns to the opener when it
 *   closes. On tablet focus moves in and returns, without trapping Tab. On
 *   desktop the drawer leaves focus where it was.
 */

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceItemDrawer from "./ExamWorkspaceItemDrawer.vue";
import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";

const ITEM: NativeExamItem = {
  answer_key: { correct_choice_ids: [], origin: "not_applicable" },
  body: [{ segments: [{ kind: "text", text: "Beskriv vattnets kretslopp." }] }],
  choices: [],
  gaps: [],
  item_id: "item_001",
  kind: "free_text",
  points: 2,
  review: {
    confidence: 0.9,
    parse_origin: "deterministic",
    reasons: [],
    state: "review_complete",
  },
  sequence: 1,
  source_anchor: null,
  title: "Kretslopp",
};

let opener: HTMLButtonElement | null = null;

async function mountDrawer(
  layout: ExamWorkspaceLayout,
  overrides: Partial<{ item: NativeExamItem }> = {},
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
      proposedItem: null,
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
        proposedItem: null,
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
    const reasons = { ...ITEM.review, reasons: ["missing_points"] };
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
      "Poäng saknas",
    );
    reviewed.unmount();
  });

  it("leaves focus where it was on desktop", async () => {
    const wrapper = await mountDrawer("desktop");

    expect(document.activeElement).toBe(opener);
    wrapper.unmount();
  });
});
