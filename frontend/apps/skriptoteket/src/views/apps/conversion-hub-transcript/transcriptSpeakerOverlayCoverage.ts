/**
 * Canonical speaker-name coverage shared by overlay persistence and its workspace.
 * A transcript needs at least one speaker and a nonblank name for every label.
 */

import type { ConversionHubTranscriptSpeakerOverlayEntry } from "../../../api/conversionHubTranscriptSaves";
import type { TranscriptSegment } from "../../../api/sirConvertGateway";

export function speakerOverlayEntriesCoverTranscript(
  segments: readonly TranscriptSegment[],
  entries: readonly ConversionHubTranscriptSpeakerOverlayEntry[],
): boolean {
  const speakerLabels = new Set(segments.map((segment) => segment.speakerLabel));
  if (speakerLabels.size === 0) return false;
  const namedLabels = new Set(
    entries
      .filter((entry) => entry.display_name.trim().length > 0)
      .map((entry) => entry.canonical_speaker_label),
  );
  return [...speakerLabels].every((label) => namedLabels.has(label));
}
