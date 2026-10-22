import { beforeEach, describe, expect, it, vi } from "vitest";
import { EditorState, Transaction } from "@codemirror/state";
import { EditorView } from "@codemirror/view";

import { createPinia, setActivePinia } from "pinia";

import { ApiError, apiFetch } from "../../api/client";
import { useToastStore } from "../../stores/toast";
import {
  AI_USER_LIMIT_NOTE,
  aiDailyLimitNote,
  resetAiDailyLimitForTests,
} from "../../views/apps/exam-workspace/aiDailyLimit";
import { skriptoteketGhostText } from "./skriptoteketGhostText";

vi.mock("../../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/client")>()),
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
    resetAiDailyLimitForTests();
    setActivePinia(createPinia());
  });

  it("answers a user-share 429 with the inline note, no toast and no further requests", async () => {
    vi.mocked(apiFetch).mockRejectedValue(
      new ApiError({
        code: "AI_DAILY_LIMIT_REACHED",
        message: AI_USER_LIMIT_NOTE,
        status: 429,
        details: { limit: "user_share" },
      }),
    );

    const { view, parent } = createEditor("def x():\n    ");

    try {
      typeText(view, "x");
      vi.advanceTimersByTime(10);
      await flushMicrotasks();

      expect(apiFetch).toHaveBeenCalledTimes(1);
      expect(aiDailyLimitNote.value).toBe(AI_USER_LIMIT_NOTE);
      expect(useToastStore().toasts).toHaveLength(0);

      typeText(view, "y");
      vi.advanceTimersByTime(10);
      await flushMicrotasks();
      keyDown(view.contentDOM, "Alt-\\");
      await flushMicrotasks();

      expect(apiFetch).toHaveBeenCalledTimes(1);
      expect(parent.querySelector(".cm-skriptoteket-ghost-text")).toBeFalsy();
    } finally {
      view.destroy();
      parent.remove();
    }
  });

  it("leaves the limit unmarked when a completion fails for another reason", async () => {
    vi.mocked(apiFetch).mockRejectedValue(
      new ApiError({ code: "INTERNAL_ERROR", message: "Fel", status: 500 }),
    );

    const { view, parent } = createEditor("def x():\n    ");

    try {
      typeText(view, "x");
      vi.advanceTimersByTime(10);
      await flushMicrotasks();

      expect(aiDailyLimitNote.value).toBeNull();
    } finally {
      view.destroy();
      parent.remove();
    }
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

  it("accepts ghost text with right-side replacement", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      completion: "rn",
      enabled: true,
      replace_suffix_chars: 2,
    });

    const { view, parent } = createEditor("retuXX");

    try {
      view.dispatch({ selection: { anchor: 4 } });
      keyDown(view.contentDOM, "Alt-\\");
      await flushMicrotasks();

      const widget = parent.querySelector(".cm-skriptoteket-ghost-text");
      expect(widget).toBeTruthy();
      expect(widget?.textContent).toBe("rn");

      keyDown(view.contentDOM, "Tab");
      await flushMicrotasks();

      expect(view.state.doc.toString()).toBe("return");
      expect(parent.querySelector(".cm-skriptoteket-ghost-text")).toBeFalsy();
    } finally {
      view.destroy();
      parent.remove();
    }
  });
});
