/**
 * Exam workspace column resize handle.
 *
 * Expected behavior:
 *   A focusable role=separator handle on one desktop panel border. Bounds
 *   come only from a transient read of the closest .ws__body ancestor's
 *   computed gridTemplateColumns on focus and on pointerdown; nothing is
 *   measured at rest. Pointer drag emits set with the clamped rounded width
 *   (the list widens with +dx, the side panel with -dx); double-click emits
 *   reset; the keyboard follows the separator key mapping (arrows step,
 *   Home/End jump, Enter collapses, Shift+Enter resets), mirrored for the
 *   side edge. Null bounds make every input a no-op.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import { mount, type DOMWrapper, type VueWrapper } from "@vue/test-utils";

import ExamWorkspaceColumnHandle from "./ExamWorkspaceColumnHandle.vue";

const GRID = "260px 700px 320px";
const LIST_MAX = 260 + 700 - 400;
const SIDE_MAX = 320 + 700 - 400;

const containers: HTMLElement[] = [];
const mountedWrappers: VueWrapper[] = [];

function stubGridTemplateColumns(value: string): void {
  vi.spyOn(window, "getComputedStyle").mockReturnValue({
    gridTemplateColumns: value,
  } as CSSStyleDeclaration);
}

function mountHandle(props: {
  edge: "list" | "side";
  column: "list" | "drawer" | "preview";
  collapsible?: boolean;
}): VueWrapper {
  const container = document.createElement("div");
  container.className = "ws__body";
  document.body.appendChild(container);
  containers.push(container);
  const wrapper = mount(ExamWorkspaceColumnHandle, {
    attachTo: container,
    props: {
      controls: "exam-panel",
      label: "Ändra bredd på frågelistan",
      collapsible: true,
      ...props,
    },
  });
  mountedWrappers.push(wrapper);
  return wrapper;
}

function handleOf(wrapper: VueWrapper): DOMWrapper<Element> {
  return wrapper.find('[data-test^="exam-workspace-column-handle-"]');
}

/**
 * Dispatch a pointer lifecycle event with position details. Vue Test Utils
 * builds pointer triggers on MouseEvent, whose button is getter-only, so
 * the drag tests dispatch the event directly instead.
 */
async function pointer(
  handle: DOMWrapper<Element>,
  type: string,
  init: MouseEventInit,
): Promise<void> {
  handle.element.dispatchEvent(
    new MouseEvent(type, { bubbles: true, cancelable: true, ...init }),
  );
  await nextTick();
}

beforeEach(() => {
  HTMLElement.prototype.setPointerCapture = vi.fn();
  HTMLElement.prototype.releasePointerCapture = vi.fn();
  stubGridTemplateColumns(GRID);
});

afterEach(() => {
  for (const wrapper of mountedWrappers.splice(0)) {
    wrapper.unmount();
  }
  for (const container of containers.splice(0)) {
    container.remove();
  }
  vi.restoreAllMocks();
});

