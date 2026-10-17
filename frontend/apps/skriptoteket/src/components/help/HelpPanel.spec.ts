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
import { useAuthStore } from "../../stores/auth";

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
    help.setSuspended(false);
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

  it("does not list retired run-history help in the authenticated help index", async () => {
    routeMocks.route.name = "unmapped-route";
    routeMocks.route.fullPath = "/missing";

    const auth = useAuthStore();
    auth.user = {
      id: "user-1",
      email: "teacher@example.com",
      role: "user",
      auth_provider: "huleedu",
    };

    const wrapper = mount(HelpPanel, {
      attachTo: document.body,
    });

    await flushPromises();
    await flushPromises();

    expect(document.body.textContent).toContain("Hjälpindex");
    expect(document.body.textContent).toContain("Mina filer");
    expect(document.body.textContent).not.toContain("Mina körningar");

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

  it("moves focus into the opened panel instead of leaving it on the opener", async () => {
    const help = useHelp();
    help.isOpen.value = false;
    const opener = document.createElement("button");
    document.body.appendChild(opener);
    opener.focus();

    const wrapper = mount(HelpPanel, { attachTo: document.body });
    help.open(opener);
    await flushPromises();

    const panel = document.body.querySelector<HTMLElement>("#help-panel");
    expect(panel).not.toBeNull();
    expect(document.activeElement).toBe(panel);

    wrapper.unmount();
    opener.remove();
  });

  it("takes focus again when help is opened while it is already open", async () => {
    const help = useHelp();
    const wrapper = mount(HelpPanel, { attachTo: document.body });
    await flushPromises();
    const panel = document.body.querySelector<HTMLElement>("#help-panel");

    const elsewhere = document.createElement("button");
    document.body.appendChild(elsewhere);
    elsewhere.focus();
    help.open(elsewhere);
    await flushPromises();

    expect(document.activeElement).toBe(panel);

    wrapper.unmount();
    elsewhere.remove();
  });

  it("is inert while a covering layer suspends help, and only then", async () => {
    const help = useHelp();
    const wrapper = mount(HelpPanel, { attachTo: document.body });
    await flushPromises();
    const panel = document.body.querySelector<HTMLElement>("#help-panel")!;
    expect(panel.hasAttribute("inert")).toBe(false);

    help.setSuspended(true);
    await flushPromises();
    expect(panel.hasAttribute("inert")).toBe(true);

    help.setSuspended(false);
    await flushPromises();
    expect(panel.hasAttribute("inert")).toBe(false);

    wrapper.unmount();
  });

  it("renders no scrim: the page behind the non-modal panel stays usable", async () => {
    const wrapper = mount(HelpPanel, { attachTo: document.body });
    await flushPromises();

    const panel = document.body.querySelector("#help-panel");
    expect(panel?.getAttribute("aria-modal")).toBe("false");
    expect(document.body.querySelector(".help-backdrop")).toBeNull();
    expect(document.body.querySelectorAll(".fixed.inset-0")).toHaveLength(0);

    wrapper.unmount();
  });

  it("closes on Escape inside the panel and stops the key at the panel", async () => {
    const help = useHelp();
    const wrapper = mount(HelpPanel, { attachTo: document.body });
    await flushPromises();

    const outerEscape = vi.fn();
    document.addEventListener("keydown", outerEscape);
    const closeButton = document.body.querySelector<HTMLElement>("#help-panel button");
    closeButton?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await flushPromises();
    document.removeEventListener("keydown", outerEscape);

    expect(help.isOpen.value).toBe(false);
    expect(document.body.querySelector("#help-panel")).toBeNull();
    expect(outerEscape).not.toHaveBeenCalled();

    wrapper.unmount();
  });

  it("leaves Escape from the page behind to the page's own top layer", async () => {
    const help = useHelp();
    const wrapper = mount(HelpPanel, { attachTo: document.body });
    await flushPromises();

    const pageControl = document.createElement("button");
    document.body.appendChild(pageControl);
    pageControl.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await flushPromises();

    expect(help.isOpen.value).toBe(true);
    expect(document.body.querySelector("#help-panel")).not.toBeNull();

    wrapper.unmount();
    pageControl.remove();
  });

  it("returns focus to the opener when Escape closes the panel", async () => {
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
    const panel = document.body.querySelector<HTMLElement>("#help-panel");
    expect(document.activeElement).toBe(panel);

    panel?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await flushPromises();

    expect(help.isOpen.value).toBe(false);
    expect(document.activeElement).toBe(opener);

    wrapper.unmount();
    opener.remove();
  });
});
