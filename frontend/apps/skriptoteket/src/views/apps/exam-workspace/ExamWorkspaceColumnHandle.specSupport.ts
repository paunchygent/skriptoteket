/**
 * Exam workspace column resize handle spec support.
 *
 * Purpose:
 *   Shared helpers for the `ExamWorkspaceColumnHandle` specs: the grid and
 *   CSS-owned minimum defaults, the typed computed-style stub, the typed
 *   ResizeObserver double (jsdom has none, so specs fire the callback by
 *   hand), the mount helper attaching the handle inside a `.xw-root.ws__body`
 *   ancestor, the handle finder, the direct pointer-event dispatcher (Vue
 *   Test Utils builds pointer triggers on MouseEvent, whose button is
 *   getter-only), and the per-test setup/teardown each spec wires into its
 *   own `beforeEach`/`afterEach`.
 */

import { vi } from "vitest";
import { nextTick } from "vue";
import { mount, type DOMWrapper, type VueWrapper } from "@vue/test-utils";

import ExamWorkspaceColumnHandle from "./ExamWorkspaceColumnHandle.vue";

export const GRID = "260px 700px 320px";
export const LIST_MAX = 260 + 700 - 400;
export const SIDE_MAX = 320 + 700 - 400;

export type MinimumName = "--xw-list-min" | "--xw-drawer-min" | "--xw-preview-min" | "--xw-editor-min";

export const DEFAULT_MINIMUMS: Record<MinimumName, string> = {
  "--xw-list-min": "260px",
  "--xw-drawer-min": "300px",
  "--xw-preview-min": "300px",
  "--xw-editor-min": "400px",
};

const containers: HTMLElement[] = [];
export const mountedWrappers: VueWrapper[] = [];

/**
 * A typed ResizeObserver double: jsdom has no ResizeObserver, so the spec
 * installs this class and fires the callback by hand. It records every
 * observed target, mirroring the sharedSegmentedToggle.spec.ts pattern.
 */
export class HandleResizeObserver implements ResizeObserver {
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

export function latestObserver(): HandleResizeObserver {
  const observer = HandleResizeObserver.instances.at(-1);
  if (observer === undefined) {
    throw new Error("expected a ResizeObserver instance");
  }
  return observer;
}

export function bodyOf(wrapper: VueWrapper): HTMLElement {
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
export function stubComputedStyle(grid: string, overrides: Partial<Record<MinimumName, string>> = {}): void {
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

export interface MountHandleProps {
  edge: "list" | "side";
  column: "list" | "drawer" | "preview";
  collapsible?: boolean;
  collapsed?: boolean;
}

export function mountHandle(props: MountHandleProps): VueWrapper {
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

export function handleOf(wrapper: VueWrapper): DOMWrapper<Element> {
  return wrapper.find('[data-test^="exam-workspace-column-handle-"]');
}

/**
 * Dispatch a pointer lifecycle event with position details. Vue Test Utils
 * builds pointer triggers on MouseEvent, whose button is getter-only, so the
 * drag tests dispatch the event directly instead.
 */
export async function pointer(
  handle: DOMWrapper<Element>,
  type: string,
  init: MouseEventInit,
): Promise<void> {
  handle.element.dispatchEvent(
    new MouseEvent(type, { bubbles: true, cancelable: true, ...init }),
  );
  await nextTick();
}

/** Install the observer double, the pointer-capture stubs and the default grid style. */
export function setupHandleTestEnv(): void {
  HTMLElement.prototype.setPointerCapture = vi.fn();
  HTMLElement.prototype.releasePointerCapture = vi.fn();
  HandleResizeObserver.instances = [];
  vi.stubGlobal("ResizeObserver", HandleResizeObserver);
  stubComputedStyle(GRID);
}

/** Unmount every mounted handle, remove its containers and restore mocks and globals. */
export function teardownHandleTestEnv(): void {
  for (const wrapper of mountedWrappers.splice(0)) {
    wrapper.unmount();
  }
  for (const container of containers.splice(0)) {
    container.remove();
  }
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
}
