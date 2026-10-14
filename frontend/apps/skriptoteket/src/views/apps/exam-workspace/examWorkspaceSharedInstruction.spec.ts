/**
 * Shared instruction rendering.
 *
 * Expected behavior:
 *   A shared instruction's native paragraphs map to ordered text and picture
 *   parts; a known asset id resolves to its protected URL and an unknown one
 *   carries no URL, so the reader either shows the real diagram or the "Bild"
 *   placeholder. The read-only renderer keeps text as text (never markup),
 *   shows the picture from the protected URL, and never turns a forbidden
 *   response gap into a question atom.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import ExamWorkspaceSharedInstruction from "./ExamWorkspaceSharedInstruction.vue";
import {
  SHARED_INSTRUCTION_GAP_TEXT,
  examWorkspaceSharedParagraphs,
  examWorkspaceSharedParts,
} from "./examWorkspaceSharedInstruction";

const ASSET_ID = "asset_0123456789abcdef";
const PROTECTED_URL =
  "/api/v1/apps/documents.conversion_hub/exam-workspace/documents/lineage-1/assets/asset_0123456789abcdef?revision=3";

function pictureParagraph(): NativeExamBodyParagraph {
  return {
    segments: [
      { kind: "text", text: "Betrakta diagrammet." },
      { asset_id: ASSET_ID, kind: "asset" },
      { kind: "text", text: "Svara sedan." },
    ],
  };
}

function mountShared(
  paragraphs: NativeExamBodyParagraph[],
  assetUrls: Record<string, string> = {},
) {
  return mount(ExamWorkspaceSharedInstruction, {
    props: { paragraphs: examWorkspaceSharedParagraphs(paragraphs, assetUrls) },
  });
}

describe("examWorkspaceSharedParts", () => {
  it("keeps text and pictures in order and resolves a known protected URL", () => {
    expect(examWorkspaceSharedParts(pictureParagraph(), { [ASSET_ID]: PROTECTED_URL })).toEqual([
      { kind: "text", text: "Betrakta diagrammet." },
      { assetId: ASSET_ID, kind: "asset", url: PROTECTED_URL },
      { kind: "text", text: "Svara sedan." },
    ]);
  });

  it("carries no URL for a picture the asset map does not know", () => {
    expect(examWorkspaceSharedParts(pictureParagraph())).toEqual([
      { kind: "text", text: "Betrakta diagrammet." },
      { assetId: ASSET_ID, kind: "asset", url: null },
      { kind: "text", text: "Svara sedan." },
    ]);
  });

  it("keeps an impossible response gap visible as text instead of an answer atom", () => {
    const paragraph: NativeExamBodyParagraph = {
      segments: [
        { kind: "text", text: "Före" },
        { gap_id: "gap_001", kind: "gap" },
        { kind: "text", text: "efter" },
      ],
    };

    expect(examWorkspaceSharedParts(paragraph)).toEqual([
      { kind: "text", text: "Före" },
      { kind: "text", text: SHARED_INSTRUCTION_GAP_TEXT },
      { kind: "text", text: "efter" },
    ]);
  });
});

describe("ExamWorkspaceSharedInstruction", () => {
  it("renders text, the real picture from its protected URL, then text", () => {
    const wrapper = mountShared([pictureParagraph()], { [ASSET_ID]: PROTECTED_URL });

    const paragraph = wrapper.get('[data-test="exam-workspace-shared-instruction-paragraph"]');
    const rendered = Array.from(paragraph.element.children).map((element) =>
      element.tagName === "IMG" ? element.getAttribute("src") : element.textContent,
    );
    expect(rendered).toEqual(["Betrakta diagrammet.", PROTECTED_URL, "Svara sedan."]);

    const image = wrapper.get('[data-test="exam-workspace-shared-instruction-image"]');
    expect(image.attributes("data-asset-id")).toBe(ASSET_ID);
    expect(image.attributes("src")).toBe(PROTECTED_URL);
  });

  it("renders the Bild placeholder while the picture URL is unknown", () => {
    const wrapper = mountShared([pictureParagraph()]);

    expect(
      wrapper.get('[data-test="exam-workspace-shared-instruction-placeholder"]').text(),
    ).toBe("Bild");
    expect(wrapper.find('[data-test="exam-workspace-shared-instruction-image"]').exists()).toBe(
      false,
    );
  });

  it("renders instruction text as text and never as markup", () => {
    const injected = '<img src="x" onerror="alert(1)">';
    const wrapper = mountShared([{ segments: [{ kind: "text", text: injected }] }]);

    expect(
      wrapper.get('[data-test="exam-workspace-shared-instruction-paragraph"]').text(),
    ).toBe(injected);
    expect(wrapper.find("img").exists()).toBe(false);
  });
});
