/**
 * Help panel route and context behavior tests.
 *
 * These checks keep the global drawer aligned with the SPA route model,
 * including the dual public/authenticated behavior of the `/` route.
 */
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

  it("keeps the newer planner help topic when stale shell cleanup arrives after a mode return", async () => {
    const help = useHelp();
    help.setHelpContext("planner_seating");

    const wrapper = mount(HelpPanel, {
      attachTo: document.body,
    });

    await flushPromises();
    await flushPromises();
    expect(document.body.textContent).toContain("Sittplatser");

    help.setHelpContext("planner_overview");
    help.clearHelpContext("planner_seating");
    await flushPromises();
    await flushPromises();

    expect(document.body.textContent).toContain("Översikt: klass och klassrum");
    expect(document.body.textContent).toContain("Steg 1 -- Skapa din första klass");
    expect(document.body.textContent).not.toContain("Hjälpindex");

    wrapper.unmount();
  });

  it("does not show authenticated Start help on the signed-out public landing route", async () => {
    routeMocks.route.name = "home";
    routeMocks.route.fullPath = "/";

    const wrapper = mount(HelpPanel, {
      attachTo: document.body,
    });

    await flushPromises();
    await flushPromises();

    expect(document.body.textContent).toContain("Hjälpindex");
    expect(document.body.textContent).toContain("Logga in");
    expect(document.body.textContent).toContain("Konto och lösenord");
    expect(document.body.textContent).not.toContain("Start samlar");

    wrapper.unmount();
  });

  it("uses public Klassrumskartan copy on the public app route", async () => {
    routeMocks.route.name = "public-app-detail";
    routeMocks.route.fullPath = "/public/apps/classroom.group-seating-studio";

    const wrapper = mount(HelpPanel, {
      attachTo: document.body,
    });

    await flushPromises();
    await flushPromises();

    expect(document.body.textContent).toContain(
      "Detta är en fullständig förhandsvisning av vad Klassrumskartan gör.",
    );
    expect(document.body.textContent).toContain("Logga in för att spara ditt arbete");
    expect(document.body.textContent).not.toContain("Klicka Starta");
    expect(document.body.textContent).not.toContain("Klicka på appen för att öppna arbetsytan.");

    wrapper.unmount();
  });

  it("uses authenticated app workspace copy on the app detail route", async () => {
    routeMocks.route.name = "app-detail";
    routeMocks.route.fullPath = "/apps/classroom.group-seating-studio";

    const wrapper = mount(HelpPanel, {
      attachTo: document.body,
    });

    await flushPromises();
    await flushPromises();

    expect(document.body.textContent).toContain("Klicka på appen för att öppna arbetsytan.");
    expect(document.body.textContent).toContain("När du är inloggad sparas arbetet i appen");
    expect(document.body.textContent).not.toContain("Detta är en fullständig förhandsvisning");

    wrapper.unmount();
  });

  it("closes deterministically when Escape is pressed", async () => {
    const help = useHelp();
    const wrapper = mount(HelpPanel, {
      attachTo: document.body,
    });

    await flushPromises();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await flushPromises();

    expect(help.isOpen.value).toBe(false);
    expect(document.body.querySelector("#help-panel")).toBeNull();

    wrapper.unmount();
  });

  it("keeps backdrop click closing the drawer", async () => {
    const help = useHelp();
    const wrapper = mount(HelpPanel, {
      attachTo: document.body,
    });

    await flushPromises();
    const backdrop = document.body.querySelector(".help-backdrop");
    expect(backdrop).not.toBeNull();
    backdrop?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await flushPromises();

    expect(help.isOpen.value).toBe(false);
    expect(document.body.querySelector("#help-panel")).toBeNull();

    wrapper.unmount();
  });

  it("returns focus to the opener when Escape closes the drawer", async () => {
    const help = useHelp();
    help.isOpen.value = false;

    const opener = document.createElement("button");
    opener.type = "button";
    opener.textContent = "Hjälp";
    document.body.appendChild(opener);
    opener.focus();

    const wrapper = mount(HelpPanel, {
      attachTo: document.body,
    });

    help.open(opener);
    await flushPromises();
    expect(document.body.querySelector("#help-panel")).not.toBeNull();

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await flushPromises();

    expect(help.isOpen.value).toBe(false);
    expect(document.activeElement).toBe(opener);

    wrapper.unmount();
    opener.remove();
  });

  it("keeps the help index link lists border-only inside the shadowed drawer", async () => {
    routeMocks.route.name = "home";
    routeMocks.route.fullPath = "/";

    const wrapper = mount(HelpPanel, {
      attachTo: document.body,
    });

    await flushPromises();
    await flushPromises();

    const lists = Array.from(document.body.querySelectorAll('[data-test="help-index-list"]'));
    expect(lists.length).toBeGreaterThan(0);
    for (const list of lists) {
      expect(list.classList.contains("shadow-brutal")).toBe(false);
      expect(list.classList.contains("shadow-brutal-sm")).toBe(false);
    }

    wrapper.unmount();
  });
});
