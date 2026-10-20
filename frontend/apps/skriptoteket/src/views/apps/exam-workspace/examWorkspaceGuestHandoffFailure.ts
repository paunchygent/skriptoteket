/**
 * Guest draft handoff failure classification.
 *
 * Domain purpose:
 *   Decide, from the error the guest-draft handoff POST threw, how the caller
 *   treats the failure. `vault_full` means Mina filer is full, so there is no
 *   automatic retry; the teacher frees space and retries by hand. `permanent`
 *   means the server will never accept this draft, so the caller stops
 *   retrying and offers download or removal. `transient` means a later try
 *   can succeed, so the caller retries later with backoff. `deferred` means
 *   the sign-in ended, so the handoff waits and the next signed-in load tries
 *   again. A failed CSRF token refresh (403 AUTHORIZATION_ERROR) defers like
 *   401; every other 403, including a role refusal (FORBIDDEN), stays
 *   permanent.
 *
 * Relationships:
 *   - Consumed by `useExamWorkspaceGuestHandoff`.
 *   - Client-side permanent cases such as missing picture bytes are decided
 *     by the caller before any POST, not here.
 */

import { isApiError } from "../../../api/client";
import { SupersededAuthSessionError } from "../../../stores/auth";

export type GuestHandoffFailureKind = "permanent" | "transient" | "deferred" | "vault_full";

/** The server's full-vault marker: a 422 whose details carry exactly this reason. */
function isVaultFullDetails(details: unknown): boolean {
  if (typeof details !== "object" || details === null) {
    return false;
  }
  if (!("reason" in details)) {
    return false;
  }
  const reason: unknown = details.reason;
  return reason === "vault_full";
}

/**
 * Classify the error a guest-draft handoff POST threw. Classification uses
 * the status, the error code AUTHORIZATION_ERROR and the server's vault_full
 * detail only, never message text. A failed CSRF token refresh (403
 * AUTHORIZATION_ERROR) defers like 401.
 */
export function classifyGuestHandoffFailure(error: unknown): GuestHandoffFailureKind {
  if (error instanceof SupersededAuthSessionError) {
    return "deferred";
  }
  if (isApiError(error)) {
    if (error.status === 422 && isVaultFullDetails(error.details)) {
      return "vault_full";
    }
    if (error.status === 401) {
      return "deferred";
    }
    if (error.status === 403 && error.code === "AUTHORIZATION_ERROR") {
      return "deferred";
    }
    if (error.status === 408 || error.status === 429) {
      return "transient";
    }
    if (error.status >= 500) {
      return "transient";
    }
    if (error.status >= 400 && error.status <= 499) {
      return "permanent";
    }
    return "transient";
  }
  return "transient";
}
