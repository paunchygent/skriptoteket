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

async function mountDrawer(layout: ExamWorkspaceLayout) {
  opener = document.createElement("button");
  document.body.append(opener);
  opener.focus();
  const wrapper = mount(ExamWorkspaceItemDrawer, {
    attachTo: document.body,
    props: {
      disabled: false,
      item: ITEM,
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

  it("leaves focus where it was on desktop", async () => {
    const wrapper = await mountDrawer("desktop");

    expect(document.activeElement).toBe(opener);
    wrapper.unmount();
  });
});
