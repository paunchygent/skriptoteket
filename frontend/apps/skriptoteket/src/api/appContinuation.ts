/**
 * Skriptoteket app-local bootstrap continuation contract.
 *
 * Purpose:
 *   Centralize the post-HuleEdu-session endpoint that hydrates local AI policy
 *   and profile AI preferences without restoring a local current-user endpoint.
 *
 * Relationships:
 *   - `stores/auth.ts` calls this endpoint after the shared HuleEdu session.
 *   - `stores/ai.ts` consumes the resulting policy and profile preferences.
 */

import type { components } from "./openapi";

export const APP_CONTINUATION_PATH = "/api/v1/profile/app-continuation";

export type AppContinuationResponse =
  components["schemas"]["ProfileAppContinuationResponse"];
