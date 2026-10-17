import { mount } from "@vue/test-utils";
import { defineComponent, h, ref } from "vue";
import { describe, expect, it } from "vitest";

import { useReagentPrepChefForm } from "../../../composables/reagentPrepChef/useReagentPrepChefForm";
import ReagentPrepChefStepClass from "./ReagentPrepChefStepClass.vue";

// The real form owns validation; the child must communicate and gate it at entry.
describe("Reagent Prep Chef class margin", () => {
  it.each(["0,9", "-0,1", "fel", ""])("explains invalid margin %j before continuing and recovers", async (invalid) => {
    const wrapper = mount(defineComponent({
      setup() {
        const state = useReagentPrepChefForm(ref([]));
        return () => h(ReagentPrepChefStepClass, {
          form: state.form,
          derivedGroups: state.derivedGroups.value,
          derivedTotalVolumeMl: state.derivedTotalVolumeMl.value,
          fieldErrors: state.fieldErrors.value,
        });
      },
    }));
    try {
      const child = wrapper.getComponent(ReagentPrepChefStepClass);
      const margin = wrapper.get<HTMLInputElement>("#rpc-safety-factor");
      const next = wrapper.findAll("button").find((button) => button.text().includes("Fortsätt"))!;
      await margin.setValue(invalid);
      expect(margin.attributes("aria-invalid")).toBe("true");
      const descriptionId = margin.attributes("aria-describedby");
      expect(descriptionId).toBeTruthy();
      const description = wrapper.findAll("[id]").find((item) => item.attributes("id") === descriptionId)!;
      expect(description.text()).toMatch(/marginal/i);
      expect(next.attributes("disabled")).toBeDefined();
      await next.trigger("click");
      expect(child.emitted("next")).toBeUndefined();

      await margin.setValue("0,5");
      expect(margin.attributes("aria-invalid")).not.toBe("true");
      expect(next.attributes("disabled")).toBeUndefined();
      await next.trigger("click");
      expect(child.emitted("next")).toHaveLength(1);
    } finally {
      wrapper.unmount();
    }
  });
});
