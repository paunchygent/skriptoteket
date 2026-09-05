/**
 * Exam Converter authenticated conversion-start slice behavior.
 *
 * Slice purpose:
 *   Add the approved local conversion-start scaffold: enable the start action
 *   only for a single selected exam and selected output targets, show the
 *   teacher-facing running state with dynamic progress visualization, and
 *   define the compact result strip states.
 *
 * Expected behavior:
 *   The teacher can start one conversion after selecting a `.dxe` and at least
 *   one target format. Starting conversion must not invent question rows,
 *   file rows, reports, downloads, save controls, or upstream runtime details.
 *
 * Recommended implementation shape:
 *   Keep state in a small composable, render one `ExamConverterResultStrip`,
 *   keep local progress visually honest, and leave Gateway submit/poll/result
 *   plus upstream ETA/progress streams to later approved slices.
 */

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import ExamConverterResultStrip from "./exam-converter-authenticated/ExamConverterResultStrip.vue";
import type { ExamConverterResultStripState } from "./exam-converter-authenticated/useExamConverterConversionState";

const gatewayMocks = vi.hoisted(() => ({
  applyExamAuthoringCorrections: vi.fn(),
  downloadDigiExamMigrationArtifact: vi.fn(),
  downloadDigiExamMigrationCorrectionReplayArtifact: vi.fn(),
  getDigiExamMigrationJob: vi.fn(),
  getDigiExamMigrationResult: vi.fn(),
  issueExamAuthoringCorrectionSourceState: vi.fn(),
  listDigiExamMigrationArtifacts: vi.fn(),
  saveDigiExamMigrationArtifactToUserFiles: vi.fn(),
  submitDigiExamMigration: vi.fn(),
}));

vi.mock("../../api/examConverterLocal", () => ({
  downloadLocalExamConversionArtifact: gatewayMocks.downloadDigiExamMigrationArtifact,
  getLocalExamConversionJob: gatewayMocks.getDigiExamMigrationJob,
  getLocalExamConversionResult: gatewayMocks.getDigiExamMigrationResult,
  getLocalExamConversionSourceState: gatewayMocks.issueExamAuthoringCorrectionSourceState,
  listLocalExamConversionArtifacts: gatewayMocks.listDigiExamMigrationArtifacts,
  replayLocalExamConversion: vi.fn(),
  submitLocalExamConversion: gatewayMocks.submitDigiExamMigration,
}));

async function chooseSourceFile(wrapper: ReturnType<typeof mount>) {
  const input = wrapper.find<HTMLInputElement>(
    '[data-test="exam-converter-source-file-input"]',
  );
  Object.defineProperty(input.element, "files", {
    configurable: true,
    value: [
      new File(["exam"], "Ma1c_NationelltProv_HT25.dxe", {
        type: "application/octet-stream",
      }),
    ],
  });
  await input.trigger("change");
}

function startButton(wrapper: ReturnType<typeof mount>) {
  return wrapper.find('[data-test="exam-converter-start-conversion"]');
}

