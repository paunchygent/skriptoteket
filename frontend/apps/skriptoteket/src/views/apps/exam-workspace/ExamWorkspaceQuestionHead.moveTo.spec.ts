/**
 * Exam workspace question head, Flytta till.
 *
 * Expected behavior:
 *   ⋮ holds "Flytta till…" above Ta bort, and it opens a second menu listing
 *   "Ingen del (fristående)" first, then every part in list order (G3). The
 *   question's current place is disabled with "Här nu"; for an ordering
 *   question every part entry is disabled with its reason (G6). Choosing a
 *   part emits its id, choosing "Ingen del (fristående)" emits null.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { NativeExamItemKind } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionHead from "./ExamWorkspaceQuestionHead.vue";

const ORDERING_REASON = "Ordna-frågor kan inte ligga i en del";

const TARGETS = [
  { id: "parent_001", label: "2 · Delinstruktion" },
  { id: "parent_002", label: "Instruktion · Tom instruktion" },
];

const mounted: Array<VueWrapper> = [];

function mountHead(kind: NativeExamItemKind, currentParentId: string | null): VueWrapper {
  const wrapper = mount(ExamWorkspaceQuestionHead, {
    attachTo: document.body,
    props: {
      child: null,
      converting: false,
      currentParentId,
      disabled: false,
      kind,
      label: "3",
      moveTargets: TARGETS,
      suggestedKind: null,
      unbuilt: false,
    },
  });
  mounted.push(wrapper);
  return wrapper;
}

function clickTest(id: string): void {
  const element = document.querySelector(`[data-test="${id}"]`);
  if (!element) {
    throw new Error(`missing ${id}`);
  }
  (element as HTMLElement).click();
}

function moveEntries(): HTMLElement[] {
  return Array.from(document.querySelectorAll<HTMLElement>('[data-test="exam-workspace-move-menu"] [role="menuitem"]'));
}

async function openMoveMenu(wrapper: VueWrapper): Promise<HTMLElement[]> {
  await wrapper.get('[data-test="exam-workspace-more"]').trigger("click");
  await flushPromises();
  clickTest("exam-workspace-move-to");
  await flushPromises();
  return moveEntries();
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  document.body.replaceChildren();
});

describe("ExamWorkspaceQuestionHead Flytta till", () => {
  it("lists Ingen del (fristående) first, then the parts, and disables the current place", async () => {
    const wrapper = mountHead("free_text", "parent_001");

    const entries = await openMoveMenu(wrapper);

    expect(entries).toHaveLength(3);
    expect(entries[0]!.textContent).toContain("Ingen del (fristående)");
    expect(entries[0]!.getAttribute("aria-disabled")).toBeNull();
    expect(entries[1]!.textContent).toContain("2 · Delinstruktion");
    expect(entries[2]!.textContent).toContain("Instruktion · Tom instruktion");

    expect(entries[1]!.getAttribute("aria-disabled")).toBe("true");
    expect(entries[1]!.textContent).toContain("Här nu");
    expect(entries[2]!.getAttribute("aria-disabled")).toBeNull();
  });

  it("marks a standalone question's Ingen del as its current place", async () => {
    const wrapper = mountHead("free_text", null);

    const entries = await openMoveMenu(wrapper);

    expect(entries[0]!.getAttribute("aria-disabled")).toBe("true");
    expect(entries[0]!.textContent).toContain("Här nu");
    expect(entries[1]!.getAttribute("aria-disabled")).toBeNull();
  });

  it("disables every part for an ordering question with its reason", async () => {
    const wrapper = mountHead("ordering", null);

    const entries = await openMoveMenu(wrapper);

    expect(entries[0]!.getAttribute("aria-disabled")).toBe("true");
    expect(entries[0]!.textContent).toContain("Här nu");
    for (const entry of entries.slice(1)) {
      expect(entry.getAttribute("aria-disabled")).toBe("true");
      expect(entry.textContent).toContain(ORDERING_REASON);
    }
  });

  it("emits the chosen part id, and null for Ingen del (fristående)", async () => {
    const wrapper = mountHead("free_text", "parent_001");

    await openMoveMenu(wrapper);
    clickTest("exam-workspace-move-parent_002");
    await flushPromises();
    expect(wrapper.emitted("moveTo")).toEqual([["parent_002"]]);

    await openMoveMenu(wrapper);
    clickTest("exam-workspace-move-standalone");
    await flushPromises();
    expect(wrapper.emitted("moveTo")).toEqual([["parent_002"], [null]]);
  });

  it("does nothing when the current place is chosen", async () => {
    const wrapper = mountHead("free_text", "parent_001");

    await openMoveMenu(wrapper);
    clickTest("exam-workspace-move-parent_001");
    await flushPromises();

    expect(wrapper.emitted("moveTo")).toBeUndefined();
  });
});
