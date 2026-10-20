/**
 * Exam workspace route projection spec double.
 *
 * Domain purpose:
 *   A router-less projection for specs that mount the editing session
 *   without a router: it names nothing, publishes nowhere, observes nothing
 *   and is always idle. Production always passes `createRouteProjection`.
 */

import type { ExamWorkspaceRouteProjection } from "./examWorkspaceRouteProjection";

export function nullRouteProjection(): ExamWorkspaceRouteProjection {
  return {
    current: () => null,
    project: () => undefined,
    waitForIdle: () => Promise.resolve(),
    watchAddress: () => undefined,
  };
}
