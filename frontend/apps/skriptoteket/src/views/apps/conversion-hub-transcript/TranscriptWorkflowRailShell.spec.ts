/**
 * Transcript workflow rail shell specs.
 *
 * Domain purpose:
 *   Prove the transcript setup rail keeps cancellation as a stable, direct
 *   running-work action without layout jumps or misleading icon affordances.
 *
 * Relationships:
 *   - Exercises `TranscriptWorkflowRailShell.vue` as the DOM boundary.
 *   - Complements runtime cancellation tests in `useTranscriptGatewayRuntime`.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import TranscriptWorkflowRailShell from "./TranscriptWorkflowRailShell.vue";
import type {
  TranscriptSourceFileSelection,
  TranscriptSpeakerMode,
} from "./useTranscriptSourceFile";
import type { TranscriptAbortState } from "./useTranscriptGatewayRuntime";

function mountRail(
  overrides: Partial<{
    abortState: TranscriptAbortState;
    canStartTranscript: boolean;
    isRunning: boolean;
    selectedTranscriptFile: TranscriptSourceFileSelection | null;
    speakerMode: TranscriptSpeakerMode;
  }> = {},
) {
  return mount(TranscriptWorkflowRailShell, {
    props: {
      abortState: overrides.abortState ?? { message: null, status: "idle" },
      canStartTranscript: overrides.canStartTranscript ?? true,
      isRunning: overrides.isRunning ?? false,
      maxSpeakers: 4,
      minSpeakers: 1,
      selectedTranscriptFile: overrides.selectedTranscriptFile ?? null,
      speakerCount: 2,
      speakerError: null,
      speakerMode: overrides.speakerMode ?? "auto",
      transcriptFileError: null,
    },
  });
}

function buttonIndex(wrapper: ReturnType<typeof mountRail>, selector: string): number {
  const target = wrapper.get(selector).element;
  return Array.from(wrapper.element.querySelectorAll("button")).indexOf(target as HTMLButtonElement);
}

describe("TranscriptWorkflowRailShell", () => {
  it("renders the start command as a neutral compact control instead of a filled CTA", () => {
    const wrapper = mountRail();

    const start = wrapper.get("[data-test='transcript-start']");

    expect(start.classes()).not.toContain("btn-cta");
    expect(start.classes()).not.toContain("bg-navy");
    expect(start.classes()).not.toContain("text-canvas");
    expect(start.classes()).toContain("bg-panel");
    expect(start.classes()).toContain("text-navy");
  });

  it("reserves an invisible cancel slot above start before transcription runs", () => {
    const wrapper = mountRail();

    const cancel = wrapper.get("[data-test='transcript-cancel']");

    expect(buttonIndex(wrapper, "[data-test='transcript-cancel']")).toBeLessThan(
      buttonIndex(wrapper, "[data-test='transcript-start']"),
    );
    expect(cancel.text()).toBe("Avbryt");
    expect(cancel.classes()).toContain("invisible");
    expect(cancel.classes()).toContain("pointer-events-none");
    expect(cancel.attributes("aria-hidden")).toBe("true");
    expect(cancel.attributes("disabled")).toBe("");
    expect(cancel.attributes("tabindex")).toBe("-1");
    expect(cancel.find("svg").exists()).toBe(false);
    expect(wrapper.find("input[type='checkbox']").exists()).toBe(false);
  });

  it("shows the same cancel slot without shifting start while transcription runs", async () => {
    const wrapper = mountRail({ isRunning: true });

    const cancel = wrapper.get("[data-test='transcript-cancel']");

    expect(buttonIndex(wrapper, "[data-test='transcript-cancel']")).toBeLessThan(
      buttonIndex(wrapper, "[data-test='transcript-start']"),
    );
    expect(cancel.classes()).not.toContain("invisible");
    expect(cancel.attributes("aria-hidden")).toBeUndefined();
    expect(cancel.attributes("disabled")).toBeUndefined();
    expect(cancel.attributes("tabindex")).toBe("0");
    expect(cancel.find("svg").exists()).toBe(false);

    await cancel.trigger("click");

    expect(wrapper.emitted("cancelTranscript")).toHaveLength(1);
  });

  it("keeps the cancel slot visible but inert while cancellation is pending", () => {
    const wrapper = mountRail({
      abortState: { message: "Avbryter transkriberingen.", status: "pending" },
      isRunning: true,
    });

    const cancel = wrapper.get("[data-test='transcript-cancel']");

    expect(cancel.text()).toBe("Avbryter");
    expect(cancel.classes()).not.toContain("invisible");
    expect(cancel.attributes("disabled")).toBe("");
    expect(cancel.find("svg").exists()).toBe(false);
  });
});
