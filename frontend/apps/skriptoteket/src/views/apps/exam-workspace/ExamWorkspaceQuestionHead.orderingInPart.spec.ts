/**
 * Exam workspace question head, an ordering question inside a part
 * (TASK-SKRIPT-39-06-11 D1, D2).
 *
 * Expected behavior:
 *   A deluppgift's Byt frågetyp offers Ordna, so a part child can become an
 *   ordering question. An ordering question's Flytta till offers every part
 *   with no refusal hint and emits the chosen part id; only its current place
 *   stays disabled with "Här nu".
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { NativeExamItemKind } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionHead from "./ExamWorkspaceQuestionHead.vue";

const REFUSAL = "Ordna-frågor kan inte ligga i en del";

const TARGETS = [
  { id: "parent_001", label: "2 · Delinstruktion" },
  { id: "parent_002", label: "Instruktion · Tom instruktion" },
];

const mounted: Array<VueWrapper> = [];

function mountHead(options: {
  child?: { index: number; count: number } | null;
  currentParentId?: string | null;
  kind?: NativeExamItemKind;
} = {}): VueWrapper {
  const wrapper = mount(ExamWorkspaceQuestionHead, {
    attachTo: document.body,
    props: {
      child: options.child ?? null,
      converting: false,
      currentParentId: options.currentParentId ?? null,
      disabled: false,
      kind: options.kind ?? "free_text",
      label: "3",
      moveTargets: TARGETS,
      suggestedKind: null,
      typeLabel: "Ordna",
      unbuilt: false,
    },
  });
  mounted.push(wrapper);
  return wrapper;
}

function clickTest(id: string): void {
  const element = document.querySelector(`[data-test="${id}"]`);
  if (!(element instanceof HTMLElement)) {
    throw new Error(`missing ${id}`);
  }
  element.click();
}

function inDocument(testId: string): HTMLElement | null {
  const element = document.querySelector(`[data-test="${testId}"]`);
  return element instanceof HTMLElement ? element : null;
}

function moveEntries(): HTMLElement[] {
  return Array.from(
    document.querySelectorAll<HTMLElement>('[data-test="exam-workspace-move-menu"] [role="menuitem"]'),
  );
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

describe("ExamWorkspaceQuestionHead ordering inside a part", () => {
  it("offers Ordna in a deluppgift's Byt frågetyp", async () => {
    const wrapper = mountHead({ child: { index: 0, count: 2 } });

    await wrapper.get('[data-test="exam-workspace-type"]').trigger("click");
    await flushPromises();

    expect(inDocument("exam-workspace-type-ordering")).not.toBeNull();
  });

  it("lists every part for an ordering question with no refusal hint", async () => {
    const wrapper = mountHead({ kind: "ordering" });

    const entries = await openMoveMenu(wrapper);

    expect(entries[0]!.getAttribute("aria-disabled")).toBe("true");
    expect(entries[0]!.textContent).toContain("Här nu");
    for (const entry of entries.slice(1)) {
      expect(entry.getAttribute("aria-disabled")).toBeNull();
      expect(entry.textContent).not.toContain(REFUSAL);
    }
  });

  it("emits the chosen part id for an ordering question", async () => {
    const wrapper = mountHead({ kind: "ordering" });

    await openMoveMenu(wrapper);
    clickTest("exam-workspace-move-parent_002");
    await flushPromises();

    expect(wrapper.emitted("moveTo")).toEqual([["parent_002"]]);
  });
});
