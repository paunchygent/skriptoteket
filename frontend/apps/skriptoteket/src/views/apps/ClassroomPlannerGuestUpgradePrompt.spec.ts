/**
 * Klassrumskartan authenticated guest-upgrade prompt tests.
 *
 * These tests lock the first-visit modal copy so the prompt stays focused on
 * the teacher's decision instead of regressing into a storage-ledger surface.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ClassroomPlannerGuestUpgradePrompt from "./ClassroomPlannerGuestUpgradePrompt.vue";

describe("ClassroomPlannerGuestUpgradePrompt", () => {
  it("renders a modal with a compact human summary and natural actions", async () => {
    const wrapper = mount(ClassroomPlannerGuestUpgradePrompt, {
      props: {
        summary: {
          snapshot_id: "guest-snapshot-1",
          profile: "public_browser_workspace_with_upgrade",
          created_at: "2026-04-04T08:00:00.000Z",
          updated_at: "2026-04-04T08:00:00.000Z",
          expires_at: "2026-04-18T08:00:00.000Z",
          roster_count: 1,
          template_count: 1,
          smart_rule_set_count: 0,
          checkpoint_count: 0,
          has_grouping_draft: true,
          has_seating_draft: false,
        },
        previewReceipt: null,
        errorMessage: null,
      },
    });

    expect(wrapper.find("[data-test='guest-upgrade-modal']").exists()).toBe(true);
    expect(wrapper.text()).toContain("Arbete från gästläge hittat");
    expect(wrapper.text()).toContain("Vill du importera det?");
    expect(wrapper.get("[data-test='guest-upgrade-summary-line']").text()).toContain(
      "1 klass, 1 klassrum och 1 utkast finns att föra över till ditt konto.",
    );
    expect(wrapper.text()).not.toContain("Snapshot-id");
    expect(wrapper.text()).not.toContain("Regler / checkpoints");
    expect(wrapper.text()).not.toContain("Rensa lokal gästarbetsyta");
    expect(wrapper.get("[data-test='guest-upgrade-import-button']").text()).toBe("Importera");
    expect(wrapper.get("[data-test='guest-upgrade-postpone-button']").text()).toBe("Inte nu");
    expect(wrapper.get("[data-test='guest-upgrade-discard-button']").text()).toBe("Kasta");

    await wrapper.get("[data-test='guest-upgrade-import-button']").trigger("click");
    await wrapper.get("[data-test='guest-upgrade-postpone-button']").trigger("click");
    await wrapper.get("[data-test='guest-upgrade-discard-button']").trigger("click");

    expect(wrapper.emitted("import")).toHaveLength(1);
    expect(wrapper.emitted("postpone")).toHaveLength(1);
    expect(wrapper.emitted("discard")).toHaveLength(1);
  });

  it("shows the simplified conflict copy when some work could not be saved", () => {
    const wrapper = mount(ClassroomPlannerGuestUpgradePrompt, {
      props: {
        summary: {
          snapshot_id: "guest-snapshot-1",
          profile: "public_browser_workspace_with_upgrade",
          created_at: "2026-04-04T08:00:00.000Z",
          updated_at: "2026-04-04T08:00:00.000Z",
          expires_at: "2026-04-18T08:00:00.000Z",
          roster_count: 1,
          template_count: 0,
          smart_rule_set_count: 0,
          checkpoint_count: 0,
          has_grouping_draft: false,
          has_seating_draft: false,
        },
        previewReceipt: null,
        errorMessage: "Allt gick inte att spara. Det som blev kvar finns fortfarande i den här webbläsaren.",
      },
    });

    expect(wrapper.get("[data-test='guest-upgrade-error-message']").text()).toBe(
      "Allt gick inte att spara. Det som blev kvar finns fortfarande i den här webbläsaren.",
    );
  });
});
