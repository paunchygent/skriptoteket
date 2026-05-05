/**
 * User-facing authentication recovery copy.
 *
 * This module keeps auth action failures in Swedish product copy instead of
 * leaking transport, backend, or timeout internals into authenticated chrome.
 */

export const LOGOUT_NETWORK_FAILURE_MESSAGE =
  "Det gick inte att logga ut just nu. Kontrollera din internetanslutning och klicka på Logga ut igen.";

export const LOGOUT_GENERIC_FAILURE_MESSAGE =
  "Det gick inte att logga ut just nu. Klicka på Logga ut igen.";

export function normalizeLogoutFailureMessage(error: unknown): string {
  if (error instanceof Error && error.message === LOGOUT_NETWORK_FAILURE_MESSAGE) {
    return LOGOUT_NETWORK_FAILURE_MESSAGE;
  }
  return LOGOUT_GENERIC_FAILURE_MESSAGE;
}
