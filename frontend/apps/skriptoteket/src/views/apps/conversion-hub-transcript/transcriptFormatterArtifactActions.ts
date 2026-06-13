/**
 * Transcript formatter artifact action view state.
 *
 * Domain purpose:
 *   Share compact download and Mina filer save state for replay-returned
 *   transcript formatter artifact controls.
 *
 * Relationships:
 *   - Used by `ConversionHubTranscriptHost`, `TranscriptWorkspaceShell`, and
 *     `TranscriptFormatterReplayPanel`.
 *   - Keys match owner-scoped backend artifact refs from PR-0347 replay.
 */

import type {
  TranscriptFormatterArtifactKey,
} from "../../../api/conversionHubTranscriptFormatterArtifactActions";

export type FormatterArtifactActionPhase = "idle" | "running" | "succeeded" | "failed";

export type FormatterArtifactActionState = {
  download: FormatterArtifactActionPhase;
  save: FormatterArtifactActionPhase;
  savedFilename: string | null;
};

export type FormatterArtifactActionStates = Partial<
  Record<TranscriptFormatterArtifactKey, FormatterArtifactActionState>
>;

export function idleFormatterArtifactActionState(): FormatterArtifactActionState {
  return {
    download: "idle",
    save: "idle",
    savedFilename: null,
  };
}

export function formatterArtifactActionState(
  states: FormatterArtifactActionStates,
  artifactKey: TranscriptFormatterArtifactKey,
): FormatterArtifactActionState {
  return states[artifactKey] ?? idleFormatterArtifactActionState();
}
