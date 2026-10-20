/**
 * Exam workspace document address sync.
 *
 * Domain purpose:
 *   The address is an adapter, not another controller: it parses address
 *   requests and submits them synchronously to the gate-owned replacement
 *   coordinator, which alone settles, chooses, retires, opens or adopts, and
 *   publishes the address. A projection echo matching the coordinator's
 *   current address is idempotent; a genuinely different address becomes a new
 *   intent before any application await.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView` through the view panels; drawer opens use
 *     the same coordinator entrance without touching the router first.
 *   - The coordinator publishes through the shared route projection; this
 *     adapter never writes the address, keeps no pending target, interprets
 *     no open outcome and runs no return-to-open continuation.
 */

import { onMounted } from "vue";

import type { ExamWorkspaceRouteProjection } from "./examWorkspaceRouteProjection";

export type ExamWorkspaceAddressParams = {
  /** Submit a route-open intent synchronously; the coordinator owns what follows. */
  submitRoute: (lineageId: string) => void;
  /** The address the coordinator stands behind: its desired target, else its source. */
  currentAddress: () => string | null;
  /** The shared router adapter: observed here, published only by the coordinator. */
  projection: ExamWorkspaceRouteProjection;
};

export function useExamWorkspaceAddress(params: ExamWorkspaceAddressParams) {
  function submitChangedAddress(lineageId: string | null): void {
    if (lineageId === null) {
      return;
    }
    if (lineageId === params.currentAddress()) {
      return;
    }
    params.submitRoute(lineageId);
  }

  params.projection.watchAddress((lineageId) => {
    submitChangedAddress(lineageId);
  });

  onMounted(() => {
    submitChangedAddress(params.projection.current());
  });
}
