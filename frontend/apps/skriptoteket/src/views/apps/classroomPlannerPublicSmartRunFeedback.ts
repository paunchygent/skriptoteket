/**
 * Public Smart run feedback normalization.
 *
 * Purpose:
 *   Convert public Klassrumskartan Smart helper diagnostics into teacher-facing
 *   recovery copy before the guest workspace shell turns run messages into
 *   toasts.
 *
 * Relationships:
 *   - consumed by the public Smart grouping and seating run composables
 *   - keeps backend revision mismatch text available to logs/tests without
 *     leaking it into public guest UI feedback
 */

import { isApiError } from "../../api/client";

const PUBLIC_SMART_REVISION_CONFLICT_PATTERN = /^Draft revision mismatch\./;

export const PUBLIC_SMART_REVISION_CONFLICT_MESSAGE =
  "Det gick inte att slumpa just nu. Klicka på Slumpa igen.";

export function normalizePublicSmartRunError(
  error: unknown,
  fallbackMessage: string,
  normalizeErrorMessage: (error: unknown, fallbackMessage: string) => string,
): string {
  if (
    isApiError(error)
    && error.status === 409
    && PUBLIC_SMART_REVISION_CONFLICT_PATTERN.test(error.message)
  ) {
    return PUBLIC_SMART_REVISION_CONFLICT_MESSAGE;
  }

  return normalizeErrorMessage(error, fallbackMessage);
}
