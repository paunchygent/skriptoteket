/**
 * Exam workspace column resize handle.
 *
 * Expected behavior:
 *   A focusable role=separator handle on one desktop panel border. Bounds
 *   come only from transient reads: the resolved gridTemplateColumns of the
 *   closest .ws__body ancestor, and the CSS-owned minimums (--xw-<column>-min
 *   and --xw-editor-min) of the closest .xw-root ancestor, parsed as px. Any
 *   missing minimum gives null bounds. Bounds are read and applied on mount
 *   (after nextTick), on focus, after every emitted key/double-click set,
 *   reset and toggle-collapse (nextTick, then read again), and when the
 *   collapsed prop changes. A ResizeObserver on the closest .ws__body and
 *   each of its element children re-reads the bounds on every track change;
 *   the callback only updates the separator values and never emits.
 *   Pointer drag emits set with the
 *   clamped rounded width (the list widens with +dx, the side panel with -dx);
 *   the drag holds its pointerdown bounds. Double-click emits reset; the
 *   keyboard follows the separator key mapping (arrows step, Home/End jump,
 *   Enter collapses, Shift+Enter resets), mirrored for the side edge. Null
 *   bounds make every input a no-op. The side edge reads the last track, so a
 *   two-track [editor, side] grid works. With collapsed the separator reports
 *   the rail: aria-valuenow/min are the rail track width, aria-valuemax is the
 *   normal max, and aria-valuetext is "Dold".
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import { mount, type DOMWrapper, type VueWrapper } from "@vue/test-utils";

import ExamWorkspaceColumnHandle from "./ExamWorkspaceColumnHandle.vue";

const GRID = "260px 700px 320px";
const LIST_MAX = 260 + 700 - 400;
const SIDE_MAX = 320 + 700 - 400;

type MinimumName = "--xw-list-min" | "--xw-drawer-min" | "--xw-preview-min" | "--xw-editor-min";

const DEFAULT_MINIMUMS: Record<MinimumName, string> = {
  "--xw-list-min": "260px",
  "--xw-drawer-min": "300px",
  "--xw-preview-min": "300px",
  "--xw-editor-min": "400px",
};

const containers: HTMLElement[] = [];
const mountedWrappers: VueWrapper[] = [];

/**
 * A typed ResizeObserver double: jsdom has no ResizeObserver, so the spec
 * installs this class and fires the callback by hand. It records every
 * observed target, mirroring the sharedSegmentedToggle.spec.ts pattern.
 */
class HandleResizeObserver implements ResizeObserver {
  static instances: HandleResizeObserver[] = [];
  readonly targets = new Set<Element>();
  readonly disconnect = vi.fn((): void => {
    this.targets.clear();
  });

  constructor(private readonly callback: ResizeObserverCallback) {
    HandleResizeObserver.instances.push(this);
  }

  observe(target: Element): void {
    this.targets.add(target);
  }

  unobserve(target: Element): void {
    this.targets.delete(target);
  }

  fire(): void {
    this.callback([], this);
  }
}

function latestObserver(): HandleResizeObserver {
  const observer = HandleResizeObserver.instances.at(-1);
  if (observer === undefined) {
    throw new Error("expected a ResizeObserver instance");
  }
  return observer;
}

function bodyOf(wrapper: VueWrapper): HTMLElement {
  const candidate = wrapper.element.closest(".ws__body");
  if (!(candidate instanceof HTMLElement)) {
    throw new Error("expected the handle to sit inside a .ws__body");
  }
  return candidate;
}

/**
 * A typed computed-style mock: a real CSSStyleDeclaration carrying the grid
 * tracks and the CSS-owned minimums, so no type assertion is needed.
 */
function stubComputedStyle(grid: string, overrides: Partial<Record<MinimumName, string>> = {}): void {
  const style = document.createElement("div").style;
  style.gridTemplateColumns = grid;
  const merged: Record<MinimumName, string> = { ...DEFAULT_MINIMUMS, ...overrides };
  for (const [name, value] of Object.entries(merged)) {
    if (value === "") {
      style.removeProperty(name);
    } else {
      style.setProperty(name, value);
    }
  }
  vi.spyOn(window, "getComputedStyle").mockReturnValue(style);
}

