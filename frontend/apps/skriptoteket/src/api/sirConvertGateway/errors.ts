/**
 * Sir Convert Gateway adapter errors.
 *
 * Purpose:
 *   Preserve Sir Convert and Gateway failure envelopes as typed frontend errors
 *   without remapping route-specific codes into Skriptoteket-only meanings.
 *
 * Relationships:
 *   - `parsers.ts` creates these errors from HTTP responses.
 *   - UI flows can branch on `code`, `status`, and `correlationId`.
 */

export class SirConvertGatewayError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly details: unknown;
  public readonly correlationId: string | null;

  public constructor(params: {
    status: number;
    code: string;
    message: string;
    details?: unknown;
    correlationId?: string | null;
  }) {
    super(params.message);
    this.name = "SirConvertGatewayError";
    this.status = params.status;
    this.code = params.code;
    this.details = params.details ?? null;
    this.correlationId = params.correlationId ?? null;
  }
}

export function isSirConvertGatewayError(error: unknown): error is SirConvertGatewayError {
  return error instanceof SirConvertGatewayError;
}
