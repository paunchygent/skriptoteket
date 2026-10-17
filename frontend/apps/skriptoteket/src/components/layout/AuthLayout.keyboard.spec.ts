/**
 * Phone drawer and shared help keyboard lifecycle tests.
 *
 * These cases mount the real help panel beside the shell and try to break the
 * open drawer's modality: Tab past either end, Escape reaching outer listeners,
 * focus left on a hidden control after a selection, and help that is already
 * open when the drawer opens or is entered again. jsdom does not enforce
 * `inert`, so those cases assert the attribute, not its effect.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import HelpPanel from "../help/HelpPanel.vue";
import { useHelp } from "../help/useHelp";
import { createShellHarness } from "./authLayoutShellHarness";

const routeMocks = vi.hoisted(() => ({
  route: {
    name: "app-detail" as string,
    params: {
      appId: "chemistry.reagent_prep_chef",
    } as Record<string, string>,
  },
}));

vi.mock("vue-router", () => ({
  RouterLink: {
    template: "<a><slot /></a>",
  },
  useRoute: () => routeMocks.route,
}));

const { wrapper, mountLayout, menuButton, sidebar, drawerHelpButton, topbarHelpButton } =
  createShellHarness(routeMocks.route);

describe("phone drawer and help keyboard lifecycle", () => {
  let outerKeydown: Mock<(event: KeyboardEvent) => void>;

  beforeEach(() => {
    outerKeydown = vi.fn<(event: KeyboardEvent) => void>();
    document.addEventListener("keydown", outerKeydown);
  });

  afterEach(() => {
    document.removeEventListener("keydown", outerKeydown);
    vi.unstubAllGlobals();
  });

  function key(target: Element, init: KeyboardEventInit): KeyboardEvent {
    const event = new KeyboardEvent("keydown", { bubbles: true, cancelable: true, ...init });
    target.dispatchEvent(event);
    return event;
  }

  function drawerControls(): HTMLElement[] {
    return Array.from(
      sidebar().element.querySelectorAll<HTMLElement>("a[href], button:not([disabled])"),
    );
  }

  function closeButton(): HTMLElement {
    return wrapper().get(".sidebar button[aria-label='Stäng menyn']").element as HTMLElement;
  }

  it("wraps Tab and Shift+Tab inside the open drawer and makes the page behind inert", async () => {
    mountLayout();
    await menuButton().trigger("click");
    await flushPromises();

    expect(wrapper().get(".topbar").attributes("inert")).toBeDefined();
    expect(wrapper().get("main").attributes("inert")).toBeDefined();

    const controls = drawerControls();
    const last = controls[controls.length - 1]!;
    expect(last.classList.contains("sidebar-logout")).toBe(true);

    last.focus();
    const forward = key(last, { key: "Tab" });
    expect(forward.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(closeButton());

    const backward = key(closeButton(), { key: "Tab", shiftKey: true });
    expect(backward.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(last);

    const middle = controls[2]!;
    middle.focus();
    expect(key(middle, { key: "Tab" }).defaultPrevented).toBe(false);

    await sidebar().trigger("keydown", { key: "Escape" });
    await flushPromises();
    expect(wrapper().get(".topbar").attributes("inert")).toBeUndefined();
    expect(wrapper().get("main").attributes("inert")).toBeUndefined();
  });

  it("pulls focus that sits outside the open drawer back in on Tab", async () => {
    mountLayout();
    await menuButton().trigger("click");
    await flushPromises();

    const outside = document.createElement("button");
    document.body.appendChild(outside);
    outside.focus();
    key(sidebar().element, { key: "Tab", shiftKey: true });

    const controls = drawerControls();
    expect(document.activeElement).toBe(controls[controls.length - 1]);
    outside.remove();
  });

  it("stops Escape at the open drawer so no outer listener also reacts", async () => {
    mountLayout();
    await menuButton().trigger("click");
    await flushPromises();

    const link = sidebar().element.querySelector<HTMLElement>(".sidebar-nav a")!;
    link.focus();
    const escape = key(link, { key: "Escape" });
    await flushPromises();

    expect(escape.defaultPrevented).toBe(true);
    expect(outerKeydown).not.toHaveBeenCalled();
    expect(sidebar().classes()).not.toContain("is-open");
    expect(document.activeElement).toBe(menuButton().element);
  });

  it("passes Escape and Tab through the inline sidebar while no drawer is open", async () => {
    mountLayout();
    const link = sidebar().element.querySelector<HTMLElement>(".sidebar-nav a")!;
    link.focus();

    expect(key(link, { key: "Escape" }).defaultPrevented).toBe(false);
    expect(outerKeydown).toHaveBeenCalledTimes(1);
    expect(key(link, { key: "Tab" }).defaultPrevented).toBe(false);
    expect(wrapper().emitted()).not.toHaveProperty("dismiss");
    expect(wrapper().get("main").attributes("inert")).toBeUndefined();
  });

  it("leaves focus on the visible Meny button after a drawer link is chosen", async () => {
    mountLayout();
    await menuButton().trigger("click");
    await flushPromises();

    const link = Array.from(sidebar().element.querySelectorAll<HTMLElement>(".sidebar-nav a")).find(
      (item) => item.textContent?.includes("Katalog"),
    )!;
    link.focus();
    link.click();
    await flushPromises();

    expect(sidebar().classes()).not.toContain("is-open");
    expect(document.activeElement).toBe(menuButton().element);
  });

  it("closes the drawer and lifts inert when the window widens past the phone width", async () => {
    let onChange: ((event: { matches: boolean }) => void) | null = null;
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: true,
      media: query,
      addEventListener: (_type: string, listener: (event: { matches: boolean }) => void) => {
        onChange = listener;
      },
      removeEventListener: vi.fn(),
    }));
    mountLayout();
    await menuButton().trigger("click");
    expect(onChange).not.toBeNull();

    onChange!({ matches: false });
    await flushPromises();

    expect(sidebar().classes()).not.toContain("is-open");
    expect(wrapper().get("main").attributes("inert")).toBeUndefined();
  });

  it("moves focus into the real help panel from the drawer and back to Meny on Escape", async () => {
    mountLayout();
    const helpPanel = mount(HelpPanel, { attachTo: document.body });
    await menuButton().trigger("click");
    await drawerHelpButton().trigger("click");
    await flushPromises();

    const panel = document.querySelector<HTMLElement>("#help-panel")!;
    expect(panel).not.toBeNull();
    expect(document.activeElement).toBe(panel);
    expect(wrapper().get("main").attributes("inert")).toBeUndefined();

    const escape = key(panel, { key: "Escape" });
    await flushPromises();

    expect(outerKeydown).not.toHaveBeenCalled();
    expect(escape.defaultPrevented).toBe(false);
    expect(useHelp().isOpen.value).toBe(false);
    expect(document.activeElement).toBe(menuButton().element);
    helpPanel.unmount();
  });

  it("moves focus from the top-bar Hjälp into the help panel and back again", async () => {
    mountLayout();
    const helpPanel = mount(HelpPanel, { attachTo: document.body });
    const opener = topbarHelpButton().element as HTMLElement;
    opener.focus();
    opener.click();
    await flushPromises();

    const panel = document.querySelector<HTMLElement>("#help-panel")!;
    expect(document.activeElement).toBe(panel);
    expect(document.querySelector(".help-backdrop")).toBeNull();

    key(panel, { key: "Escape" });
    await flushPromises();
    expect(document.activeElement).toBe(opener);
    helpPanel.unmount();
  });

  it("makes already open help inert under the drawer and lifts it when the drawer closes", async () => {
    mountLayout();
    const helpPanel = mount(HelpPanel, { attachTo: document.body });
    await menuButton().trigger("click");
    await drawerHelpButton().trigger("click");
    await flushPromises();
    const panel = document.querySelector<HTMLElement>("#help-panel")!;
    expect(panel.hasAttribute("inert")).toBe(false);

    await menuButton().trigger("click");
    await flushPromises();
    expect(sidebar().classes()).toContain("is-open");
    expect(useHelp().isOpen.value).toBe(true);
    expect(panel.hasAttribute("inert")).toBe(true);

    key(sidebar().element, { key: "Escape" });
    await flushPromises();
    expect(panel.hasAttribute("inert")).toBe(false);
    expect(document.activeElement).toBe(menuButton().element);
    helpPanel.unmount();
  });

  it("moves focus back into already open help when the drawer's Hjälp is chosen again", async () => {
    mountLayout();
    const helpPanel = mount(HelpPanel, { attachTo: document.body });
    await menuButton().trigger("click");
    await drawerHelpButton().trigger("click");
    await flushPromises();

    await menuButton().trigger("click");
    await flushPromises();
    const drawerHelp = drawerHelpButton().element as HTMLElement;
    drawerHelp.focus();
    drawerHelp.click();
    await flushPromises();

    const panel = document.querySelector<HTMLElement>("#help-panel")!;
    expect(sidebar().classes()).not.toContain("is-open");
    expect(panel.hasAttribute("inert")).toBe(false);
    expect(document.activeElement).toBe(panel);

    key(panel, { key: "Escape" });
    await flushPromises();
    expect(outerKeydown).not.toHaveBeenCalled();
    expect(useHelp().isOpen.value).toBe(false);
    expect(document.activeElement).toBe(menuButton().element);
    helpPanel.unmount();
  });
});
