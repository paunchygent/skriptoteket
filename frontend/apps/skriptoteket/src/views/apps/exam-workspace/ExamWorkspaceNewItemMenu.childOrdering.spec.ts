/**
 * Exam workspace new-question menu, ordering inside a part (TASK-SKRIPT-39-06-11 D1).
 *
 * Expected behavior:
 *   "+ Deluppgift" offers every question kind, Ordna included, because an
 *   ordering question may now sit inside a part. It still offers neither Ny
 *   del nor Instruktion med deluppgifter, and the top-level menu still offers
 *   Ordna alongside them. Choosing Ordna inside a part emits the kind.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import ExamWorkspaceNewItemMenu from "./ExamWorkspaceNewItemMenu.vue";

const mounted: Array<VueWrapper> = [];

function mountMenu(child: boolean): VueWrapper {
  const wrapper = mount(ExamWorkspaceNewItemMenu, {
    attachTo: document.body,
    props: { anchor: null, child, open: true },
  });
  mounted.push(wrapper);
  return wrapper;
}

function entryTests(child: boolean): string[] {
  const menu = document.querySelector(
    `[data-test="${child ? "exam-workspace-new-child-menu" : "exam-workspace-new-menu"}"]`,
  );
  if (!(menu instanceof HTMLElement)) {
    throw new Error("expected the new-item menu");
  }
  return Array.from(menu.querySelectorAll<HTMLElement>('[role="menuitem"]')).map(
    (entry) => entry.dataset.test ?? "",
  );
}

function inDocument(testId: string): HTMLElement | null {
  const element = document.querySelector(`[data-test="${testId}"]`);
  return element instanceof HTMLElement ? element : null;
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  document.body.replaceChildren();
});

describe("ExamWorkspaceNewItemMenu ordering inside a part", () => {
  it("offers Ordna in a deluppgift menu", () => {
    mountMenu(true);

    expect(entryTests(true)).toContain("exam-workspace-new-ordering");
  });

  it("still offers no Ny del and no Instruktion med deluppgifter in a deluppgift menu", () => {
    mountMenu(true);

    const entries = entryTests(true);
    expect(entries).not.toContain("exam-workspace-new-part");
    expect(entries).not.toContain("exam-workspace-new-instruction");
  });

  it("keeps every kind, Ordna included, in the top-level menu", () => {
    mountMenu(false);

    const entries = entryTests(false);
    expect(entries).toContain("exam-workspace-new-ordering");
    expect(entries).toContain("exam-workspace-new-part");
    expect(entries).toContain("exam-workspace-new-instruction");
  });

  it("emits the chosen Ordna kind from a deluppgift menu", async () => {
    const wrapper = mountMenu(true);

    inDocument("exam-workspace-new-ordering")!.click();

    expect(wrapper.emitted("choose")).toEqual([["ordering"]]);
  });
});
