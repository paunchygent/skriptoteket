/**
 * Sir Convert Gateway adapter public surface.
 *
 * Purpose:
 *   Export the small protocol-shaped pieces used by Skriptoteket's
 *   authenticated transcript conversion flow.
 *
 * Relationships:
 *   - Consumers import from this folder instead of reaching into submodules.
 *   - Submodules remain split by contract, request context, transport, and
 *     parsing responsibilities.
 */

export * from "./client";
export * from "./errors";
export * from "./requestFingerprint";
export * from "./transcriptOptions";
export * from "./transcriptRequestContext";
export {
  parseTranscriptArtifactManifest,
  parseTranscriptJob,
  parseTranscriptJson,
  parseTranscriptResult,
} from "./transcriptParsers";
export * from "./transcriptTypes";
export * from "./uploadProgress";
export * from "./urls";
