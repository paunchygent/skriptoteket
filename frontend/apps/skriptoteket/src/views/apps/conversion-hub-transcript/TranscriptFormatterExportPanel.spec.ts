/**
 * Transcript formatter export panel specs.
 *
 * Domain purpose:
 *   Prove the saved transcript export controls keep selector state visually
 *   separate from neutral download and Mina filer command buttons.
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
  it("keeps selected format styling separate from neutral command buttons", async () => {
    const wrapper = mountPanel();

    const selectedTxt = wrapper.get("[data-test='transcript-format-option-txt']");
    const download = wrapper.get("[data-test='transcript-download-selected-format']");
    const save = wrapper.get("[data-test='transcript-save-selected-format']");

    expect(selectedTxt.attributes("aria-pressed")).toBe("true");
    expect(selectedTxt.classes()).toContain("bg-navy");
    expect(selectedTxt.classes()).toContain("text-canvas");

    for (const command of [download, save]) {
      expect(command.classes()).not.toContain("btn-cta");
      expect(command.classes()).not.toContain("bg-navy");
      expect(command.classes()).not.toContain("text-canvas");
      expect(command.classes()).toContain("bg-panel");
      expect(command.classes()).toContain("text-navy");
    }

    await wrapper.get("[data-test='transcript-format-option-md']").trigger("click");

    expect(wrapper.get("[data-test='transcript-format-option-md']").classes()).toContain(
      "bg-navy",
    );
    expect(wrapper.get("[data-test='transcript-format-option-md']").classes()).toContain(
      "text-canvas",
    );
  });
});
