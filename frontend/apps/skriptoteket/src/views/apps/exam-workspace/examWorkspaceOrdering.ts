/**
 * Exam workspace ordering-question steps and their saved print order.
 *
 * Domain purpose:
 *   An ordering question's steps are its choices, and their list order is the
 *   answer key (TASK-SKRIPT-39-06-08 D1). Every print shows the steps in one
 *   saved shuffled order (D2, D5); "Blanda om" draws a new one, and from two
 *   steps the order is never the key order (D6). Adding, removing or moving a
 *   step keeps the printed order of the other steps where it still differs
 *   from the key.
 *
 * Relationships:
 *   - Mirrors `draw_print_order` and `validate_print_order` in
 *     `domain/curated_apps/exam_workspace/native_exam_ordering.py`; the
 *     server refuses a print order that breaks either rule.
 *   - Each transition is one document edit, so autosave history undoes it.
 */

import type { NativeExamBodyParagraph, NativeExamItem } from "../../../api/examWorkspace";

/** A random number in [0, 1), as `Math.random` returns. */
export type ExamWorkspaceRandom = () => number;

function randomIndex(random: ExamWorkspaceRandom, size: number): number {
  return Math.min(size - 1, Math.floor(random() * size));
}

function sameOrder(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((id, index) => id === right[index]);
}

/** A shuffled order of the steps that is never the key order once there are two. */
export function drawPrintOrder(stepIds: string[], random: ExamWorkspaceRandom = Math.random): string[] {
  const order = [...stepIds];
  if (order.length < 2) {
    return order;
  }
  for (let index = order.length - 1; index > 0; index -= 1) {
    const swap = randomIndex(random, index + 1);
    [order[index], order[swap]] = [order[swap], order[index]];
  }
  if (sameOrder(order, stepIds)) {
    // A rotation by 1..n-1 of distinct ids never equals the key order.
    const shift = 1 + randomIndex(random, order.length - 1);
    return [...order.slice(shift), ...order.slice(0, shift)];
  }
  return order;
}

/**
 * The print order after the steps changed: surviving steps keep their printed
 * order, a new step lands at a random printed position, and an order that now
 * equals the key is drawn again.
 */
export function keptPrintOrder(
  stepIds: string[],
  previousOrder: string[],
  random: ExamWorkspaceRandom = Math.random,
): string[] {
  const steps = new Set(stepIds);
  const order = previousOrder.filter((id) => steps.has(id));
  for (const id of stepIds) {
    if (!order.includes(id)) {
      order.splice(randomIndex(random, order.length + 1), 0, id);
    }
  }
  return stepIds.length >= 2 && sameOrder(order, stepIds) ? drawPrintOrder(stepIds, random) : order;
}

function withSteps(
  item: NativeExamItem,
  choices: NativeExamItem["choices"],
  random: ExamWorkspaceRandom,
): NativeExamItem {
  const stepIds = choices.map((choice) => choice.choice_id);
  return { ...item, choices, print_order: keptPrintOrder(stepIds, item.print_order, random) };
}

/** "Blanda om": a new saved print order. */
export function withShuffledSteps(item: NativeExamItem, random: ExamWorkspaceRandom = Math.random): NativeExamItem {
  return { ...item, print_order: drawPrintOrder(item.choices.map((choice) => choice.choice_id), random) };
}

function nextChoiceId(choiceIds: string[]): string {
  const highest = choiceIds.reduce((max, id) => Math.max(max, Number(id.slice("choice_".length)) || 0), 0);
  return `choice_${String(highest + 1).padStart(3, "0")}`;
}

/** An empty step, as the server writes an empty paragraph: a text segment needs one character. */
function blankStepBody(): NativeExamBodyParagraph[] {
  return [{ heading_level: null, segments: [{ kind: "text", text: " ", marks: [] }] }];
}

/** Append one empty step at the end of the key order. */
export function withStepAdded(item: NativeExamItem, random: ExamWorkspaceRandom = Math.random): NativeExamItem {
  const choiceId = nextChoiceId(item.choices.map((choice) => choice.choice_id));
  return withSteps(item, [...item.choices, { body: blankStepBody(), choice_id: choiceId }], random);
}

/** Remove one step; the last step stays, because an ordering question keeps one. */
export function withStepRemoved(
  item: NativeExamItem,
  choiceId: string,
  random: ExamWorkspaceRandom = Math.random,
): NativeExamItem {
  if (item.choices.length <= 1 || !item.choices.some((choice) => choice.choice_id === choiceId)) {
    return item;
  }
  return withSteps(item, item.choices.filter((choice) => choice.choice_id !== choiceId), random);
}

/** Move one step up (-1) or down (1) in the key order; the ends stay put. */
export function withStepMoved(
  item: NativeExamItem,
  choiceId: string,
  delta: -1 | 1,
  random: ExamWorkspaceRandom = Math.random,
): NativeExamItem {
  const from = item.choices.findIndex((choice) => choice.choice_id === choiceId);
  const to = from + delta;
  if (from < 0 || to < 0 || to >= item.choices.length) {
    return item;
  }
  const choices = [...item.choices];
  [choices[from], choices[to]] = [choices[to], choices[from]];
  return withSteps(item, choices, random);
}
