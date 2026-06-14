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
import type {
  SirConvertTranscriptJob,
  SirConvertTranscriptProgressPhase,
} from "../../../api/sirConvertGateway";

function transcriptJob(phase: SirConvertTranscriptProgressPhase): SirConvertTranscriptJob {
  return {
    jobId: "job_transcript_1",
    progress: {
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

describe("TranscriptWorkspaceShell", () => {
  it("maps upstream progress phases to safe teacher-facing progress copy", () => {
    const wrapper = mount(TranscriptWorkspaceShell, {
      props: {
        abortState: { message: null, status: "idle" },
        canEditSpeakerOverlays: false,
        canSaveTranscript: false,
        currentJob: transcriptJob("normalizing_audio"),
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

    expect(wrapper.text()).toContain("Förbereder ljudet.");
    expect(wrapper.text()).not.toContain("sidecar");
    expect(wrapper.text()).not.toContain("model");
    expect(wrapper.text()).not.toContain("pyannote");
  });

  it("renders full running progress from the Gateway snapshot", () => {
    const wrapper = mount(TranscriptWorkspaceShell, {
      props: {
        abortState: { message: null, status: "idle" },
        canEditSpeakerOverlays: false,
        canSaveTranscript: false,
        currentJob: transcriptJob("transcribing"),
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

    expect(wrapper.get("[data-test='transcript-progress-phase']").text()).toContain(
      "Skriver ut talet.",
    );
    expect(wrapper.get("[data-test='transcript-progress-percent']").text()).toContain("35 %");
    expect(wrapper.get("[data-test='transcript-progress-duration']").text()).toContain(
      "0:42 av 2:00",
    );
    expect(wrapper.get("[data-test='transcript-progress-chunks']").text()).toContain("Del 2 av 3");
    expect(wrapper.get("[data-test='transcript-progress-heartbeat']").text()).toContain(
      "Senast uppdaterad",
    );
  });

  it("renders upload progress before Sir Convert returns a job id", () => {
    const wrapper = mount(TranscriptWorkspaceShell, {
      props: {
        abortState: { message: null, status: "idle" },
        canEditSpeakerOverlays: false,
        canSaveTranscript: false,
        currentJob: null,
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
        uploadState: {
          loadedBytes: 8 * 1024 * 1024,
          percentComplete: 50,
          status: "uploading",
          totalBytes: 16 * 1024 * 1024,
        },
      },
    });

    expect(wrapper.get("[data-test='transcript-progress-phase']").text()).toContain(
      "Laddar upp inspelningen.",
    );
    expect(wrapper.get("[data-test='transcript-progress-percent']").text()).toContain("50 %");
    expect(wrapper.get("[data-test='transcript-upload-bytes']").text()).toContain(
      "8.0 MB av 16.0 MB",
    );
    expect(wrapper.find("[data-test='transcript-progress-heartbeat']").exists()).toBe(false);
  });

  it("renders abort pending and failure feedback without ending the running surface", () => {
    const wrapper = mount(TranscriptWorkspaceShell, {
      props: {
        abortState: {
          message: "Det gick inte att avbryta. Transkriberingen fortsätter.",
          status: "failed",
        },
        canEditSpeakerOverlays: false,
        canSaveTranscript: false,
        currentJob: transcriptJob("transcribing"),
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

    expect(wrapper.find("[data-test='transcript-running-surface']").exists()).toBe(true);
    expect(wrapper.get("[data-test='transcript-abort-state']").text()).toContain(
      "Det gick inte att avbryta. Transkriberingen fortsätter.",
    );
  });

  it("emits save when a completed transcript can be persisted", async () => {
    const wrapper = mount(TranscriptWorkspaceShell, {
      props: {
        abortState: { message: null, status: "idle" },
        canEditSpeakerOverlays: false,
        canSaveTranscript: true,
        currentJob: null,
        errorMessage: null,
        runtimeStatus: "succeeded",
        saveErrorMessage: null,
        saveStatus: "idle",
        selectedTranscriptFile: null,
        speakerOverlayEntries: [],
        speakerOverlayErrorMessage: null,
        speakerOverlayStatus: "idle",
        transcript: {
          schemaVersion: "transcript_json_v1",
          transcriptText: "Hej.",
          segments: [
            {
              id: "seg_1",
              startSeconds: 0,
              endSeconds: 1,
              speakerLabel: "SPEAKER_00",
              text: "Hej.",
            },
          ],
        },
        transcriptFileError: null,
      },
    });

    await wrapper.get("[data-test='transcript-save-button']").trigger("click");

    expect(wrapper.emitted("saveTranscript")).toHaveLength(1);
    expect(wrapper.get("[data-test='transcript-save-state']").text()).toContain(
      "Tillfälligt transkript",
    );
  });

  it("shows saved state and disables duplicate saves", () => {
    const wrapper = mount(TranscriptWorkspaceShell, {
      props: {
        abortState: { message: null, status: "idle" },
        canEditSpeakerOverlays: false,
        canSaveTranscript: false,
        currentJob: null,
        errorMessage: null,
        runtimeStatus: "succeeded",
        saveErrorMessage: null,
        saveStatus: "saved",
        selectedTranscriptFile: null,
        speakerOverlayEntries: [],
        speakerOverlayErrorMessage: null,
        speakerOverlayStatus: "idle",
        transcript: {
          schemaVersion: "transcript_json_v1",
          transcriptText: "Hej.",
          segments: [
            {
              id: "seg_1",
              startSeconds: 0,
              endSeconds: 1,
              speakerLabel: "SPEAKER_00",
              text: "Hej.",
            },
          ],
        },
        transcriptFileError: null,
      },
    });

    expect(wrapper.text()).toContain("Transkriptet är sparat.");
    expect(wrapper.get("[data-test='transcript-save-button']").attributes("disabled")).toBe("");
  });

  it("renders editable speaker overlays over saved transcript segments", async () => {
    const wrapper = mount(TranscriptWorkspaceShell, {
      props: {
        abortState: { message: null, status: "idle" },
        canEditSpeakerOverlays: true,
        canSaveTranscript: false,
        currentJob: null,
        errorMessage: null,
        runtimeStatus: "succeeded",
        saveErrorMessage: null,
        saveStatus: "saved",
        selectedTranscriptFile: null,
        speakerOverlayEntries: [
          { canonical_speaker_label: "SPEAKER_00", display_name: "Anna Andersson" },
        ],
        speakerOverlayErrorMessage: null,
        speakerOverlayStatus: "idle",
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

    expect(wrapper.text()).toContain("Anna Andersson");
    expect(wrapper.text()).toContain("SPEAKER_01");
    await wrapper
      .get<HTMLInputElement>("[data-test='transcript-speaker-name-SPEAKER_01']")
      .setValue("Bo Berg");
    await wrapper.get("[data-test='transcript-speaker-overlays-save']").trigger("click");

    expect(wrapper.emitted("speakerOverlayChanged")).toEqual([["SPEAKER_01", "Bo Berg"]]);
    expect(wrapper.emitted("saveSpeakerOverlays")).toHaveLength(1);
  });

  it("renders formatter replay command and producer artifact actions only for valid refs", async () => {
    const wrapper = mount(TranscriptWorkspaceShell, {
      props: {
        abortState: { message: null, status: "idle" },
        canEditSpeakerOverlays: true,
        canRequestFormatterReplay: true,
        canSaveTranscript: false,
        currentJob: null,
        errorMessage: null,
        formatterReplayArtifacts: [],
        formatterReplayErrorMessage: null,
        formatterReplayStatus: "not_requested",
        runtimeStatus: "succeeded",
        saveErrorMessage: null,
        saveStatus: "saved",
        selectedTranscriptFile: null,
        speakerOverlayEntries: [
          { canonical_speaker_label: "SPEAKER_00", display_name: "Anna Andersson" },
        ],
        speakerOverlayErrorMessage: null,
        speakerOverlayStatus: "saved",
        transcript: {
          schemaVersion: "transcript_json_v1",
          transcriptText: "Hej.",
          segments: [
            {
              id: "seg_1",
              startSeconds: 0,
              endSeconds: 1,
              speakerLabel: "SPEAKER_00",
              text: "Hej.",
            },
          ],
        },
        transcriptFileError: null,
      },
    });

    await wrapper.get("[data-test='transcript-formatter-replay-button']").trigger("click");

    expect(wrapper.emitted("requestFormatterReplay")).toHaveLength(1);
    expect(wrapper.find("[data-test='transcript-download-artifact-transcript_txt']").exists()).toBe(
      false,
    );
    expect(wrapper.find("[data-test='transcript-save-artifact-transcript_txt']").exists()).toBe(
      false,
    );
    await wrapper.setProps({
      canRequestFormatterReplay: false,
      formatterReplayArtifacts: [
        {
          artifact_key: "transcript_txt",
          content_type: "text/plain",
          filename: "transcript_txt.txt",
          requested_artifact: "txt",
          size_bytes: 12,
        },
      ],
      formatterReplayStatus: "succeeded",
    });

    expect(wrapper.get("[data-test='transcript-formatter-replay-state']").text()).toContain(
      "Exportfiler är klara",
    );
    expect(wrapper.text()).toContain("TXT");
    expect(wrapper.find("a[download]").exists()).toBe(false);

    const download = wrapper.get("[data-test='transcript-download-artifact-transcript_txt']");
    const save = wrapper.get("[data-test='transcript-save-artifact-transcript_txt']");
    expect(download.attributes("disabled")).toBeUndefined();
    expect(save.attributes("disabled")).toBeUndefined();

    await download.trigger("click");
    await save.trigger("click");

    expect(wrapper.emitted("downloadFormatterArtifact")?.[0]?.[0]).toMatchObject({
      artifact_key: "transcript_txt",
    });
    expect(wrapper.emitted("saveFormatterArtifact")?.[0]?.[0]).toMatchObject({
      artifact_key: "transcript_txt",
    });
  });

  it("shows formatter artifact action progress and failure states", () => {
    const wrapper = mount(TranscriptWorkspaceShell, {
      props: {
        abortState: { message: null, status: "idle" },
        canEditSpeakerOverlays: true,
        canRequestFormatterReplay: false,
        canSaveTranscript: false,
        currentJob: null,
        errorMessage: null,
        formatterArtifactActionStates: {
          transcript_txt: {
            download: "failed",
            save: "running",
            savedFilename: null,
          },
        },
        formatterReplayArtifacts: [
          {
            artifact_key: "transcript_txt",
            content_type: "text/plain",
            filename: "transcript_txt.txt",
            requested_artifact: "txt",
            size_bytes: 12,
          },
        ],
        formatterReplayErrorMessage: null,
        formatterReplayStatus: "succeeded",
        runtimeStatus: "succeeded",
        saveErrorMessage: null,
        saveStatus: "saved",
        selectedTranscriptFile: null,
        speakerOverlayEntries: [
          { canonical_speaker_label: "SPEAKER_00", display_name: "Anna Andersson" },
        ],
        speakerOverlayErrorMessage: null,
        speakerOverlayStatus: "saved",
        transcript: {
          schemaVersion: "transcript_json_v1",
          transcriptText: "Hej.",
          segments: [
            {
              id: "seg_1",
              startSeconds: 0,
              endSeconds: 1,
              speakerLabel: "SPEAKER_00",
              text: "Hej.",
            },
          ],
        },
        transcriptFileError: null,
      },
    });

    expect(wrapper.get("[data-test='transcript-download-artifact-transcript_txt']").text()).toContain(
      "Försök igen",
    );
    expect(wrapper.get("[data-test='transcript-save-artifact-transcript_txt']").text()).toContain(
      "Sparar",
    );
    expect(
      wrapper.get("[data-test='transcript-save-artifact-transcript_txt']").attributes("disabled"),
    ).toBe("");
    expect(wrapper.get("[data-test='transcript-artifact-action-state-transcript_txt']").text()).toContain(
      "Det gick inte att hämta filen.",
    );
  });
});
