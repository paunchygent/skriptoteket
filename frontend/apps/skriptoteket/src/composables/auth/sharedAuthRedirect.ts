/**
 * Shared-auth browser redirect helper.
 *
 * Purpose:
 *   Keep top-level HuleEdu ceremony navigation mockable in view tests while
 *   using the browser's normal document navigation in production.
 *
 * Relationships:
 *   - Used by `AuthLoginView` for the `/auth/login` auto-handoff fallback.
 *   - URL construction remains owned by `api/sharedAuth.ts`.
 */

export function redirectToSharedAuthCeremony(url: string): void {
  window.location.assign(url);
}
