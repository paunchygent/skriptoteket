/** Single-file result saves confirm only after the API succeeds. */
import { flushPromises } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { fileApiMocks, mountReadySingleFileResult, setupSingleFileView } from "./documentConverterSingleFileView.test-support";
import { useToastStore } from "../../../stores/toast";

describe("Single-file save confirmation", () => {
  setupSingleFileView();

  it("confirms an awaited save and reports rejection without another success", async () => {
    const wrapper = await mountReadySingleFileResult();

    const success = vi.spyOn(useToastStore(), "success");
    let finishSave!: () => void;
    fileApiMocks.saveDocumentConverterJobArtifact.mockReturnValueOnce(
      new Promise<void>((resolve) => { finishSave = resolve; }),
    );
    await wrapper.get('[data-testid="document-converter-save"]').trigger("click");
    await flushPromises();
    expect(fileApiMocks.saveDocumentConverterJobArtifact).toHaveBeenCalledWith({
      filenameStem: "lektion", jobId: "job-ready",
    });
    expect(success).not.toHaveBeenCalled();
    finishSave();
    await flushPromises();
    expect(success).toHaveBeenCalledTimes(1);
    expect(success.mock.calls[0]?.[0]).toMatch(/Mina filer/);
    fileApiMocks.saveDocumentConverterJobArtifact.mockRejectedValueOnce(new Error("network"));
    await wrapper.get('[data-testid="document-converter-save"]').trigger("click");
    await flushPromises();
    expect(success).toHaveBeenCalledTimes(1);
    expect(wrapper.get('[role="alert"]').text()).toMatch(/spara/i);

  });
});
