/**
 * Conversion Hub transcript host PR-0351 UX specs.
 *
 * Domain purpose:
 *   Prove the transcript host enforces the approved completion workspace:
 *   automatic transcript persistence, complete speaker-overlay persistence,
 *   selected-format export actions, and absence of retired manual controls.
 *
 * Relationships:
 *   - Uses `ConversionHubTranscriptHost.specSupport.ts` for authenticated host
 *     runtime seams.
 *   - Complements shell-level PR-0351 DOM contract tests.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  artifactActionMocks,
  browserDownloadMocks,
  formatterExportMocks,
  formatterExportResponse,
  mountHost,
  overlaysResponse,
  resetTranscriptHostHarness,
  saveSpeakerNames,
  saveTranscript,
  startExportReadyTranscript,
  startSuccessfulTranscript,
  transcriptSaveMocks,
} from "./ConversionHubTranscriptHost.specSupport";

describe("ConversionHubTranscriptHost PR-0351 UX", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    resetTranscriptHostHarness();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("autosaves the completed transcript and skips the generic manual save gate", async () => {
    const wrapper = mountHost();

    await startSuccessfulTranscript(wrapper);

    expect(wrapper.get("[data-test='transcript-host-layout']").classes()).toEqual(
      expect.arrayContaining([
        "col-span-full",
        "grid-cols-1",
        "min-[821px]:grid-cols-[minmax(14rem,17rem)_minmax(0,1fr)]",
        "min-[1181px]:grid-cols-[minmax(15rem,18rem)_minmax(0,1fr)]",
      ]),
    );
    expect(transcriptSaveMocks.saveConversionHubTranscript).toHaveBeenCalledTimes(1);
    expect(wrapper.find("[data-test='transcript-save-button']").exists()).toBe(false);
    expect(wrapper.get("[data-test='transcript-save-state']").text()).toContain(
      "Sparat automatiskt",
    );
    expect(wrapper.get("[data-test='transcript-inspector']").text()).toContain(
      "Talare och export",
    );
    expect(wrapper.text()).not.toContain("Transkriptet är klart men inte sparat");
    expect(wrapper.text()).not.toContain("Tillfälligt transkript");
  });

  it("uses selected-format actions to create product export state before download", async () => {
    formatterExportMocks.requestConversionHubTranscriptFormatterExport.mockResolvedValueOnce(
      formatterExportResponse({
        artifacts: [
          {
            artifact_key: "transcript_txt",
            content_type: "text/plain",
            filename: "transcript_txt.txt",
            requested_artifact: "txt",
            size_bytes: 12,
          },
          {
            artifact_key: "transcript_md",
            content_type: "text/markdown",
            filename: "transcript_md.md",
            requested_artifact: "md",
            size_bytes: 18,
          },
        ],
      }),
    );
    artifactActionMocks.downloadConversionHubTranscriptFormatterArtifact.mockResolvedValueOnce({
      blob: new Blob(["# Hej"], { type: "text/markdown" }),
      filename: "transcript_md.md",
    });

    const wrapper = mountHost();

    await startSuccessfulTranscript(wrapper);
    await saveSpeakerNames(wrapper);

    await wrapper.get("[data-test='transcript-format-option-md']").trigger("click");
    await wrapper.get("[data-test='transcript-download-selected-format']").trigger("click");
    await flushPromises();

    expect(formatterExportMocks.requestConversionHubTranscriptFormatterExport).toHaveBeenCalledWith(
      { transcriptId: "saved_transcript_1" },
    );
    expect(
      artifactActionMocks.downloadConversionHubTranscriptFormatterArtifact,
    ).toHaveBeenCalledWith({
      artifactKey: "transcript_md",
      transcriptId: "saved_transcript_1",
    });
    expect(browserDownloadMocks.triggerBrowserDownload).toHaveBeenCalledOnce();
    expect(wrapper.get("[data-test='transcript-download-selected-format']").text()).toBe(
      "Ladda ner",
    );
    expect(wrapper.get("[data-test='transcript-save-selected-format']").text()).toBe("Mina filer");
    expect(wrapper.text()).not.toContain("Ladda ner MD");
  });

  it("keeps export disabled and truthful when overlay save returns an empty persisted list", async () => {
    transcriptSaveMocks.updateConversionHubTranscriptSpeakerOverlays.mockResolvedValueOnce(
      overlaysResponse([]),
    );

    const wrapper = mountHost();

    await startExportReadyTranscript(wrapper);

    expect(wrapper.get("[data-test='transcript-speaker-overlay-state']").text()).toContain(
      "Fyll i namn för alla talare",
    );
    expect(wrapper.get("[data-test='transcript-formatter-export-state']").text()).toContain(
      "Fyll i namn för alla talare innan filer kan skapas.",
    );
    expect(wrapper.find("[data-test='transcript-speaker-overlays-save']").exists()).toBe(false);
    expect(wrapper.get("[data-test='transcript-download-selected-format']").attributes("disabled"))
      .toBe("");
    expect(wrapper.get("[data-test='transcript-save-selected-format']").attributes("disabled"))
      .toBe("");
    expect(wrapper.text()).toContain("SPEAKER_00");
    expect(wrapper.text()).not.toContain("Talarnamn");
  });

  it("keeps export disabled until all transcript speakers have persisted names", async () => {
    transcriptSaveMocks.updateConversionHubTranscriptSpeakerOverlays.mockResolvedValueOnce(
      overlaysResponse([{ canonical_speaker_label: "SPEAKER_00", display_name: "Anna Andersson" }]),
    );

    const wrapper = mountHost();

    await startExportReadyTranscript(wrapper);

    expect(wrapper.get("[data-test='transcript-speaker-overlay-state']").text()).toContain(
      "Fyll i namn för alla talare",
    );
    expect(wrapper.get("[data-test='transcript-formatter-export-state']").text()).toContain(
      "Fyll i namn för alla talare innan filer kan skapas.",
    );
    expect(wrapper.find("[data-test='transcript-speaker-overlays-save']").exists()).toBe(false);
    expect(wrapper.get("[data-test='transcript-download-selected-format']").attributes("disabled"))
      .toBe("");
    expect(wrapper.get("[data-test='transcript-save-selected-format']").attributes("disabled"))
      .toBe("");
    expect(formatterExportMocks.requestConversionHubTranscriptFormatterExport).not.toHaveBeenCalled();
  });

  it("enables export only after non-empty overlays are persisted", async () => {
    transcriptSaveMocks.updateConversionHubTranscriptSpeakerOverlays.mockResolvedValueOnce(
      overlaysResponse([
        { canonical_speaker_label: "SPEAKER_00", display_name: "Anna Andersson" },
        { canonical_speaker_label: "SPEAKER_01", display_name: "Bo Berg" },
      ]),
    );

    const wrapper = mountHost();

    await startSuccessfulTranscript(wrapper);
    await saveTranscript(wrapper);

    expect(wrapper.get("[data-test='transcript-speaker-overlay-state']").text()).toContain(
      "Fyll i namn för alla talare",
    );
    expect(wrapper.find("[data-test='transcript-speaker-overlays-save']").exists()).toBe(false);
    expect(wrapper.get("[data-test='transcript-download-selected-format']").attributes("disabled"))
      .toBe("");

    await saveSpeakerNames(wrapper);

    expect(transcriptSaveMocks.updateConversionHubTranscriptSpeakerOverlays).toHaveBeenCalledWith({
      request: {
        overlays: [
          { canonical_speaker_label: "SPEAKER_00", display_name: "Anna Andersson" },
          { canonical_speaker_label: "SPEAKER_01", display_name: "Bo Berg" },
        ],
      },
      transcriptId: "saved_transcript_1",
    });
    expect(wrapper.get("[data-test='transcript-speaker-overlay-state']").text()).toContain(
      "Namnen är sparade.",
    );
    expect(wrapper.get("[data-test='transcript-formatter-export-state']").text()).toContain(
      "Välj format och använd en av åtgärderna.",
    );
    expect(wrapper.find("[data-test='transcript-speaker-overlays-save']").exists()).toBe(false);
    expect(
      wrapper.get("[data-test='transcript-download-selected-format']").attributes("disabled"),
    ).toBeUndefined();
    expect(wrapper.text()).not.toContain("Exportfiler");
    expect(wrapper.text()).toContain("Anna Andersson");
    expect(wrapper.text()).toContain("Bo Berg");
  });
});
