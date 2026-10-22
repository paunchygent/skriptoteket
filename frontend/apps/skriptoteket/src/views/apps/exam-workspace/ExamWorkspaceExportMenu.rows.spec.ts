/**
 * Exam workspace export menu split rows.
 *
 * Expected behavior (TASK-SKRIPT-40-04-16 V3, terms L1-L4, L6-L9, Q1-Q4, B1):
 *   Each format row is a labelled group with one outlined split button at its
 *   right edge: download first, save to Mina filer second (guests see the
 *   download part alone). The name and suffix sit on one line; a name click
 *   downloads. The running part spins with aria-busy while every part is
 *   aria-disabled (never natively disabled); nothing sits on any row's left.
 *
 * The menu teleports to document.body, so rows and parts are found through
 * `document` rather than the wrapper, as in a browser.
 */

import { createTestingPinia } from "@pinia/testing";
import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import type { ExamWorkspaceExportTarget } from "../../../api/examWorkspaceExports";
import { adminUser } from "../ExamWorkspaceSlice.specSupport";
import ExamWorkspaceExportMenu from "./ExamWorkspaceExportMenu.vue";
import ExamWorkspaceMenu from "./ExamWorkspaceMenu.vue";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";
import { EXAM_WORKSPACE_EXPORT_FORMATS, QTI_ZERO_POINTS_NOTE } from "./examWorkspaceExportFormats";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { serverExamWorkspaceStore, type ExamWorkspaceStore } from "./examWorkspaceStore";
import type { ExportDestination } from "./useExamWorkspaceExports";

const GUEST_STORE: ExamWorkspaceStore = { ...serverExamWorkspaceStore, teacher: null };

const ORDERING_BLOCKER: ExamWorkspaceBlockerEntry = {
  fix: null,
  focus: '[data-test="exam-workspace-ordering-add-step"]',
  itemId: "item_001",
  label: "1",
  problem: "för få steg",
  reason: "ordering_too_few_steps",
};

type MenuOptions = {
  blockers?: ExamWorkspaceBlockerEntry[];
  checklistCount?: number;
  exportingDestination?: ExportDestination | null;
  exportingTarget?: ExamWorkspaceExportTarget | null;
  guest?: boolean;
  savedExports?: Partial<Record<ExamWorkspaceExportTarget, string>>;
  zeroPoints?: boolean;
};

function mountMenu(options: MenuOptions = {}): VueWrapper {
  return mount(ExamWorkspaceExportMenu, {
    attachTo: document.body,
    global: {
      plugins: [
        createTestingPinia({
          createSpy: vi.fn,
          initialState: { auth: { user: adminUser } },
        }),
        examWorkspaceProvidersPlugin({
          store: options.guest === true ? GUEST_STORE : serverExamWorkspaceStore,
        }),
      ],
    },
    props: {
      blockers: options.blockers ?? [],
      checklistCount: options.checklistCount ?? 0,
      disabled: false,
      exportingDestination: options.exportingDestination ?? null,
      exportingTarget: options.exportingTarget ?? null,
      fixDisabled: false,
      isPhone: false,
      result: null,
      savedExports: options.savedExports ?? {},
      suggestBusy: false,
      zeroPoints: options.zeroPoints ?? false,
    },
  });
}

async function openMenu(wrapper: VueWrapper): Promise<void> {
  await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
}

function row(target: ExamWorkspaceExportTarget): HTMLElement {
  const candidate = document.body.querySelector(`[data-test="exam-workspace-export-row-${target}"]`);
  if (!(candidate instanceof HTMLElement)) {
    throw new Error(`export row ${target} did not mount`);
  }
  return candidate;
}

function downloadPart(target: ExamWorkspaceExportTarget): HTMLButtonElement {
  const candidate = document.body.querySelector(`[data-test="exam-workspace-export-${target}"]`);
  if (!(candidate instanceof HTMLButtonElement)) {
    throw new Error(`download part ${target} did not mount`);
  }
  return candidate;
}

function savePart(target: ExamWorkspaceExportTarget): HTMLButtonElement {
  const candidate = document.body.querySelector(`[data-test="exam-workspace-export-save-${target}"]`);
  if (!(candidate instanceof HTMLButtonElement)) {
    throw new Error(`save part ${target} did not mount`);
  }
  return candidate;
}

function nameLine(target: ExamWorkspaceExportTarget): HTMLElement {
  const line = row(target).querySelector(":scope > .xw-mi__stack > .xw-grow");
  if (!(line instanceof HTMLElement)) {
    throw new Error(`name line ${target} did not mount`);
  }
  return line;
}

