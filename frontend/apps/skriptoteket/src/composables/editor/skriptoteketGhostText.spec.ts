import { beforeEach, describe, expect, it, vi } from "vitest";
import { EditorState, Transaction } from "@codemirror/state";
import { EditorView } from "@codemirror/view";

import { apiFetch } from "../../api/client";
import { skriptoteketGhostText } from "./skriptoteketGhostText";

vi.mock("../../api/client", () => ({
  apiFetch: vi.fn(),
}));

async function flushMicrotasks(): Promise<void> {
  await new Promise<void>((resolve) => queueMicrotask(() => resolve()));
  await new Promise<void>((resolve) => queueMicrotask(() => resolve()));
}

function keyDown(target: HTMLElement, key: string, init: Partial<KeyboardEventInit> = {}): void {
  target.dispatchEvent(
    new KeyboardEvent("keydown", {
      key,
      bubbles: true,
      cancelable: true,
      ...init,
    }),
  );
}

function typeText(view: EditorView, text: string): void {
  const from = view.state.selection.main.head;
  view.dispatch({
    changes: { from, to: from, insert: text },
    selection: { anchor: from + text.length },
    annotations: Transaction.userEvent.of("input"),
  });
}

function createEditor(doc: string): { view: EditorView; parent: HTMLElement } {
  const parent = document.createElement("div");
  document.body.appendChild(parent);

  const view = new EditorView({
    state: EditorState.create({
      doc,
      selection: { anchor: doc.length },
      extensions: [
        skriptoteketGhostText({
          entrypointName: "run_tool",
          ghostText: { enabled: true, autoTrigger: true, debounceMs: 10 },
        }),
      ],
    }),
    parent,
  });

  view.focus();

  return { view, parent };
}

describe("skriptoteketGhostText", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  it("shows ghost text after typing pause and accepts with Tab", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ completion: "pass\n", enabled: true });

    const { view, parent } = createEditor("def x():\n    ");

    try {
      typeText(view, "x");
      vi.advanceTimersByTime(10);
      await flushMicrotasks();

      const widget = parent.querySelector(".cm-skriptoteket-ghost-text");
      expect(widget).toBeTruthy();
      expect(widget?.textContent).toBe("pass\n");

      keyDown(view.contentDOM, "Tab");
      await flushMicrotasks();

      expect(view.state.doc.toString()).toContain("def x():\n    xpass\n");
      expect(parent.querySelector(".cm-skriptoteket-ghost-text")).toBeFalsy();
    } finally {
      view.destroy();
      parent.remove();
    }
  });

  it("dismisses ghost text with Escape", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ completion: "pass\n", enabled: true });

    const { view, parent } = createEditor("def x():\n    ");

    try {
      typeText(view, "x");
      vi.advanceTimersByTime(10);
      await flushMicrotasks();

      expect(parent.querySelector(".cm-skriptoteket-ghost-text")).toBeTruthy();

      keyDown(view.contentDOM, "Escape");
      await flushMicrotasks();

      expect(parent.querySelector(".cm-skriptoteket-ghost-text")).toBeFalsy();
      expect(view.state.doc.toString()).toContain("def x():\n    x");
    } finally {
      view.destroy();
      parent.remove();
    }
  });

  it("clears ghost text on document changes", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ completion: "pass\n", enabled: true });

    const { view, parent } = createEditor("def x():\n    ");

    try {
      typeText(view, "x");
      vi.advanceTimersByTime(10);
      await flushMicrotasks();

      expect(parent.querySelector(".cm-skriptoteket-ghost-text")).toBeTruthy();

      typeText(view, "y");
      await flushMicrotasks();

      expect(parent.querySelector(".cm-skriptoteket-ghost-text")).toBeFalsy();
    } finally {
      view.destroy();
      parent.remove();
    }
  });
});
