/**
 * Transcript workspace shell specs.
 *
 * Domain purpose:
 *   Prove transcript progress and result surfaces stay teacher-facing even
 *   when upstream lifecycle data contains internal phase names.
 *
 * Relationships:
 *   - Exercises `TranscriptWorkspaceShell.vue` as a DOM boundary.
 *   - Complements Gateway parser proof in `transcriptClient.spec.ts`.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import TranscriptWorkspaceShell from "./TranscriptWorkspaceShell.vue";
import type { SirConvertTranscriptJob } from "../../../api/sirConvertGateway";

function transcriptJob(stage: string): SirConvertTranscriptJob {
  return {
    audioProgress: {
      currentChunkIndex: null,
      percentComplete: null,
      processedMediaSeconds: null,
      totalChunks: null,
      totalMediaSeconds: null,
    },
    jobId: "job_transcript_1",
    stage,
    status: "running",
  };
}

describe("TranscriptWorkspaceShell", () => {
  it("maps raw upstream stages to safe teacher-facing progress copy", () => {
    const wrapper = mount(TranscriptWorkspaceShell, {
      props: {
        currentJob: transcriptJob("pyannote_sidecar_model_warmup"),
        errorMessage: null,
        runtimeStatus: "running",
        selectedTranscriptFile: null,
        transcript: null,
        transcriptFileError: null,
      },
    });

    expect(wrapper.text()).toContain("Bearbetar inspelningen.");
    expect(wrapper.text()).not.toContain("pyannote_sidecar_model_warmup");
    expect(wrapper.text()).not.toContain("sidecar");
    expect(wrapper.text()).not.toContain("model");
    expect(wrapper.text()).not.toContain("pyannote");
  });
});
