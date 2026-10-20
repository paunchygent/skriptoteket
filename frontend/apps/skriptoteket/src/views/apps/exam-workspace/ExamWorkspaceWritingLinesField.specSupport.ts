/**
 * ExamWorkspaceWritingLinesField spec support.
 *
 * Shared mounting helpers for the Skrivyta field responsibility specs: the
 * data-test selectors, the mixed/matching free-text fixtures, the mount
 * helper attaching the field to the document body, the narrowing button
 * finder, and the per-test teardown each spec wires into its own `afterEach`.
 */

import { mount, type VueWrapper } from "@vue/test-utils";
import { expect } from "vitest";

import ExamWorkspaceWritingLinesField from "./ExamWorkspaceWritingLinesField.vue";
import type { FreeTextWritingLines } from "./examWorkspaceWritingLines";

export const FIELD = '[data-test="exam-workspace-writing-lines"]';
export const MINUS = '[data-test="exam-workspace-writing-lines-minus"]';
export const PLUS = '[data-test="exam-workspace-writing-lines-plus"]';
export const APPLY_ALL = '[data-test="exam-workspace-writing-lines-apply-all"]';
export const COUNT = '[data-test="exam-workspace-writing-lines-count"]';
export const POPOVER = '[data-test="exam-workspace-writing-lines-popover"]';
export const CONFIRM = '[data-test="exam-workspace-writing-lines-apply-confirm"]';
export const CANCEL = '[data-test="exam-workspace-writing-lines-cancel"]';
export const CLOSE = '[data-test="exam-workspace-writing-lines-close"]';
export const CONTROLS = [MINUS, PLUS, APPLY_ALL];
export const LOCK_REASON_ID = "exam-workspace-writing-lines-lock-reason";
export const LOCK_REASON_TEXT =
  "Frågan konverteras fortfarande. Texten från provfilen visas tills den är klar och går inte att ändra under tiden.";

/** Six free-text questions of which 1a, 1b and 3a differ from 8 rows. */
export const MIXED: FreeTextWritingLines[] = [
  { itemId: "i1", label: "1a", lines: 4 },
  { itemId: "i2", label: "1b", lines: null },
  { itemId: "i3", label: "2", lines: 8 },
  { itemId: "i4", label: "3a", lines: 12 },
  { itemId: "i5", label: "3b", lines: 8 },
  { itemId: "i6", label: "4", lines: 8 },
];
export const MATCHING: FreeTextWritingLines[] = MIXED.map((entry) => ({ ...entry, lines: 8 }));

export const mountedWrappers: VueWrapper[] = [];

export type MountFieldOptions = {
  disabled?: boolean;
  freeText?: FreeTextWritingLines[];
  lockedReasonId?: string | null;
};

export function mountField(lines: number, options: MountFieldOptions = {}): VueWrapper {
  const wrapper = mount(ExamWorkspaceWritingLinesField, {
    attachTo: document.body,
    props: {
      lines,
      disabled: options.disabled ?? false,
      freeText: options.freeText ?? MIXED,
      lockedReasonId: options.lockedReasonId ?? null,
    },
  });
  mountedWrappers.push(wrapper);
  return wrapper;
}

/** Narrow an element to its button without a type assertion. */
export function requireButton(element: Element): HTMLButtonElement {
  expect(element).toBeInstanceOf(HTMLButtonElement);
  if (!(element instanceof HTMLButtonElement)) {
    throw new Error("expected a button element");
  }
  return element;
}

/** Unmount every mounted field. Each spec wires this into its own `afterEach`. */
export function teardownWritingLinesField(): void {
  for (const wrapper of mountedWrappers.splice(0)) {
    wrapper.unmount();
  }
}
