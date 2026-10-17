/** Speaker-name coverage contract shared by persistence and workspace feedback. */

import { expect, it } from "vitest";

import type { ConversionHubTranscriptSpeakerOverlayEntry } from "../../../api/conversionHubTranscriptSaves";
import type { TranscriptSegment } from "../../../api/sirConvertGateway";
import { speakerOverlayEntriesCoverTranscript } from "./transcriptSpeakerOverlayCoverage";

it("requires transcript speakers and trimmed nonblank names for every canonical label", () => {
  const firstSpeaker: TranscriptSegment = {
    id: "segment_1",
    startSeconds: 0,
    endSeconds: 1,
    speakerLabel: "SPEAKER_00",
    text: "Hej.",
  };
  const segments: TranscriptSegment[] = [
    firstSpeaker,
    { ...firstSpeaker, id: "segment_2", speakerLabel: "SPEAKER_01" },
    { ...firstSpeaker, id: "segment_3" },
  ];
  const namedFirstSpeaker: ConversionHubTranscriptSpeakerOverlayEntry = {
    canonical_speaker_label: "SPEAKER_00",
    display_name: " Anna ",
  };
  const completeEntries: ConversionHubTranscriptSpeakerOverlayEntry[] = [
    namedFirstSpeaker,
    { canonical_speaker_label: "SPEAKER_01", display_name: "Bo" },
  ];

  expect(speakerOverlayEntriesCoverTranscript([], [])).toBe(false);
  expect(speakerOverlayEntriesCoverTranscript([], completeEntries)).toBe(false);
  expect(speakerOverlayEntriesCoverTranscript(segments, [])).toBe(false);
  expect(speakerOverlayEntriesCoverTranscript(segments, [
    namedFirstSpeaker,
    { canonical_speaker_label: "SPEAKER_99", display_name: "Bo" },
  ])).toBe(false);
  expect(speakerOverlayEntriesCoverTranscript(segments, [
    namedFirstSpeaker,
    { canonical_speaker_label: "SPEAKER_01", display_name: " \t\n " },
  ])).toBe(false);
  expect(speakerOverlayEntriesCoverTranscript(segments, completeEntries)).toBe(true);
  expect(speakerOverlayEntriesCoverTranscript(segments, [
    ...completeEntries,
    { canonical_speaker_label: "SPEAKER_99", display_name: "" },
  ])).toBe(true);
});
