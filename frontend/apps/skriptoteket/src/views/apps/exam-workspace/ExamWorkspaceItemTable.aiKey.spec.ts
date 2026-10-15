/**
 * Exam workspace item table AI key status.
 *
 * Expected behavior:
 *   A row whose key the AI wrote shows exactly one IconAi with its accessible
 *   status: "Tolkad av AI" for an interpreted key and "Förslag från AI" for an
 *   invented one. An invented key keeps the row's review warning beside the
 *   glyph; a row without an AI mark shows no glyph but keeps its slot, so the
 *   warning and check stay in place between rows.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { IconAi, IconCheck, IconWarning } from "../../../components/icons";
import ExamWorkspaceItemTable from "./ExamWorkspaceItemTable.vue";
import type { ExamWorkspaceItemRow } from "./examWorkspaceRows";

function buildRow(overrides: Partial<ExamWorkspaceItemRow> = {}): ExamWorkspaceItemRow {
  return {
    aiKeyLabel: null,
    itemId: "item_001",
    parentBlock: null,
    parentChild: null,
    pointsLabel: "2",
    promptExcerpt: "Beskriv fotosyntesen.",
    reviewReasons: [],
    reviewRequired: false,
    sequence: 1,
    statusLabel: "Granskad",
    title: "Fråga 1",
    typeLabel: "Fritext",
    ...overrides,
  };
}

function mountTable(
  rows: ExamWorkspaceItemRow[],
  readinessByItemId: Record<string, string[]> = {},
) {
  return mount(ExamWorkspaceItemTable, {
    props: {
      exportBlockersByItemId: {},
      readinessByItemId,
      rows,
      selectedItemId: null,
    },
  });
}

describe("ExamWorkspaceItemTable AI key status", () => {
  it("shows one glyph per AI-written key with its accessible status", () => {
    const wrapper = mountTable([
      buildRow({ aiKeyLabel: "Tolkad av AI", itemId: "item_001" }),
      buildRow({
        aiKeyLabel: "Förslag från AI",
        itemId: "item_002",
        sequence: 2,
        title: "Fråga 2",
      }),
      buildRow({ itemId: "item_003", sequence: 3, title: "Fråga 3" }),
    ]);

    const marks = wrapper.findAll('[data-test^="exam-workspace-item-ai-key-"]');
    expect(marks.map((mark) => mark.attributes("aria-label"))).toEqual([
      "Tolkad av AI",
      "Förslag från AI",
    ]);
    expect(marks.map((mark) => mark.attributes("title"))).toEqual([
      "Tolkad av AI",
      "Förslag från AI",
    ]);
    expect(marks.every((mark) => mark.attributes("role") === "img")).toBe(true);
    expect(marks.every((mark) => mark.text() === "")).toBe(true);
    expect(wrapper.findAllComponents(IconAi)).toHaveLength(2);
  });

  it("keeps the review warning beside an invented key", () => {
    const wrapper = mountTable(
      [
        buildRow({
          aiKeyLabel: "Förslag från AI",
          itemId: "item_002",
          reviewRequired: true,
          statusLabel: "Behöver granskas",
        }),
      ],
      { item_002: ["Facit är ett maskinellt förslag – kontrollera det innan du godkänner."] },
    );

    const row = wrapper.get('[data-test="exam-workspace-item-row-item_002"]');
    expect(row.findComponent(IconAi).exists()).toBe(true);
    expect(row.findComponent(IconWarning).exists()).toBe(true);
  });

  it("keeps the reserved slot and no glyph on a row without an AI mark", () => {
    const wrapper = mountTable([
      buildRow({ aiKeyLabel: "Tolkad av AI", itemId: "item_001" }),
      buildRow({ itemId: "item_002", sequence: 2, title: "Fråga 2" }),
    ]);

    expect(wrapper.find('[data-test="exam-workspace-item-ai-slot-item_001"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-item-ai-slot-item_002"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-item-ai-key-item_002"]').exists()).toBe(false);

    const secondRow = wrapper.get('[data-test="exam-workspace-item-row-item_002"]');
    expect(secondRow.findComponent(IconAi).exists()).toBe(false);
    expect(secondRow.findComponent(IconCheck).exists()).toBe(true);
  });
});