function menuSurface(): HTMLElement | null {
  return document.body.querySelector('[data-test="exam-workspace-export-menu"]');
}

afterEach(() => document.body.replaceChildren());

describe("ExamWorkspaceExportMenu split rows", () => {
  it("emits download from the download part of every format", async () => {
    const wrapper = mountMenu();
    await openMenu(wrapper);

    for (const { target } of EXAM_WORKSPACE_EXPORT_FORMATS) {
      downloadPart(target).click();
    }

    expect(wrapper.emitted("download")).toEqual(
      EXAM_WORKSPACE_EXPORT_FORMATS.map(({ target }) => [target]),
    );
    wrapper.unmount();
  });

  it("emits saveToFiles from the save part of every format", async () => {
    const wrapper = mountMenu();
    await openMenu(wrapper);

    for (const { target } of EXAM_WORKSPACE_EXPORT_FORMATS) {
      savePart(target).click();
    }

    expect(wrapper.emitted("saveToFiles")).toEqual(
      EXAM_WORKSPACE_EXPORT_FORMATS.map(({ target }) => [target]),
    );
    wrapper.unmount();
  });

  it("downloads on a name-line click for every format", async () => {
    const wrapper = mountMenu();
    await openMenu(wrapper);

    for (const { target } of EXAM_WORKSPACE_EXPORT_FORMATS) {
      nameLine(target).click();
    }

    expect(wrapper.emitted("download")).toEqual(
      EXAM_WORKSPACE_EXPORT_FORMATS.map(({ target }) => [target]),
    );
    wrapper.unmount();
  });

  it("labels each row by its visible name and suffix", async () => {
    const wrapper = mountMenu();
    await openMenu(wrapper);

    for (const { name, target, use } of EXAM_WORKSPACE_EXPORT_FORMATS) {
      const label = use === null ? name : `${name} ${use}`;
      expect(row(target).getAttribute("role")).toBe("group");
      expect(row(target).getAttribute("aria-label")).toBe(label);
      expect(row(target).getAttribute("title")).toBe(label);
    }
    wrapper.unmount();
  });

  it("renders no suffix for PDF med facit and keeps the others", async () => {
    const wrapper = mountMenu();
    await openMenu(wrapper);

    for (const { target, use } of EXAM_WORKSPACE_EXPORT_FORMATS) {
      const suffix = row(target).querySelector(".xw-mi__sub");
      if (use === null) {
        expect(suffix).toBeNull();
      } else {
        expect(suffix?.textContent).toBe(use);
      }
    }
    wrapper.unmount();
  });

  it("keeps the name line first, on one line, with nothing on its left", async () => {
    const wrapper = mountMenu();
    await openMenu(wrapper);

    for (const { target } of EXAM_WORKSPACE_EXPORT_FORMATS) {
      const first = row(target).firstElementChild;
      expect(first?.classList.contains("xw-mi__stack")).toBe(true);
      expect(nameLine(target).classList.contains("truncate")).toBe(true);
    }
    wrapper.unmount();
  });

  it("names each part's action and format in its label and tooltip", async () => {
    const wrapper = mountMenu({ savedExports: { qti: "2026-10-18" } });
    await openMenu(wrapper);

    for (const { name, target } of EXAM_WORKSPACE_EXPORT_FORMATS) {
      expect(downloadPart(target).getAttribute("aria-label")).toBe(`Ladda ner ${name}`);
      expect(downloadPart(target).getAttribute("title")).toBe(`Ladda ner ${name}`);
      expect(savePart(target).getAttribute("aria-label")).toBe(`Spara ${name} i Mina filer`);
    }
    expect(savePart("qti").getAttribute("title")).toBe(
      "Spara QTI i Mina filer (ersätter filen från 2026-10-18)",
    );
    expect(savePart("pdf").getAttribute("title")).toBe("Spara PDF i Mina filer");
    wrapper.unmount();
  });

  it("keeps the saved-date line and the zero-points note under the name", async () => {
    const wrapper = mountMenu({ savedExports: { pdf: "2026-10-18" }, zeroPoints: true });
    await openMenu(wrapper);

    expect(row("pdf").textContent).toContain("I Mina filer 2026-10-18");
    expect(row("qti").textContent).toContain(QTI_ZERO_POINTS_NOTE);
    wrapper.unmount();
  });

  it("shows a guest the download part alone with its full radius", async () => {
    const wrapper = mountMenu({ guest: true });
    await openMenu(wrapper);

    for (const { target } of EXAM_WORKSPACE_EXPORT_FORMATS) {
      expect(
        document.body.querySelector(`[data-test="exam-workspace-export-save-${target}"]`),
      ).toBeNull();
      expect(downloadPart(target).closest(".xw-split")).toBeNull();
    }
    wrapper.unmount();
  });

  it("spins only the running save part while every part stays focusable and silent", async () => {
    const wrapper = mountMenu({ exportingDestination: "files", exportingTarget: "qti" });
    await openMenu(wrapper);

    for (const { target } of EXAM_WORKSPACE_EXPORT_FORMATS) {
      const download = downloadPart(target);
      const save = savePart(target);
      expect(download.getAttribute("aria-disabled")).toBe("true");
      expect(save.getAttribute("aria-disabled")).toBe("true");
      expect(download.hasAttribute("disabled")).toBe(false);
      expect(save.hasAttribute("disabled")).toBe(false);
      expect(download.getAttribute("aria-busy") ?? null).toBeNull();
      expect(download.querySelector(".xw-spin")).toBeNull();
      if (target === "qti") {
        expect(save.getAttribute("aria-busy")).toBe("true");
        expect(save.querySelector(".xw-spin")).not.toBeNull();
      } else {
        expect(save.getAttribute("aria-busy") ?? null).toBeNull();
        expect(save.querySelector(".xw-spin")).toBeNull();
      }
    }

    downloadPart("qti").click();
    savePart("qti").click();
    downloadPart("pdf").click();
    nameLine("pdf").click();

    expect(wrapper.emitted("download")).toBeUndefined();
    expect(wrapper.emitted("saveToFiles")).toBeUndefined();
    wrapper.unmount();
  });

  it("disables every part while a blocker is listed and emits nothing", async () => {
    const wrapper = mountMenu({ blockers: [ORDERING_BLOCKER] });
    await openMenu(wrapper);

    for (const { target } of EXAM_WORKSPACE_EXPORT_FORMATS) {
      expect(downloadPart(target).getAttribute("aria-disabled")).toBe("true");
      expect(savePart(target).getAttribute("aria-disabled")).toBe("true");
      expect(downloadPart(target).hasAttribute("disabled")).toBe(false);
      expect(savePart(target).hasAttribute("disabled")).toBe(false);
    }

    downloadPart("qti").click();
    savePart("qti").click();
    nameLine("qti").click();

    expect(wrapper.emitted("download")).toBeUndefined();
    expect(wrapper.emitted("saveToFiles")).toBeUndefined();
    wrapper.unmount();
  });

  it("moves Right from a download part to its save part", async () => {
    const wrapper = mountMenu();
    await openMenu(wrapper);

    downloadPart("qti").focus();
    downloadPart("qti").dispatchEvent(
      new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key: "ArrowRight" }),
    );

    expect(document.activeElement).toBe(savePart("qti"));
    wrapper.unmount();
  });

  it("shows no running line anywhere", async () => {
    const wrapper = mountMenu({ exportingDestination: "download", exportingTarget: "pdf" });
    await openMenu(wrapper);

    expect(document.body.textContent).not.toContain("Exporterar");
    expect(
      document.body.querySelector('[data-test="exam-workspace-export-running"]'),
    ).toBeNull();
    wrapper.unmount();
  });

  it("starts the checklist row and Fler val with their text", async () => {
    const wrapper = mountMenu({ checklistCount: 2 });
    await openMenu(wrapper);

    for (const testId of ["exam-workspace-export-checklist-open", "exam-workspace-export-more"]) {
      const candidate = document.body.querySelector(`[data-test="${testId}"]`);
      if (!(candidate instanceof HTMLElement)) {
        throw new Error(`row ${testId} did not mount`);
      }
      expect(candidate.querySelector("svg")).toBeNull();
      expect(candidate.firstElementChild?.classList.contains("xw-grow")).toBe(true);
    }
    expect(document.body.textContent).toContain("Det här tappar Exam.net (2)");
    wrapper.unmount();
  });

  it("dismisses the menu on close and stays closed on a second close", async () => {
    const wrapper = mountMenu();
    await openMenu(wrapper);
    expect(menuSurface()).not.toBeNull();

    wrapper.findComponent(ExamWorkspaceMenu).vm.$emit("close", false);
    await nextTick();
    expect(menuSurface()).toBeNull();

    wrapper.findComponent(ExamWorkspaceMenu).vm.$emit("close", false);
    await nextTick();
    expect(menuSurface()).toBeNull();
    wrapper.unmount();
  });
});
