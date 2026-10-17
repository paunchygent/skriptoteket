/** Planner-owned failure announcements and dismissal through the shared message. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerConfirmationDialog from "./PlannerConfirmationDialog.vue";

describe("PlannerConfirmationDialog", () => {
  it("announces escaped model text, clears once on dismissal, and shows a later failure", async () => {
    const failure = "Kunde inte spara <strong>klass</strong>";
    const wrapper = mount(PlannerConfirmationDialog, {
      props: {
        eyebrow: "Klass",
        title: "Ta bort klass?",
        message: "Bekräfta borttagningen.",
        confirmLabel: "Ta bort",
        errorMessage: failure,
      },
    });

    const dialog = wrapper.get('[role="dialog"]');
    expect(dialog.attributes("aria-modal")).toBe("true");
    const titleId = dialog.attributes("aria-labelledby");
    expect(titleId).toBeTruthy();
    const heading = dialog.get("h2");
    expect(heading.attributes("id")).toBe(titleId);
    expect(heading.text()).toBe("Ta bort klass?");
    expect(heading.isVisible()).toBe(true);

    const alert = wrapper.get('[role="alert"]');
    expect(alert.attributes("aria-live")).toBe("assertive");
    expect(alert.attributes("aria-atomic")).toBe("true");
    expect(alert.text()).toContain(failure);
    expect(alert.find("strong").exists()).toBe(false);
    await alert.get('button[aria-label="Stäng"]').trigger("click");
    expect(wrapper.emitted("dismiss-error")).toEqual([[]]);
    expect(wrapper.emitted("cancel")).toBeUndefined();
    expect(wrapper.emitted("confirm")).toBeUndefined();

    // The parent owns error state; the dialog emits only one clear intent.
    await wrapper.setProps({ errorMessage: null });
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    await wrapper.setProps({ errorMessage: "Ett nytt fel" });
    expect(wrapper.get('[role="alert"]').text()).toContain("Ett nytt fel");
    expect(wrapper.emitted("dismiss-error")).toEqual([[]]);
    wrapper.unmount();
  });
});
