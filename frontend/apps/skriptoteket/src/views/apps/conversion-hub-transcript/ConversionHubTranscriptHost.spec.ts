/**
 * Transcript host race and formatter-export specs.
 *
 * Domain purpose:
 *   Prove the authenticated transcript host keeps speaker-overlay loading,
 *   saving, and selected-format export affordances truthful across the
 *   saved-transcript flow.
 *
 * Relationships:
 *   - Exercises `ConversionHubTranscriptHost.vue` as the stateful DOM boundary.
 *   - Mocks only product-edge API/composable seams.
 */

import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";

import type {
  ConversionHubTranscriptSpeakerOverlaysResponse,
} from "../../../api/conversionHubTranscriptSaves";
import {
  artifactActionMocks,
  deferred,
  formatterExportMocks,
  formatterExportResponse,
  mountHost,
  overlaysResponse,
  resetTranscriptHostHarness,
  saveTranscript,
  startExportReadyTranscript,
  startSuccessfulTranscript,
  transcriptSaveMocks,
} from "./ConversionHubTranscriptHost.specSupport";

describe("ConversionHubTranscriptHost", () => {
  beforeEach(() => {
    resetTranscriptHostHarness();
  });

  it("waits for overlay readback before rendering editable speaker inputs", async () => {
    const pendingOverlays = deferred<ConversionHubTranscriptSpeakerOverlaysResponse>();
    transcriptSaveMocks.getConversionHubTranscriptSpeakerOverlays.mockReturnValueOnce(
      pendingOverlays.promise,
    );

    const wrapper = mountHost();

    await startSuccessfulTranscript(wrapper);
    await saveTranscript(wrapper);

    expect(wrapper.html()).not.toContain('data-test="transcript-speaker-overlays"');
    expect(wrapper.get("[data-test='transcript-save-state']").text()).toContain("Sparar");

    pendingOverlays.resolve(overlaysResponse([]));
    await flushPromises();

    expect(wrapper.html()).toContain('data-test="transcript-speaker-overlays"');
    expect(wrapper.get("[data-test='transcript-save-state']").text()).toContain("Sparat");
  });

  it("requests product-owned formatter export state and renders verified artifacts", async () => {
    const wrapper = mountHost();
    await startExportReadyTranscript(wrapper);
    await wrapper.get("[data-test='transcript-download-selected-format']").trigger("click");
    await flushPromises();
    expect(formatterExportMocks.requestConversionHubTranscriptFormatterExport).toHaveBeenCalledWith({ transcriptId: "saved_transcript_1" });
    expect(formatterExportMocks.getConversionHubTranscriptFormatterExport).not.toHaveBeenCalled();
    expect(artifactActionMocks.downloadConversionHubTranscriptFormatterArtifact).toHaveBeenCalledWith({ artifactKey: "transcript_txt", transcriptId: "saved_transcript_1" });
    expect(wrapper.get("[data-test='transcript-formatter-export-state']").text()).toContain("Fil hämtad.");
    expect(wrapper.find("[data-test='transcript-download-artifact-transcript_txt']").exists()).toBe(false);
  });

  it("renders pending export state and refreshes it through the product endpoint", async () => {
    formatterExportMocks.requestConversionHubTranscriptFormatterExport.mockResolvedValueOnce(
      formatterExportResponse({
        artifacts: [],
        conversion_hub_job_id: "local_export_job_1",
        status: "pending",
        updated_at: "2026-06-14T08:00:00Z",
      }),
    );
    formatterExportMocks.getConversionHubTranscriptFormatterExport.mockResolvedValueOnce(
      formatterExportResponse(),
    );
    const wrapper = mountHost();
    await startExportReadyTranscript(wrapper);
    await wrapper.get("[data-test='transcript-download-selected-format']").trigger("click");
    await flushPromises();

    expect(wrapper.get("[data-test='transcript-formatter-export-state']").text()).toContain("Filerna är köade.");

    await wrapper.get("[data-test='transcript-download-selected-format']").trigger("click");
    await flushPromises();

    expect(formatterExportMocks.getConversionHubTranscriptFormatterExport).toHaveBeenCalledWith({ transcriptId: "saved_transcript_1" });
    expect(wrapper.get("[data-test='transcript-formatter-export-state']").text()).toContain("Fil hämtad.");
  });

  it("keeps running export state refreshable through the product endpoint", async () => {
    formatterExportMocks.requestConversionHubTranscriptFormatterExport.mockResolvedValueOnce(
      formatterExportResponse({
        artifacts: [],
        conversion_hub_job_id: "local_export_job_1",
        status: "running",
        updated_at: "2026-06-14T08:00:00Z",
      }),
    );
    formatterExportMocks.getConversionHubTranscriptFormatterExport.mockResolvedValueOnce(
      formatterExportResponse(),
    );
    const wrapper = mountHost();
    await startExportReadyTranscript(wrapper);
    await wrapper.get("[data-test='transcript-download-selected-format']").trigger("click");
    await flushPromises();

    expect(wrapper.get("[data-test='transcript-formatter-export-state']").text()).toContain("Filer skapas.");
    expect(wrapper.get("[data-test='transcript-download-selected-format']").attributes("disabled"))
      .toBeUndefined();

    await wrapper.get("[data-test='transcript-download-selected-format']").trigger("click");
    await flushPromises();

    expect(formatterExportMocks.getConversionHubTranscriptFormatterExport).toHaveBeenCalledWith({ transcriptId: "saved_transcript_1" });
    expect(wrapper.get("[data-test='transcript-formatter-export-state']").text()).toContain("Fil hämtad.");
  });

  it("renders failed product export state and retries by recording a new intent", async () => {
    formatterExportMocks.requestConversionHubTranscriptFormatterExport
      .mockResolvedValueOnce(
        formatterExportResponse({
          artifacts: [],
          conversion_hub_job_id: "local_export_job_1",
          error_message: "Filerna kunde inte skapas. Försök igen.",
          status: "failed",
        }),
      )
      .mockResolvedValueOnce(formatterExportResponse());

    const wrapper = mountHost();

    await startExportReadyTranscript(wrapper);

    await wrapper.get("[data-test='transcript-download-selected-format']").trigger("click");
    await flushPromises();

    expect(wrapper.get("[data-test='transcript-formatter-export-state']").text()).toContain("Filerna kunde inte skapas.");

    await wrapper.get("[data-test='transcript-download-selected-format']").trigger("click");
    await flushPromises();

    expect(formatterExportMocks.requestConversionHubTranscriptFormatterExport).toHaveBeenCalledTimes(2);
    expect(wrapper.get("[data-test='transcript-formatter-export-state']").text()).toContain("Fil hämtad.");
  });
});