describe("ExamWorkspaceColumnHandle", () => {
  it("exposes separator semantics and bounds after focus on the list edge", async () => {
    const wrapper = mountHandle({ edge: "list", column: "list" });
    const handle = handleOf(wrapper);

    expect(handle.attributes("role")).toBe("separator");
    expect(handle.attributes("tabindex")).toBe("0");
    expect(handle.attributes("aria-orientation")).toBe("vertical");
    expect(handle.attributes("aria-controls")).toBe("exam-panel");
    expect(handle.attributes("aria-label")).toBe("Ändra bredd på frågelistan");
    expect(handle.attributes("data-test")).toBe("exam-workspace-column-handle-list");

    await handle.trigger("focus");

    expect(handle.attributes("aria-valuenow")).toBe("260");
    expect(handle.attributes("aria-valuemin")).toBe("260");
    expect(handle.attributes("aria-valuemax")).toBe(String(LIST_MAX));
    expect(handle.attributes("aria-valuetext")).toBe("260 px");
  });

  it("reports side bounds from the third track after focus", async () => {
    const wrapper = mountHandle({ edge: "side", column: "drawer" });
    const handle = handleOf(wrapper);

    await handle.trigger("focus");

    expect(handle.attributes("data-test")).toBe("exam-workspace-column-handle-side");
    expect(handle.attributes("aria-valuenow")).toBe("320");
    expect(handle.attributes("aria-valuemin")).toBe("300");
    expect(handle.attributes("aria-valuemax")).toBe(String(SIDE_MAX));
  });

  it("widens the list with ArrowRight and the side panel with ArrowLeft", async () => {
    const list = mountHandle({ edge: "list", column: "list" });
    await handleOf(list).trigger("keydown", { key: "ArrowRight", shiftKey: false });
    expect(list.emitted("set")).toEqual([[276]]);

    const side = mountHandle({ edge: "side", column: "drawer" });
    await handleOf(side).trigger("keydown", { key: "ArrowLeft", shiftKey: false });
    expect(side.emitted("set")).toEqual([[336]]);
  });

  it("steps 64 px with Shift held", async () => {
    const wrapper = mountHandle({ edge: "list", column: "list" });
    await handleOf(wrapper).trigger("keydown", { key: "ArrowRight", shiftKey: true });
    expect(wrapper.emitted("set")).toEqual([[324]]);
  });

  it("jumps to max on End and to min on Home", async () => {
    const wrapper = mountHandle({ edge: "list", column: "list" });
    const handle = handleOf(wrapper);

    await handle.trigger("keydown", { key: "End", shiftKey: false });
    await handle.trigger("keydown", { key: "Home", shiftKey: false });

    expect(wrapper.emitted("set")).toEqual([[LIST_MAX], [260]]);
  });

  it("emits toggle-collapse on Enter and reset on Shift+Enter and double-click", async () => {
    const wrapper = mountHandle({ edge: "list", column: "list" });
    const handle = handleOf(wrapper);

    await handle.trigger("keydown", { key: "Enter", shiftKey: false });
    await handle.trigger("keydown", { key: "Enter", shiftKey: true });
    await handle.trigger("dblclick");

    expect(wrapper.emitted("toggle-collapse")).toEqual([[]]);
    expect(wrapper.emitted("reset")).toEqual([[], []]);
  });

  it("ignores Enter when not collapsible", async () => {
    const wrapper = mountHandle({ edge: "list", column: "list", collapsible: false });

    await handleOf(wrapper).trigger("keydown", { key: "Enter", shiftKey: false });

    expect(wrapper.emitted("toggle-collapse")).toBeUndefined();
  });

  it("drags the list wider with +dx", async () => {
    const wrapper = mountHandle({ edge: "list", column: "list" });
    const handle = handleOf(wrapper);

    await pointer(handle, "pointerdown", { button: 0, clientX: 100 });
    await pointer(handle, "pointermove", { clientX: 200 });

    expect(wrapper.emitted("set")).toEqual([[360]]);
    expect(handle.attributes("aria-valuenow")).toBe("360");
  });

  it("drags the side panel wider with -dx", async () => {
    const wrapper = mountHandle({ edge: "side", column: "drawer" });
    const handle = handleOf(wrapper);

    await pointer(handle, "pointerdown", { button: 0, clientX: 300 });
    await pointer(handle, "pointermove", { clientX: 200 });

    expect(wrapper.emitted("set")).toEqual([[420]]);
  });

  it("clamps a drag beyond the maximum", async () => {
    const wrapper = mountHandle({ edge: "list", column: "list" });
    const handle = handleOf(wrapper);

    await pointer(handle, "pointerdown", { button: 0, clientX: 100 });
    await pointer(handle, "pointermove", { clientX: 1000 });

    expect(wrapper.emitted("set")).toEqual([[LIST_MAX]]);
  });

  it("stops emitting after pointerup", async () => {
    const wrapper = mountHandle({ edge: "list", column: "list" });
    const handle = handleOf(wrapper);

    await pointer(handle, "pointerdown", { button: 0, clientX: 100 });
    await pointer(handle, "pointermove", { clientX: 200 });
    await pointer(handle, "pointerup", { clientX: 200 });
    await pointer(handle, "pointermove", { clientX: 300 });

    expect(wrapper.emitted("set")).toEqual([[360]]);
  });

  it("ignores a non-primary pointer button", async () => {
    const wrapper = mountHandle({ edge: "list", column: "list" });
    const handle = handleOf(wrapper);

    await pointer(handle, "pointerdown", { button: 2, clientX: 100 });
    await pointer(handle, "pointermove", { clientX: 200 });

    expect(wrapper.emitted("set")).toBeUndefined();
  });

  it("makes every input a no-op when bounds are null", async () => {
    stubGridTemplateColumns("260px 1fr 320px");
    const wrapper = mountHandle({ edge: "list", column: "list" });
    const handle = handleOf(wrapper);

    await handle.trigger("focus");
    await handle.trigger("keydown", { key: "ArrowRight", shiftKey: false });
    await handle.trigger("keydown", { key: "Enter", shiftKey: false });
    await pointer(handle, "pointerdown", { button: 0, clientX: 100 });
    await pointer(handle, "pointermove", { clientX: 200 });
    await handle.trigger("dblclick");

    expect(handle.attributes("aria-valuenow")).toBeUndefined();
    expect(wrapper.emitted("set")).toBeUndefined();
    expect(wrapper.emitted("reset")).toBeUndefined();
    expect(wrapper.emitted("toggle-collapse")).toBeUndefined();
  });
});
