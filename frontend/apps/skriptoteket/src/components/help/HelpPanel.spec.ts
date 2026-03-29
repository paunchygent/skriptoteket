import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HelpPanel from "./HelpPanel.vue";
import { useHelp } from "./useHelp";

const routeMocks = vi.hoisted(() => ({
  route: {
    name: "app-detail",
    fullPath: "/apps/classroom.group-seating-studio",
  },
}));

vi.mock("vue-router", () => ({
  useRoute: () => routeMocks.route,
}));

async function flushPromises(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
  await nextTick();
  await nextTick();
  await vi.dynamicImportSettled();
  await nextTick();
}

describe("HelpPanel", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    routeMocks.route.name = "app-detail";
    routeMocks.route.fullPath = "/apps/classroom.group-seating-studio";
    document.body.innerHTML = "";

    const help = useHelp();
    help.isOpen.value = true;
    help.activeTopic.value = null;
    help.setHelpContext(null);
  });

  it("renders the generated planner overview help from planner context", async () => {
    const help = useHelp();
    help.setHelpContext("planner_overview");

    const wrapper = mount(HelpPanel, {
      attachTo: document.body,
    });

    await flushPromises();
    await flushPromises();

    expect(document.body.textContent).toContain("Översikt: klass och klassrum");
    expect(document.body.textContent).toContain("Steg 1 -- Skapa din första klass");
    expect(document.body.textContent).toContain("Steg 2 -- Skapa ditt första klassrum");

    wrapper.unmount();
  });

  it("switches planner help content when the planner context changes", async () => {
    const help = useHelp();
    help.setHelpContext("planner_overview");

    const wrapper = mount(HelpPanel, {
      attachTo: document.body,
    });

    await flushPromises();
    await flushPromises();
    expect(document.body.textContent).toContain("Översikt: klass och klassrum");

    help.setHelpContext("planner_rules");
    await flushPromises();
    await flushPromises();

    expect(document.body.textContent).toContain("Regler och sammanfattning");
    expect(document.body.textContent).toContain("Färre regler = bättre resultat");

    wrapper.unmount();
  });
});
