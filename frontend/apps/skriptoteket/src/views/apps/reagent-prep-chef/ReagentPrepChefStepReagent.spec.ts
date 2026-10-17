import { mount } from "@vue/test-utils";
import { defineComponent, h, ref } from "vue";
import { describe, expect, it } from "vitest";

import { useReagentPrepChefForm } from "../../../composables/reagentPrepChef/useReagentPrepChefForm";
import ReagentPrepChefStepReagent from "./ReagentPrepChefStepReagent.vue";
import type { ReagentPrepChefChemicalOption } from "./types";

const chemicals: ReagentPrepChefChemicalOption[] = [
  { key: "Al", display_name: "Aluminium (Al)", aliases: [] },
  { key: "NH3", display_name: "Ammoniak (NH3)", aliases: [] },
  { key: "NaCl", display_name: "Natriumklorid", aliases: [] },
];

function mountStep() {
  return mount(defineComponent({
    setup() {
      const state = useReagentPrepChefForm(ref(chemicals));
      return () => h(ReagentPrepChefStepReagent, {
        form: state.form,
        chemicals,
        selectedChemicalKey: state.selectedChemicalKey.value,
        chemicalQuery: state.chemicalQuery.value,
        chemicalSearchIsActive: state.chemicalSearchIsActive.value,
        chemicalSearchResults: state.chemicalSearchResults.value,
        "onUpdate:chemicalQuery": (value: string) => { state.chemicalQuery.value = value; },
        "onUpdate:selectedChemicalKey": (value: string) => { state.selectedChemicalKey.value = value; },
        onSelectChemical: state.selectChemicalFromSearch,
      });
    },
  }));
}

describe("Reagent Prep Chef substance choices", () => {
  it("names the select and exposes search choices as ordinary buttons that close on pick", async () => {
    const wrapper = mountStep();
    try {
      const select = wrapper.get("select");
      const label = wrapper.findAll("label").find((item) => item.text().includes("Ämneslista"))!;
      const labelledBy = select.attributes("aria-labelledby");
      expect(Boolean(select.attributes("aria-label")) || Boolean(labelledBy && wrapper.find(`[id="${labelledBy}"]`).exists()) ||
        Boolean(select.attributes("id") && label.attributes("for") === select.attributes("id"))).toBe(true);
      await wrapper.get('input[type="search"]').setValue("Al");
      expect(wrapper.find('[role="listbox"]').exists()).toBe(false);
      const choice = wrapper.findAll("button").find((button) => button.text().includes("Aluminium"))!;
      expect(choice).toBeDefined();
      await choice.trigger("click");
      expect(wrapper.get<HTMLInputElement>("#rpc-formula").element.value).toBe("Al");
      expect(wrapper.findAll("button").some((button) => button.text().includes("Aluminium"))).toBe(false);
    } finally {
      wrapper.unmount();
    }
  });

  it("shows each formula once while adding it to names that lack it", () => {
    const wrapper = mountStep();
    try {
      const options = wrapper.findAll("option").map((option) => option.text());
      expect(options).toContain("Aluminium (Al)");
      expect(options).toContain("Ammoniak (NH3)");
      expect(options).toContain("Natriumklorid (NaCl)");
    } finally {
      wrapper.unmount();
    }
  });
});