function mountHandle(props: {
  edge: "list" | "side";
  column: "list" | "drawer" | "preview";
  collapsible?: boolean;
  collapsed?: boolean;
}): VueWrapper {
  const container = document.createElement("div");
  container.className = "xw-root ws__body";
  document.body.appendChild(container);
  containers.push(container);
  const wrapper = mount(ExamWorkspaceColumnHandle, {
    attachTo: container,
    props: {
      controls: "exam-panel",
      label: "Ändra bredd på frågelistan",
      collapsible: true,
      collapsed: false,
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
 * builds pointer triggers on MouseEvent, whose button is getter-only, so the
 * drag tests dispatch the event directly instead.
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
  HandleResizeObserver.instances = [];
  vi.stubGlobal("ResizeObserver", HandleResizeObserver);
  stubComputedStyle(GRID);
});

afterEach(() => {
  for (const wrapper of mountedWrappers.splice(0)) {
    wrapper.unmount();
  }
  for (const container of containers.splice(0)) {
    container.remove();
  }
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("ExamWorkspaceColumnHandle", () => {
  it("announces separator bounds after mount without waiting for focus", async () => {
    const wrapper = mountHandle({ edge: "list", column: "list" });
    await nextTick();
    await nextTick();

    const handle = handleOf(wrapper);
    expect(handle.attributes("aria-valuenow")).toBe("260");
    expect(handle.attributes("aria-valuemin")).toBe("260");
    expect(handle.attributes("aria-valuemax")).toBe(String(LIST_MAX));
    expect(handle.attributes("aria-valuetext")).toBe("260 px");
  });

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

  it("announces the rail when collapsed", async () => {
    stubComputedStyle("44px 700px 320px");
    const wrapper = mountHandle({ edge: "list", column: "list", collapsed: true });
    await nextTick();
    await nextTick();

    const handle = handleOf(wrapper);
    expect(handle.attributes("aria-valuenow")).toBe("44");
    expect(handle.attributes("aria-valuemin")).toBe("44");
    expect(handle.attributes("aria-valuemax")).toBe(String(44 + 700 - 400));
    expect(handle.attributes("aria-valuetext")).toBe("Dold");
  });

  it("drives the side handle over a two-track editor/side grid", async () => {
    stubComputedStyle("700px 320px");
    const wrapper = mountHandle({ edge: "side", column: "drawer" });
    const handle = handleOf(wrapper);

    await handle.trigger("focus");
    expect(handle.attributes("aria-valuenow")).toBe("320");

    await handle.trigger("keydown", { key: "ArrowLeft", shiftKey: false });
    expect(wrapper.emitted("set")).toEqual([[336]]);

    await pointer(handle, "pointerdown", { button: 0, clientX: 300 });
    await pointer(handle, "pointermove", { clientX: 200 });
    expect(wrapper.emitted("set")).toEqual([[336], [420]]);
  });

  it("clamps a drag at the CSS-owned list minimum", async () => {
    stubComputedStyle(GRID, { "--xw-list-min": "280px" });
    const wrapper = mountHandle({ edge: "list", column: "list" });
    const handle = handleOf(wrapper);

    await pointer(handle, "pointerdown", { button: 0, clientX: 100 });
    await pointer(handle, "pointermove", { clientX: 0 });

    expect(wrapper.emitted("set")).toEqual([[280]]);
  });

  it("re-reads the grid after Shift+Enter reset", async () => {
    stubComputedStyle("500px 700px 320px");
    const wrapper = mountHandle({ edge: "list", column: "list" });
    const handle = handleOf(wrapper);

    await handle.trigger("focus");
    expect(handle.attributes("aria-valuenow")).toBe("500");

    stubComputedStyle(GRID);
    await handle.trigger("keydown", { key: "Enter", shiftKey: true });
    await nextTick();

    expect(wrapper.emitted("reset")).toEqual([[]]);
    expect(handle.attributes("aria-valuenow")).toBe("260");
  });

  it("observes the body and each body child on mount", async () => {
    const wrapper = mountHandle({ edge: "list", column: "list" });
    await nextTick();
    await nextTick();

    const observer = latestObserver();
    const body = bodyOf(wrapper);
    expect(body.classList.contains("ws__body")).toBe(true);
    expect(observer.targets.has(body)).toBe(true);
    for (const child of Array.from(body.children)) {
      expect(observer.targets.has(child)).toBe(true);
    }
  });

  it("follows new tracks when the observer fires, without emitting", async () => {
    const list = mountHandle({ edge: "list", column: "list" });
    const side = mountHandle({ edge: "side", column: "drawer" });
    await nextTick();
    await nextTick();

    stubComputedStyle("300px 500px 200px");
    for (const observer of HandleResizeObserver.instances) {
      observer.fire();
    }
    await nextTick();

    const listHandle = handleOf(list);
    expect(listHandle.attributes("aria-valuenow")).toBe("300");
    expect(listHandle.attributes("aria-valuemax")).toBe(String(300 + 500 - 400));
    const sideHandle = handleOf(side);
    expect(sideHandle.attributes("aria-valuenow")).toBe("200");
    expect(sideHandle.attributes("aria-valuemax")).toBe(String(200 + 500 - 400));
    expect(list.emitted("set")).toBeUndefined();
    expect(list.emitted("reset")).toBeUndefined();
    expect(side.emitted("set")).toBeUndefined();
    expect(side.emitted("reset")).toBeUndefined();
  });

  it("picks up body children added after mount and disconnects on unmount", async () => {
    const wrapper = mountHandle({ edge: "list", column: "list" });
    await nextTick();
    await nextTick();

    const observer = latestObserver();
    const body = bodyOf(wrapper);
    const late = document.createElement("section");
    body.appendChild(late);
    expect(observer.targets.has(late)).toBe(false);

    observer.fire();
    expect(observer.targets.has(late)).toBe(true);

    body.removeChild(late);
    observer.fire();
    expect(observer.targets.has(late)).toBe(false);

    mountedWrappers.splice(mountedWrappers.indexOf(wrapper), 1);
    wrapper.unmount();
    expect(observer.disconnect).toHaveBeenCalledOnce();
  });

  it("narrows the list with ArrowLeft", async () => {
    stubComputedStyle("500px 700px 320px");
    const wrapper = mountHandle({ edge: "list", column: "list" });
    await handleOf(wrapper).trigger("keydown", { key: "ArrowLeft", shiftKey: false });
    expect(wrapper.emitted("set")).toEqual([[484]]);
  });

  it("mirrors ArrowRight to narrow the side panel", async () => {
    const wrapper = mountHandle({ edge: "side", column: "drawer" });
    await handleOf(wrapper).trigger("keydown", { key: "ArrowRight", shiftKey: false });
    expect(wrapper.emitted("set")).toEqual([[304]]);
  });

  it("steps 64 px with Shift held in both directions", async () => {
    const list = mountHandle({ edge: "list", column: "list" });
    await handleOf(list).trigger("keydown", { key: "ArrowLeft", shiftKey: true });
    expect(list.emitted("set")).toEqual([[260]]);

    const side = mountHandle({ edge: "side", column: "drawer" });
    await handleOf(side).trigger("keydown", { key: "ArrowLeft", shiftKey: true });
    expect(side.emitted("set")).toEqual([[384]]);
  });

  it("widens the list with ArrowRight and the side panel with ArrowLeft", async () => {
    const list = mountHandle({ edge: "list", column: "list" });
    await handleOf(list).trigger("keydown", { key: "ArrowRight", shiftKey: false });
    expect(list.emitted("set")).toEqual([[276]]);

    const side = mountHandle({ edge: "side", column: "drawer" });
    await handleOf(side).trigger("keydown", { key: "ArrowLeft", shiftKey: false });
    expect(side.emitted("set")).toEqual([[336]]);
  });

  it("jumps the side panel to max on End and to min on Home", async () => {
    const wrapper = mountHandle({ edge: "side", column: "drawer" });
    const handle = handleOf(wrapper);

    await handle.trigger("keydown", { key: "End", shiftKey: false });
    await handle.trigger("keydown", { key: "Home", shiftKey: false });

    expect(wrapper.emitted("set")).toEqual([[SIDE_MAX], [300]]);
  });

  it("emits toggle-collapse on Enter for the side handle", async () => {
    const wrapper = mountHandle({ edge: "side", column: "drawer" });

    await handleOf(wrapper).trigger("keydown", { key: "Enter", shiftKey: false });

    expect(wrapper.emitted("toggle-collapse")).toEqual([[]]);
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

  it("makes every input a no-op when the grid is unparsed", async () => {
    stubComputedStyle("260px 1fr 320px");
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

  it("makes every input a no-op when a CSS minimum is missing", async () => {
    stubComputedStyle(GRID, { "--xw-editor-min": "" });
    const wrapper = mountHandle({ edge: "list", column: "list" });
    const handle = handleOf(wrapper);

    await handle.trigger("focus");
    await handle.trigger("keydown", { key: "ArrowRight", shiftKey: false });
    await pointer(handle, "pointerdown", { button: 0, clientX: 100 });
    await pointer(handle, "pointermove", { clientX: 200 });

    expect(handle.attributes("aria-valuenow")).toBeUndefined();
    expect(wrapper.emitted("set")).toBeUndefined();
  });
});
