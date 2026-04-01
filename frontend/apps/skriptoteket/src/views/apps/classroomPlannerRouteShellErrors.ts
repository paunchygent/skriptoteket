/**
 * Classroom planner UI error helpers.
 *
 * This module keeps planner UI error normalization in one place so route-shell
 * flows, export flows, and state lanes can fall back to safe teacher-facing
 * copy when unexpected JavaScript/runtime exceptions leak out of the app.
 */

import { isApiError } from "../../api/client";

const UNEXPECTED_RUNTIME_MESSAGE_PATTERNS = [
  /Cannot read properties of (undefined|null)/,
  /Cannot set properties of (undefined|null)/,
  /Cannot destructure property/,
  /is not a function/,
  /undefined is not an object/i,
  /null is not an object/i,
];

function isUnexpectedPlannerRuntimeError(error: Error): boolean {
  return (
    error instanceof TypeError
    || error instanceof ReferenceError
    || error instanceof SyntaxError
  );
}

function looksLikeUnexpectedPlannerRuntimeMessage(message: string): boolean {
  return UNEXPECTED_RUNTIME_MESSAGE_PATTERNS.some((pattern) => pattern.test(message));
}

export function normalizeClassroomPlannerUiError(error: unknown, fallbackMessage: string): string {
  if (isApiError(error)) {
    return error.message || fallbackMessage;
  }
  if (
    error instanceof Error
    && (
      isUnexpectedPlannerRuntimeError(error)
      || looksLikeUnexpectedPlannerRuntimeMessage(error.message)
    )
  ) {
    console.error("Suppressed unexpected Klassrumskartan runtime error.", error);
    return fallbackMessage;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallbackMessage;
}
