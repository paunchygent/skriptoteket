/**
 * ExamWorkspaceMenu keyboard navigation across split rows.
 *
 * Expected behavior (TASK-SKRIPT-40-04-16 L5):
 *   A row is either a `role="group"` holding that row's entries or a
 *   standalone entry. ArrowUp/ArrowDown move between rows keeping the part
 *   column and wrapping at both ends; ArrowLeft/ArrowRight move between the
 *   parts of one group row and stop at its ends, while a standalone entry
 *   keeps its caret keys; Home/End move to the first and last row; opening
 *   focuses the first part of the first row; Escape closes and returns focus
 *   to the anchor; Tab closes without restoring focus.
 *
 * The menu teleports to document.body, so parts are found through `document`
 * rather than the wrapper, and keys arrive as bubbling DOM events from the
 * focused part, as in a browser.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { h, nextTick } from "vue";
import type { VNode } from "vue";

import ExamWorkspaceMenu from "./ExamWorkspaceMenu.vue";

const mounted: VueWrapper[] = [];

function menuPart(testId: string, label: string, attrs: Record<string, unknown> = {}): VNode {
  return h(
    "button",
    { type: "button", class: "xw-mi", role: "menuitem", "data-test": testId, ...attrs },
    label,
  );
}

function groupRow(label: string, children: VNode[]): VNode {
  return h("div", { role: "group", "aria-label": label }, children);
}

function splitRows(): VNode[] {
  return [
    groupRow("Format A", [menuPart("row-a-1", "A1"), menuPart("row-a-2", "A2")]),
    groupRow("Format B", [menuPart("row-b-1", "B1"), menuPart("row-b-2", "B2")]),
    groupRow("Format C", [menuPart("row-c-1", "C1")]),
    groupRow("Format D", [menuPart("row-d-1", "D1"), menuPart("row-d-2", "D2", { "aria-disabled": "true" })]),
    menuPart("row-e-1", "E1"),
  ];
}

function standaloneRows(): VNode[] {
  return [menuPart("solo-1", "S1"), menuPart("solo-2", "S2"), menuPart("solo-3", "S3")];
}

async function openMenu(children: VNode[]): Promise<{ wrapper: VueWrapper; anchor: HTMLButtonElement }> {
  const anchor = document.createElement("button");
  anchor.type = "button";
  anchor.dataset.test = "menu-anchor";
  anchor.textContent = "Trigger";
  document.body.appendChild(anchor);
  const wrapper = mount(ExamWorkspaceMenu, {
    attachTo: document.body,
    props: { anchor, label: "Testmenu", open: true },
    slots: { default: () => children },
  });
  mounted.push(wrapper);
  await nextTick();
  await nextTick();
  await nextTick();
  return { wrapper, anchor };
}

function part(testId: string): HTMLButtonElement {
  const candidate = document.body.querySelector(`[data-test="${testId}"]`);
  if (!(candidate instanceof HTMLButtonElement)) {
    throw new Error(`menu part ${testId} did not mount`);
  }
  return candidate;
}

function press(target: HTMLElement, key: string): KeyboardEvent {
  const event = new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key });
  target.dispatchEvent(event);
  return event;
}

afterEach(() => {
  while (mounted.length > 0) {
    mounted.pop()?.unmount();
  }
  document.body.replaceChildren();
});

describe("ExamWorkspaceMenu keyboard across split rows", () => {
  it("moves Down between rows keeping the column", async () => {
    await openMenu(splitRows());
    part("row-a-2").focus();

    press(part("row-a-2"), "ArrowDown");
    expect(document.activeElement).toBe(part("row-b-2"));
  });

  it("lands on the first part when the next row is shorter", async () => {
    await openMenu(splitRows());
    part("row-b-2").focus();

    press(part("row-b-2"), "ArrowDown");
    expect(document.activeElement).toBe(part("row-c-1"));
  });

  it("moves Down past a disabled part's row onto the standalone entry and wraps", async () => {
    await openMenu(splitRows());
    part("row-d-1").focus();

    press(part("row-d-1"), "ArrowDown");
    expect(document.activeElement).toBe(part("row-e-1"));

    press(part("row-e-1"), "ArrowDown");
    expect(document.activeElement).toBe(part("row-a-1"));
  });

  it("moves Up to the previous row keeping the column and wraps to the last row", async () => {
    await openMenu(splitRows());
    part("row-b-2").focus();

    press(part("row-b-2"), "ArrowUp");
    expect(document.activeElement).toBe(part("row-a-2"));

    press(part("row-a-2"), "ArrowUp");
    expect(document.activeElement).toBe(part("row-e-1"));

    part("row-a-1").focus();
    press(part("row-a-1"), "ArrowUp");
    expect(document.activeElement).toBe(part("row-e-1"));
  });

  it("moves Right and Left inside a group row and stops at its ends", async () => {
    await openMenu(splitRows());
    part("row-a-1").focus();

    const right = press(part("row-a-1"), "ArrowRight");
    expect(right.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(part("row-a-2"));

    const rightAgain = press(part("row-a-2"), "ArrowRight");
    expect(rightAgain.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(part("row-a-2"));

    const left = press(part("row-a-2"), "ArrowLeft");
    expect(left.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(part("row-a-1"));

    const leftAgain = press(part("row-a-1"), "ArrowLeft");
    expect(leftAgain.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(part("row-a-1"));
  });

  it("leaves Left and Right alone on a standalone entry so caret keys keep working", async () => {
    await openMenu(splitRows());
    part("row-e-1").focus();

    const right = press(part("row-e-1"), "ArrowRight");
    expect(right.defaultPrevented).toBe(false);
    expect(document.activeElement).toBe(part("row-e-1"));

    const left = press(part("row-e-1"), "ArrowLeft");
    expect(left.defaultPrevented).toBe(false);
    expect(document.activeElement).toBe(part("row-e-1"));
  });

  it("stays on the enabled part when the neighbour in its row is disabled", async () => {
    await openMenu(splitRows());
    part("row-d-1").focus();

    press(part("row-d-1"), "ArrowRight");
    expect(document.activeElement).toBe(part("row-d-1"));
  });

  it("moves Home and End to the first and last row", async () => {
    await openMenu(splitRows());
    part("row-b-2").focus();

    press(part("row-b-2"), "Home");
    expect(document.activeElement).toBe(part("row-a-1"));

    press(part("row-a-1"), "End");
    expect(document.activeElement).toBe(part("row-e-1"));
  });

  it("focuses the first part of the first row on open", async () => {
    await openMenu(splitRows());
    expect(document.activeElement).toBe(part("row-a-1"));
  });

  it("cycles a menu of only standalone entries with Up and Down", async () => {
    await openMenu(standaloneRows());
    expect(document.activeElement).toBe(part("solo-1"));

    press(part("solo-1"), "ArrowDown");
    expect(document.activeElement).toBe(part("solo-2"));

    press(part("solo-2"), "ArrowDown");
    expect(document.activeElement).toBe(part("solo-3"));

    press(part("solo-3"), "ArrowDown");
    expect(document.activeElement).toBe(part("solo-1"));

    press(part("solo-1"), "ArrowUp");
    expect(document.activeElement).toBe(part("solo-3"));
  });

  it("closes on Escape and returns focus to the anchor", async () => {
    const { wrapper, anchor } = await openMenu(splitRows());
    part("row-b-1").focus();

    press(part("row-b-1"), "Escape");
    await nextTick();
    await nextTick();

    expect(wrapper.emitted("close")).toEqual([[true]]);
    expect(document.activeElement).toBe(anchor);
  });

  it("closes on Tab without restoring focus", async () => {
    const { wrapper } = await openMenu(splitRows());
    part("row-a-1").focus();

    press(part("row-a-1"), "Tab");
    await nextTick();

    expect(wrapper.emitted("close")).toEqual([[false]]);
  });
});
