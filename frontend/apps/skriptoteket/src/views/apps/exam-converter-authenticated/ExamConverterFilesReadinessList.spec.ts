/**
 * Exam Converter files inspection row behavior.
 *
 * Slice purpose:
 *   Prove generated file rows keep format, readiness, and actions together in
 *   an overflow-safe surface for `Filer`.
 *
 * Expected behavior:
 *   File rows render as wrapping rows rather than wide table columns, with
 *   download/save actions still gated by the producer-owned file state.
 *
 * Recommended implementation shape:
 *   Use compact row cards inside the active `Filer` mode and keep actions
 *   adjacent to the file they affect.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamConverterFilesReadinessList from "./ExamConverterFilesReadinessList.vue";

describe("ExamConverterFilesReadinessList", () => {
  it("keeps generated-file actions in wrapping rows instead of a wide table", () => {
    const wrapper = mount(ExamConverterFilesReadinessList, {
      props: {
        actionStates: {},
        actionsEnabled: true,
        actionNotice: null,
        files: [
          {
            artifactActionReference: {
              artifactKey: "examnet_pdf",
              authority: "replay_result",
            },
            artifactKey: "examnet_pdf",
            availability: "available",
            contentType: "application/pdf",
            exportEnabled: true,
            filename: "Nationellt prov med långt filnamn Exam.net.pdf",
            kindLabel: "PDF",
            reasonCode: "target_available",
            readiness: "ready",
            sha256: "sha256:pdf",
            sizeBytes: 12345,
            sizeLabel: "12 kB",
            statusLabel: "Kan hämtas",
            unavailableCode: null,
          },
        ],
      },
    });

    const row = wrapper.get('[data-test="exam-converter-file-row-examnet_pdf"]');
    expect(wrapper.find("table").exists()).toBe(false);
    expect(row.text()).toContain("Nationellt prov med långt filnamn Exam.net.pdf");
    expect(row.text()).toContain("PDF");
    expect(row.text()).toContain("Kan hämtas");
    expect(row.text()).toContain("Hämta");
    expect(row.text()).toContain("Spara");
    expect(wrapper.text()).not.toContain("Åtgärd");
  });
});
