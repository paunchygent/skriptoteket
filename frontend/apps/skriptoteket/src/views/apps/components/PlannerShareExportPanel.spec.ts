/**
 * Planner share/export panel tests.
 *
 * These tests lock the PR-0286 surface: one `Dela` affordance opens a grouped
 * distribution panel while share and export intents remain separate emits.
 */

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";
import PlannerShareExportPanel from "./PlannerShareExportPanel.vue";
import type { PlannerExportFileOption } from "./plannerShareExportActions";

function visibleAtWidth(element: Element, width: number): boolean {
  const classList = Array.from(element.classList);
  if (width < 768 && classList.includes("hidden") && !classList.includes("md:block")) {
    return false;
  }
  if (width < 768 && classList.includes("md:hidden")) {
    return true;
  }
  if (width < 768 && classList.includes("hidden") && classList.includes("md:block")) {
    return false;
  }
  return true;
}

function isVisibleAtWidth(element: Element, width: number): boolean {
  let current: Element | null = element;
  while (current) {
    if (!visibleAtWidth(current, width)) {
      return false;
    }
    current = current.parentElement;
  }
  return true;
}

function makeShare(params: {
  id: string;
  publicUrl: string | null;
  revokedAt?: string | null;
}): ClassroomPlannerShareArtifact {
  return {
    id: params.id,
    source: "authenticated",
    draft_kind: "grouping",
    draft_id: "draft-1",
    roster_id: "roster-1",
    template_id: null,
    source_revision: 8,
    title: "Klass 7A",
    slug: "klass-7a",
    public_path: params.publicUrl ? "/share/classroom/public-token/klass-7a" : null,
    public_url: params.publicUrl,
    preview_description: null,
    renderer_version: "klassrumskartan-share-renderer-v1",
    presentation_schema_version: "grouping-share-v1",
    presentation_hash: "sha256:presentation",
    content_hash: "sha256:content",
    created_at: "2026-04-30T10:00:00Z",
    updated_at: "2026-04-30T10:00:00Z",
    revoked_at: params.revokedAt ?? null,
    expires_at: null,
  };
}

function groupingFileOptions(): PlannerExportFileOption[] {
  return [
    {
      id: "xlsx",
      label: "Excel (.xlsx)",
      option: "xlsx",
      isDefault: true,
    },
    {
      id: "pdf",
      label: "PDF (A4 stående)",
      option: "pdf_a4_portrait",
    },
  ];
}

