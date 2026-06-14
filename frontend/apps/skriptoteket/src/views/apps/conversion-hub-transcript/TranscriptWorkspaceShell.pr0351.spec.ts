/**
 * PR-0351 transcript workspace UX specs.
 *
 * Domain purpose:
 *   Prove the transcript workspace follows the approved completion-progress
 *   and selected-format export UX contract, including absence of removed controls.
 *
 * Relationships:
 *   - Exercises `TranscriptWorkspaceShell.vue` as the PR-0351 DOM boundary.
 *   - Complements ongoing state coverage in `TranscriptWorkspaceShell.spec.ts`.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type {
  SirConvertTranscriptJob,
  SirConvertTranscriptProgressPhase,
} from "../../../api/sirConvertGateway";
import TranscriptWorkspaceShell from "./TranscriptWorkspaceShell.vue";

function transcriptJob(phase: SirConvertTranscriptProgressPhase): SirConvertTranscriptJob {
  return {
    jobId: "job_transcript_1",
    progress: {
      audioPipelineEtaSeconds: null,
      audioPipelinePercentComplete: null,
      currentChunkIndex: 1,
      currentPhaseStartedAt: "2026-06-13T08:14:00Z",
      lastHeartbeatAt: "2026-06-13T08:15:30Z",
      percentComplete: 35,
      phase,
      phaseTimingsMs: {
        chunk_total_ms: 32000,
        conversion_total_ms: 45000,
      },
      processedMediaSeconds: 42,
      status: "running",
      totalChunks: 3,
      totalMediaSeconds: 120,
    },
    status: "running",
  };
}

describe("TranscriptWorkspaceShell PR-0351 UX", () => {
  it("renders running progress without raw pipeline counters or a fake transcript workspace", () => {
    const job = transcriptJob("diarizing");
    job.progress = {
      ...job.progress,
      audioPipelineEtaSeconds: 130,
      audioPipelinePercentComplete: 18,
      currentChunkIndex: 0,
      percentComplete: 0,
      processedMediaSeconds: 0,
      totalChunks: 2,
      totalMediaSeconds: 600,
    };

    const wrapper = mount(TranscriptWorkspaceShell, {
      props: {
        abortState: { message: null, status: "idle" },
        canEditSpeakerOverlays: false,
        canSaveTranscript: false,
        currentJob: job,
        errorMessage: null,
        runtimeStatus: "running",
        saveErrorMessage: null,
        saveStatus: "idle",
        selectedTranscriptFile: null,
        speakerOverlayEntries: [],
        speakerOverlayErrorMessage: null,
        speakerOverlayStatus: "idle",
        transcript: null,
        transcriptFileError: null,
      },
    });

    expect(wrapper.get("[data-test='transcript-progress-title']").text()).toContain(
      "Vi skapar ditt transkript",
    );
    expect(wrapper.get("[data-test='transcript-progress-phase']").text()).toContain(
      "Hittar talare",
    );
    expect(wrapper.find("[data-test='transcript-progress-percent']").exists()).toBe(false);
    expect(wrapper.find("[data-test='transcript-progress-eta']").exists()).toBe(false);
    expect(wrapper.find("[data-test='transcript-progress-duration']").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("18 %");
    expect(wrapper.text()).not.toContain("2:10");
    expect(wrapper.find("[data-test='transcript-result-surface']").exists()).toBe(false);
    expect(wrapper.find("[data-test='transcript-speaker-overlays']").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("0 %");
    expect(wrapper.text()).not.toContain("diarizing");
    expect(wrapper.text()).not.toContain("Talare och export");
    expect(wrapper.text()).not.toContain("Ladda ner");
  });

  it("renders the autosaved workspace with one selected export format and stable actions", async () => {
    const wrapper = mount(TranscriptWorkspaceShell, {
      props: {
        abortState: { message: null, status: "idle" },
        canEditSpeakerOverlays: true,
        canRequestFormatterExport: true,
        canSaveTranscript: false,
        currentJob: null,
        errorMessage: null,
        formatterExportArtifacts: [
          {
            artifact_key: "transcript_txt",
            content_type: "text/plain",
            filename: "transcript.txt",
            requested_artifact: "txt",
            size_bytes: 12,
          },
          {
            artifact_key: "transcript_md",
            content_type: "text/markdown",
            filename: "transcript.md",
            requested_artifact: "md",
            size_bytes: 18,
          },
        ],
        formatterExportErrorMessage: null,
        formatterExportStatus: "succeeded",
        runtimeStatus: "succeeded",
        saveErrorMessage: null,
        saveStatus: "saved",
        selectedTranscriptFile: null,
        speakerOverlayEntries: [
          { canonical_speaker_label: "SPEAKER_00", display_name: "Anna Andersson" },
          { canonical_speaker_label: "SPEAKER_01", display_name: "Bo Berg" },
        ],
        speakerOverlayErrorMessage: null,
        speakerOverlayStatus: "saved",
        transcript: {
          schemaVersion: "transcript_json_v1",
          transcriptText: "Hej. Välkomna.",
          segments: [
            {
              id: "seg_1",
              startSeconds: 0,
              endSeconds: 1,
              speakerLabel: "SPEAKER_00",
              text: "Hej.",
            },
            {
              id: "seg_2",
              startSeconds: 1,
              endSeconds: 2,
              speakerLabel: "SPEAKER_01",
              text: "Välkomna.",
            },
          ],
        },
        transcriptFileError: null,
      },
    });

    expect(wrapper.get("[data-test='transcript-save-state']").text()).toContain(
      "Sparat automatiskt",
    );
    expect(wrapper.find("[data-test='transcript-save-button']").exists()).toBe(false);
    expect(wrapper.get("[data-test='transcript-inspector']").text()).toContain(
      "Talare och export",
    );
    expect(wrapper.get("[data-test='transcript-speaker-overlay-state']").text()).toContain(
      "Namnen är sparade.",
    );
    expect(wrapper.find("[data-test='transcript-speaker-overlays-save']").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Talarnamn");
    expect(wrapper.text()).not.toContain("Skapa exportfiler");
    expect(wrapper.text()).not.toContain("Skapa igen");
    expect(wrapper.find("[data-test='transcript-download-artifact-transcript_txt']").exists()).toBe(
      false,
    );
    expect(wrapper.find("[data-test='transcript-save-artifact-transcript_txt']").exists()).toBe(
      false,
    );
    expect(wrapper.get("[data-test='transcript-result-surface']").classes()).toContain(
      "@container",
    );
    expect(wrapper.get("[data-test='transcript-result-grid']").classes()).toContain(
      "@min-[56rem]:grid-cols-[minmax(0,1fr)_minmax(18rem,21rem)]",
    );

    const formatOptions = wrapper.findAll("[data-test^='transcript-format-option-']");
    expect(formatOptions).toHaveLength(4);
    expect(wrapper.get("[data-test='transcript-format-option-txt']").classes()).toContain(
      "text-canvas",
    );
    expect(wrapper.get("[data-test='transcript-format-option-txt']").classes()).not.toContain(
      "text-navy",
    );
    expect(wrapper.get("[data-test='transcript-download-selected-format']").text()).toBe(
      "Ladda ner",
    );
    expect(wrapper.get("[data-test='transcript-save-selected-format']").text()).toBe("Mina filer");

    await wrapper.get("[data-test='transcript-format-option-md']").trigger("click");
    expect(wrapper.get("[data-test='transcript-format-option-md']").classes()).toContain(
      "text-canvas",
    );
    expect(wrapper.get("[data-test='transcript-format-option-md']").classes()).not.toContain(
      "text-navy",
    );
    expect(wrapper.get("[data-test='transcript-format-option-txt']").classes()).toContain(
      "text-navy",
    );
    expect(wrapper.get("[data-test='transcript-format-option-md']").attributes("aria-pressed"))
      .toBe("true");
    await wrapper.get("[data-test='transcript-download-selected-format']").trigger("click");
    await wrapper.get("[data-test='transcript-save-selected-format']").trigger("click");

    expect(wrapper.emitted("downloadFormatterArtifact")?.[0]?.[0]).toBe("md");
    expect(wrapper.emitted("saveFormatterArtifact")?.[0]?.[0]).toBe("md");
  });
});
