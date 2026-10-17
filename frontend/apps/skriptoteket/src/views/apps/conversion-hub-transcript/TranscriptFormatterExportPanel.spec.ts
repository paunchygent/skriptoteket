/**
 * Transcript formatter export panel specs.
 *
 * Domain purpose:
 *   Prove format selection reaches export commands and unavailable or running
 *   artifacts cannot trigger download or save work.
 *
 * Relationships:
 *   - Exercises `TranscriptFormatterExportPanel.vue` as the DOM boundary.
 *   - Complements host specs that prove the emitted export/save behavior.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type {
  ConversionHubTranscriptFormatterArtifactRef,
  ConversionHubTranscriptFormatterExportStatus,
} from "../../../api/conversionHubTranscriptFormatterExports";
import TranscriptFormatterExportPanel from "./TranscriptFormatterExportPanel.vue";
import type {
  FormatterArtifactActionStates,
} from "./transcriptFormatterArtifactActions";

const TXT_ARTIFACT: ConversionHubTranscriptFormatterArtifactRef = {
  artifact_key: "transcript_txt",
  content_type: "text/plain",
  filename: "transcript.txt",
  requested_artifact: "txt",
  size_bytes: 12,
};

function mountPanel(
  overrides: Partial<{
    actionStates: FormatterArtifactActionStates;
    artifacts: readonly ConversionHubTranscriptFormatterArtifactRef[];
    canRequest: boolean;
    errorMessage: string | null;
    status: ConversionHubTranscriptFormatterExportStatus;
  }> = {},
) {
  return mount(TranscriptFormatterExportPanel, {
    props: {
      actionStates: overrides.actionStates ?? {},
      artifacts: overrides.artifacts ?? [TXT_ARTIFACT],
      canRequest: overrides.canRequest ?? false,
      errorMessage: overrides.errorMessage ?? null,
      status: overrides.status ?? "succeeded",
    },
  });
}

describe("TranscriptFormatterExportPanel", () => {
  it("sends the selected format to both commands after keyboard selection", async () => {
    const wrapper = mountPanel({ canRequest: true });
    const txt = wrapper.get("[data-test='transcript-format-option-txt']");
    const md = wrapper.get("[data-test='transcript-format-option-md']");

    expect(txt.attributes("aria-checked")).toBe("true");
    await txt.trigger("keydown", { key: "ArrowRight" });
    expect(md.attributes("aria-checked")).toBe("true");
    expect(txt.attributes("aria-checked")).toBe("false");

    await wrapper.get("[data-test='transcript-download-selected-format']").trigger("click");
    await wrapper.get("[data-test='transcript-save-selected-format']").trigger("click");

    expect(wrapper.emitted("downloadFormatterArtifact")).toEqual([["md"]]);
    expect(wrapper.emitted("saveFormatterArtifact")).toEqual([["md"]]);
  });

  it("blocks unavailable formats and running artifact actions without emitting work", async () => {
    const wrapper = mountPanel();
    const download = wrapper.get("[data-test='transcript-download-selected-format']");
    const save = wrapper.get("[data-test='transcript-save-selected-format']");

    await wrapper.get("[data-test='transcript-format-option-md']").trigger("click");
    expect(download.attributes("disabled")).toBe("");
    expect(save.attributes("disabled")).toBe("");
    await download.trigger("click");
    await save.trigger("click");

    await wrapper.get("[data-test='transcript-format-option-txt']").trigger("click");
    expect(download.attributes("disabled")).toBeUndefined();
    expect(save.attributes("disabled")).toBeUndefined();

    await wrapper.setProps({
      canRequest: true,
      actionStates: {
        transcript_txt: { download: "running", save: "idle", savedFilename: null },
      },
    });
    expect(download.attributes("disabled")).toBe("");
    expect(save.attributes("disabled")).toBe("");
    await download.trigger("click");
    await save.trigger("click");
    expect(wrapper.emitted("downloadFormatterArtifact")).toBeUndefined();
    expect(wrapper.emitted("saveFormatterArtifact")).toBeUndefined();
  });
});