beforeEach(() => {
  gatewayMocks.applyExamAuthoringCorrections.mockReset();
  gatewayMocks.downloadDigiExamMigrationArtifact.mockReset();
  gatewayMocks.downloadDigiExamMigrationCorrectionReplayArtifact.mockReset();
  gatewayMocks.getDigiExamMigrationJob.mockReset();
  gatewayMocks.getDigiExamMigrationResult.mockReset();
  gatewayMocks.issueExamAuthoringCorrectionSourceState.mockReset();
  gatewayMocks.listDigiExamMigrationArtifacts.mockReset();
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReturnValue(new Promise(() => undefined));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ExamConverterAuthenticatedView conversion-start slice", () => {
  it("enables start only after one exam file is selected", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    expect(startButton(wrapper).attributes("disabled")).toBeDefined();

    await chooseSourceFile(wrapper);
    expect(startButton(wrapper).attributes("disabled")).toBeUndefined();
  });

  it("starts the local running state with dynamic progress but no question, file, or report modes", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(wrapper);
    await startButton(wrapper).trigger("click");

    expect(wrapper.find('[data-test="exam-converter-result-strip"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-converter-running-surface"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("Konverterar provet...");
    expect(wrapper.text()).toContain("Vänta medan provet konverteras.");
    expect(wrapper.find('[data-test="exam-converter-conversion-progress"]').exists()).toBe(
      true,
    );
    expect(wrapper.html()).not.toContain("animate-spin");
    expect(wrapper.text()).not.toContain("Konverterade frågor");
    expect(wrapper.text()).not.toContain("Filer klara att hämta");
    expect(wrapper.text()).not.toContain("Rapport");
    expect(wrapper.text()).not.toContain("Spara i mina filer");
  });

  it("moves the local progress visualization while waiting for upstream progress events", async () => {
    vi.useFakeTimers();
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(wrapper);
    await startButton(wrapper).trigger("click");
    const initialWidth = wrapper
      .find('[data-test="exam-converter-progress-bar"]')
      .attributes("style");

    await vi.advanceTimersByTimeAsync(3_000);
    await wrapper.vm.$nextTick();

    expect(
      wrapper.find('[data-test="exam-converter-progress-stage"]').text(),
    ).toContain("Läser provfilen");
    expect(
      wrapper.find('[data-test="exam-converter-progress-bar"]').attributes("style"),
    ).not.toBe(initialWidth);
    wrapper.unmount();
  });

  it("shows a long-running wait message after ten seconds without inventing an ETA", async () => {
    vi.useFakeTimers();
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(wrapper);
    await startButton(wrapper).trigger("click");
    await vi.advanceTimersByTimeAsync(10_000);
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-test="exam-converter-long-running-copy"]').text()).toBe(
      "Det här tar längre tid än vanligt. Sidan uppdateras när nästa steg är klart.",
    );
    expect(wrapper.text()).not.toContain("ETA");
    expect(wrapper.text()).not.toContain("Sir Convert");
    wrapper.unmount();
  });

  it("clears the running state when local choices are reset", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(wrapper);
    await startButton(wrapper).trigger("click");
    await wrapper.find("button.btn-ghost").trigger("click");

    expect(wrapper.find('[data-test="exam-converter-result-strip"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-converter-source-drop-zone"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("Välj provfil för att börja");
  });
});

describe("ExamConverterResultStrip", () => {
  const resultStates: ExamConverterResultStripState[] = [
    {
      actionLabel: null,
      detail: null,
      nextAction: "Filerna kan sparas eller hämtas.",
      progress: null,
      status: "success",
      title: "Provet är konverterat",
      tone: "success",
    },
    {
      actionLabel: null,
      detail: "8 frågor saknar facit eller poäng.",
      nextAction: "Kontrollera frågorna med saknat facit eller poäng.",
      progress: null,
      status: "partial",
      title: "Konverteringen av provet lyckades delvis",
      tone: "warning",
    },
    {
      actionLabel: null,
      detail: null,
      nextAction: "Kontrollera provfilen och försök igen.",
      progress: null,
      status: "failed",
      title: "Konverteringen av provet misslyckades",
      tone: "error",
    },
  ];

  it("renders the approved teacher-facing result states without service jargon", () => {
    for (const result of resultStates) {
      const wrapper = mount(ExamConverterResultStrip, {
        props: { result },
      });

      expect(wrapper.text()).toContain(result.title);
      expect(wrapper.text()).not.toContain("artefakt");
      expect(wrapper.text()).not.toContain("manifest");
      expect(wrapper.text()).not.toContain("runtime");
      expect(wrapper.text()).not.toContain("pipeline");
    }
  });

  it("keeps result-strip navigation out of the dedicated review decision gate", () => {
    const wrapper = mount(ExamConverterResultStrip, {
      props: { result: resultStates[1] },
    });

    expect(wrapper.find('[data-test="exam-converter-result-open-questions"]').exists()).toBe(
      false,
    );
    expect(wrapper.emitted("openQuestions")).toBeUndefined();
  });
});