describe("PlannerShareExportPanel", () => {
  afterEach(() => {
    document.body.style.overflow = "";
    document.body.innerHTML = "";
  });

  it("opens one Dela panel with link management and file export actions", async () => {
    const share = makeShare({
      id: "share-1",
      publicUrl: "https://skriptoteket.hule.education/share/classroom/public-token/klass-7a",
    });
    const wrapper = mount(PlannerShareExportPanel, {
      props: {
        fileOptions: groupingFileOptions(),
        shares: [share],
        triggerTestId: "grouping-share-trigger",
        panelTestId: "grouping-share-management",
        createShareTestId: "grouping-share-create",
        fileOptionTestIdPrefix: "grouping-export-option",
      },
    });

    expect(wrapper.find('[data-test="grouping-share-management"]').exists()).toBe(false);

    await wrapper.get('[data-test="grouping-share-trigger"]').trigger("click");

    expect(wrapper.get('[data-test="grouping-share-management"]').text()).toContain("Dela och exportera");
    expect(wrapper.get('[data-test="grouping-share-management"]').text()).toContain("Länk");
    expect(wrapper.get('[data-test="grouping-share-management"]').text()).toContain("Filer");
    expect(wrapper.get('[data-test="grouping-share-management"]').attributes("aria-modal")).toBe("true");
    expect(wrapper.get('[data-test="planner-share-export-scroll"]').classes()).toContain("overscroll-contain");
    expect(wrapper.find('[data-test="planner-share-export-backdrop"]').exists()).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
    expect(wrapper.get('[data-test="grouping-export-option-xlsx"]').text()).toContain("Standard");
    expect(wrapper.get('[data-test="grouping-export-option-pdf"]').text()).toContain("PDF (A4 stående)");

    await wrapper.get('[data-test="grouping-share-create"]').trigger("click");
    await wrapper.get('[data-test="planner-share-copy-share-1"]').trigger("click");
    await wrapper.get('[data-test="planner-share-revoke-share-1"]').trigger("click");
    await wrapper.get('[data-test="grouping-export-option-xlsx"]').trigger("click");
    await wrapper.get('[data-test="grouping-export-option-pdf"]').trigger("click");

    expect(wrapper.emitted("create-share")).toEqual([[]]);
    expect(wrapper.emitted("copy-share")).toEqual([[share]]);
    expect(wrapper.emitted("revoke-share")).toEqual([[share]]);
    expect(wrapper.emitted("export-default")).toEqual([[]]);
    expect(wrapper.emitted("export-option")).toEqual([["pdf_a4_portrait"]]);

    await wrapper.get('[data-test="planner-share-export-close"]').trigger("click");
    expect(document.body.style.overflow).toBe("");
  });

  it("keeps revoked links hidden and disables file actions while export is busy", async () => {
    const activeShare = makeShare({
      id: "share-2",
      publicUrl: "https://skriptoteket.hule.education/share/classroom/active/klass-7a",
    });
    const revokedShare = makeShare({
      id: "share-3",
      publicUrl: "https://skriptoteket.hule.education/share/classroom/revoked/klass-7a",
      revokedAt: "2026-04-30T11:00:00Z",
    });
    const wrapper = mount(PlannerShareExportPanel, {
      props: {
        fileOptions: groupingFileOptions(),
        shares: [activeShare, revokedShare],
        exportBusy: true,
        fileOptionTestIdPrefix: "grouping-export-option",
      },
    });

    await wrapper.get('[data-test="planner-share-export-trigger"]').trigger("click");

    expect(wrapper.find('[data-test="planner-share-link-share-2"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="planner-share-link-share-3"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="planner-export-status"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="grouping-export-option-xlsx"]').attributes("disabled"))
      .toBeDefined();
    expect(wrapper.get('[data-test="grouping-export-option-xlsx"]').find('[data-ui="dense-spinner"]').exists())
      .toBe(true);

    await wrapper.get('[data-test="grouping-export-option-xlsx"]').trigger("click");
    expect(wrapper.emitted("export-default")).toBeUndefined();
  });

  it("shows exactly one create-link action in the mobile sheet", async () => {
    const wrapper = mount(PlannerShareExportPanel, {
      props: {
        fileOptions: groupingFileOptions(),
        createShareTestId: "grouping-share-create",
        createShareMobileTestId: "grouping-share-create-mobile",
      },
    });

    await wrapper.get('[data-test="planner-share-export-trigger"]').trigger("click");

    const createActions = wrapper.findAll("button").filter((button) => button.text().includes("Skapa länk"));
    const visibleMobileActions = createActions.filter((button) => isVisibleAtWidth(button.element, 390));

    expect(createActions).toHaveLength(2);
    expect(visibleMobileActions).toHaveLength(1);
    expect(visibleMobileActions[0]?.attributes("data-test")).toBe("grouping-share-create-mobile");
  });

  it("uses desktop overview row actions instead of toolbar button tokens", () => {
    const wrapper = mount(PlannerShareExportPanel, {
      props: {
        fileOptions: groupingFileOptions(),
        triggerVariant: "inline",
        visualVariant: "desktop-overview",
        createShareTestId: "desktop-overview-share-create",
        createShareMobileTestId: "desktop-overview-share-create-mobile",
      },
    });

    const createButton = wrapper.get('[data-test="desktop-overview-share-create"]');
    expect(createButton.classes()).toContain("planner-share-export-link-create-button");
    expect(createButton.attributes("data-ui")).toBeUndefined();
    expect(createButton.classes()).not.toContain("h-10");
    expect(wrapper.get('[data-test="planner-share-export-file-xlsx"]').html())
      .toContain("lucide-file-spreadsheet");
    expect(wrapper.get('[data-test="planner-share-export-file-pdf"]').html())
      .toContain("lucide-file-text");
  });
});
