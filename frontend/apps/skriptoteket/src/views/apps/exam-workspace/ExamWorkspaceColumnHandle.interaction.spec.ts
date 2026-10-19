/**
 * Exam workspace column resize handle: keyboard and pointer operation.
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

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  LIST_MAX,
  SIDE_MAX,
  handleOf,
  mountHandle,
  pointer,
  setupHandleTestEnv,
  stubComputedStyle,
  teardownHandleTestEnv,
} from "./ExamWorkspaceColumnHandle.specSupport";

beforeEach(() => {
  setupHandleTestEnv();
});

afterEach(() => {
  teardownHandleTestEnv();
});

describe("ExamWorkspaceColumnHandle", () => {
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
});
