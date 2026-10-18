/**
 * Exam workspace Förhandsgranska panel (TASK-SKRIPT-40-04-07, W5).
 *
 * Expected behavior:
 *   The panel shows one image per printed page, names each page, states what
 *   the panel is doing (rendering, updating, blocked, or empty), scrolls to
 *   the selected question's page, and closes on the close button.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import ExamWorkspacePrintPreviewPanel from "./ExamWorkspacePrintPreviewPanel.vue";

type PanelProps = {
  pages: string[];
  questionPages: Record<string, number>;
  loading: boolean;
  blocked: boolean;
  message: string | null;
  selectedItemId: string | null;
};

function mountPanel(props: Partial<PanelProps> = {}) {
  return mount(ExamWorkspacePrintPreviewPanel, {
    attachTo: document.body,
    props: {
      blocked: false,
      loading: false,
      message: null,
      pages: [],
      questionPages: {},
      selectedItemId: null,
      ...props,
    },
  });
}

afterEach(() => document.body.replaceChildren());

describe("ExamWorkspacePrintPreviewPanel", () => {
  it("shows one image per page, named Sida n", () => {
    const wrapper = mountPanel({ pages: ["data:1", "data:2", "data:3"] });

    const images = wrapper.findAll("img");
    expect(images).toHaveLength(3);
    expect(images.map((image) => image.attributes("alt"))).toEqual(["Sida 1", "Sida 2", "Sida 3"]);
    expect(wrapper.find('[data-test="exam-workspace-print-preview"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it("reports what the panel is doing while it renders and updates", async () => {
    const empty = mountPanel({ loading: true, pages: [] });
    expect(empty.get('[data-test="exam-workspace-print-preview-status"]').text())
      .toBe("Skapar förhandsgranskning …");
    empty.unmount();

    const updating = mountPanel({ loading: true, pages: ["data:1"] });
    expect(updating.get('[data-test="exam-workspace-print-preview-status"]').text())
      .toBe("Uppdaterar …");
    updating.unmount();
  });

  it("says what the blocked panel shows, with and without pages", async () => {
    const noPages = mountPanel({ blocked: true, pages: [], message: "Bilden saknas" });
    expect(noPages.get('[data-test="exam-workspace-print-preview-status"]').text())
      .toBe("Förhandsgranskningen visas när provet går att skriva ut.");
    expect(noPages.get('[data-test="exam-workspace-print-preview-message"]').text())
      .toBe("Bilden saknas");
    noPages.unmount();

    const lastPages = mountPanel({ blocked: true, pages: ["data:1"] });
    expect(lastPages.get('[data-test="exam-workspace-print-preview-status"]').text())
      .toBe("Förhandsgranskningen visar den senaste utskriften.");
    lastPages.unmount();
  });

  it("scrolls the selected question's page into view", async () => {
    const wrapper = mountPanel({
      pages: ["data:1", "data:2", "data:3"],
      questionPages: { item_2: 2 },
    });
    const target = wrapper.findAll("img")[2].element as HTMLElement;
    const scrollIntoView = vi.fn();
    target.scrollIntoView = scrollIntoView;

    await wrapper.setProps({ selectedItemId: "item_2" });
    await flushPromises();

    expect(scrollIntoView).toHaveBeenCalledWith({ block: "start" });
    wrapper.unmount();
  });

  it("closes on the close button", async () => {
    const wrapper = mountPanel();

    await wrapper.get('[data-test="exam-workspace-print-preview-close"]').trigger("click");

    expect(wrapper.emitted("close")).toHaveLength(1);
    wrapper.unmount();
  });
});
