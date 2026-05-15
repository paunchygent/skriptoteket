/**
 * Sir Convert Gateway adapter public surface.
 *
 * Purpose:
 *   Export the small protocol-shaped pieces used by Skriptoteket's
 *   authenticated DigiExam migration flow.
 *
 * Relationships:
 *   - Consumers import from this folder instead of reaching into submodules.
 *   - Submodules remain split by contract, request context, transport, and
 *     save-metadata responsibilities.
 */

export * from "./client";
export * from "./contractValues";
export * from "./errors";
export * from "./jobSpec";
export { parseTargetReadinessReport } from "./parsers";
export * from "./requestContext";
export * from "./saveMetadata";
export * from "./types";
export * from "./userFiles";
export * from "./urls";
