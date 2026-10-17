/**
 * Authenticated shell action tests.
 *
 * These tests mount the real sidebar, top bar and shared help opener together
 * to prove that Hjälp, focus mode and logout stay wired through both the phone
 * drawer and the top bar, that the drawer gives focus back to Meny however it
 * closes, and that the rail toggle and the workspace contract hold. Drawer
 * cases run for an ordinary tool route and Klassrumskartan, which used to have
 * its own shell cutoff and now shares the one shell composition. They assert
 * action state, shared help state, focus return and emitted shell events;
 * rendered breakpoint geometry is proven by the browser walk, not by jsdom.
 * The keyboard cases mount the real help panel beside the shell and try to
 * break the open drawer's modality: Tab past either end, Escape reaching outer
 * listeners, and focus left on a hidden control after a selection. jsdom does
 * not enforce `inert`, so those cases assert the attribute, not its effect.
 */

import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import HelpPanel from "../help/HelpPanel.vue";
import { useHelp } from "../help/useHelp";
import { useLayoutStore } from "../../stores/layout";
import AuthLayout from "./AuthLayout.vue";

const shellRoutes = [
  { label: "ordinary tool route", appId: "chemistry.reagent_prep_chef" },
  { label: "Klassrumskartan route", appId: "classroom.group-seating-studio" },
] as const;

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

let wrapper: VueWrapper | null = null;

function mountLayout(
  options: { appId?: string; routeName?: string; userId?: string; logoutInProgress?: boolean } = {},
): VueWrapper {
  routeMocks.route.name = options.routeName ?? "app-detail";
  routeMocks.route.params.appId = options.appId ?? shellRoutes[0].appId;

  wrapper = mount(AuthLayout, {
    attachTo: document.body,
    props: {
      user: { id: options.userId ?? "user-1", email: "teacher@example.com", role: "user" },
      profile: null,
      aiPolicy: null,
      canSeeContributor: false,
      canSeeAdmin: false,
      canSeeSuperuser: false,
      logoutInProgress: options.logoutInProgress ?? false,
    },
    global: {
      stubs: {
        RouterLink: {
          template: "<a href=\"#\"><slot /></a>",
        },
      },
    },
    slots: {
      default: "<div>Route content</div>",
    },
  });

  return wrapper;
}

function menuButton() {
  return wrapper!.get(".topbar button.topbar-menu-button");
}

function sidebar() {
  return wrapper!.get(".sidebar");
}

function drawerHelpButton() {
  return wrapper!.get(".sidebar-footer button[aria-controls='help-panel']");
}

function drawerFocusButton() {
  return wrapper!.get(".sidebar-footer button[aria-pressed]");
}

function drawerLogoutButton() {
  return wrapper!.get(".sidebar-footer .sidebar-logout");
}

function topbarHelpButton() {
  return wrapper!.get(".topbar button.topbar-help[aria-controls='help-panel']");
}

function topbarFocusButton() {
  return wrapper!.get(".topbar button.topbar-focus-toggle");
}

beforeEach(() => {
  setActivePinia(createPinia());
  localStorage.clear();

  const help = useHelp();
  help.close({ restoreFocus: false });
  help.showIndex();
  help.setHelpContext(null);

  document.body.classList.remove("app-shell-game-mode");
});

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  document.body.innerHTML = "";
  document.body.className = "";
});

describe("AuthLayout shell action wiring", () => {
  describe.each(shellRoutes)("drawer actions in the $label", ({ appId }) => {
    it("opens and closes the drawer from the Meny button", async () => {
      mountLayout({ appId });

      expect(menuButton().attributes("aria-expanded")).toBe("false");
      expect(sidebar().classes()).not.toContain("is-open");

      await menuButton().trigger("click");

      expect(menuButton().attributes("aria-expanded")).toBe("true");
      expect(sidebar().classes()).toContain("is-open");

      await menuButton().trigger("click");

      expect(menuButton().attributes("aria-expanded")).toBe("false");
      expect(sidebar().classes()).not.toContain("is-open");
    });

    it("opens shared help from the drawer and restores focus to Meny when help closes", async () => {
      mountLayout({ appId });
      const help = useHelp();

      await menuButton().trigger("click");

      const helpButton = drawerHelpButton();
      expect(helpButton.attributes("aria-controls")).toBe("help-panel");
      expect(helpButton.attributes("aria-haspopup")).toBe("dialog");

      await helpButton.trigger("click");

      expect(help.isOpen.value).toBe(true);
      expect(sidebar().classes()).not.toContain("is-open");
      expect(menuButton().attributes("aria-expanded")).toBe("false");
      expect(topbarHelpButton().attributes("aria-expanded")).toBe("true");

      help.close();
      await flushPromises();

      expect(help.isOpen.value).toBe(false);
      expect(topbarHelpButton().attributes("aria-expanded")).toBe("false");
      expect(document.activeElement).toBe(menuButton().element);
    });

    it("toggles focus mode both ways from the drawer and returns focus to Meny", async () => {
      mountLayout({ appId });
      const layout = useLayoutStore();

      await menuButton().trigger("click");
      expect(drawerFocusButton().attributes("aria-pressed")).toBe("false");

      await drawerFocusButton().trigger("click");

      expect(layout.focusMode).toBe(true);
      expect(sidebar().classes()).not.toContain("is-open");
      expect(document.activeElement).toBe(menuButton().element);
      expect(drawerFocusButton().attributes("aria-pressed")).toBe("true");
      expect(drawerFocusButton().text()).toBe("Avsluta fokusläge");
      expect(topbarFocusButton().attributes("aria-pressed")).toBe("true");

      await menuButton().trigger("click");
      await drawerFocusButton().trigger("click");

      expect(layout.focusMode).toBe(false);
      expect(drawerFocusButton().attributes("aria-pressed")).toBe("false");
      expect(drawerFocusButton().text()).toBe("Aktivera fokusläge");
      expect(topbarFocusButton().attributes("aria-pressed")).toBe("false");
    });

    it("forwards logout from the drawer and closes it", async () => {
      mountLayout({ appId });

      await menuButton().trigger("click");
      expect(sidebar().classes()).toContain("is-open");

      await drawerLogoutButton().trigger("click");

      expect(sidebar().classes()).not.toContain("is-open");
      expect(wrapper!.emitted("logout")).toHaveLength(1);
    });

    it("keeps the drawer logout disabled and silent while logout is pending", async () => {
      mountLayout({ appId, logoutInProgress: true });

      await menuButton().trigger("click");

      const drawerLogout = drawerLogoutButton();
      const topbarLogout = wrapper!.get(".topbar button.topbar-logout");

      expect(drawerLogout.attributes("disabled")).toBeDefined();
      expect(topbarLogout.attributes("disabled")).toBeDefined();

      (drawerLogout.element as HTMLButtonElement).click();
      (topbarLogout.element as HTMLButtonElement).click();
      await flushPromises();

      expect(sidebar().classes()).toContain("is-open");
      expect(wrapper!.emitted("logout")).toBeUndefined();
    });
  });

  it("drives help, focus mode and logout from the top bar", async () => {
    mountLayout();
    const help = useHelp();
    const layout = useLayoutStore();

    await topbarHelpButton().trigger("click");

    expect(help.isOpen.value).toBe(true);
    expect(sidebar().classes()).not.toContain("is-open");

    expect(topbarFocusButton().attributes("aria-pressed")).toBe("false");
    await topbarFocusButton().trigger("click");

    expect(layout.focusMode).toBe(true);
    expect(topbarFocusButton().attributes("aria-pressed")).toBe("true");

    await wrapper!.get(".topbar button.topbar-logout").trigger("click");

    expect(wrapper!.emitted("logout")).toHaveLength(1);
  });

  it("moves focus into the opened drawer and gives it back to Meny on Escape and on the backdrop", async () => {
    mountLayout();

    await menuButton().trigger("click");
    await flushPromises();

    expect(document.activeElement).toBe(wrapper!.get(".sidebar button[aria-label='Stäng menyn']").element);

    await sidebar().trigger("keydown", { key: "Escape" });

    expect(sidebar().classes()).not.toContain("is-open");
    expect(menuButton().attributes("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(menuButton().element);

    await menuButton().trigger("click");
    await wrapper!.get(".auth-nav-backdrop").trigger("click");

    expect(sidebar().classes()).not.toContain("is-open");
    expect(wrapper!.find(".auth-nav-backdrop").exists()).toBe(false);
    expect(document.activeElement).toBe(menuButton().element);
  });

  it("keeps the rail per user and independent of focus mode", async () => {
    mountLayout({ userId: "teacher-a" });
    const railToggle = () => wrapper!.get(".topbar button.topbar-sidebar-toggle");

    expect(railToggle().attributes("aria-label")).toBe("Fäll ihop menyn");
    await railToggle().trigger("click");

    expect(railToggle().attributes("aria-pressed")).toBe("true");
    expect(railToggle().attributes("aria-label")).toBe("Fäll ut menyn");
    expect(sidebar().classes()).toContain("is-rail");

    await topbarFocusButton().trigger("click");
    await topbarFocusButton().trigger("click");
    expect(sidebar().classes()).toContain("is-rail");

    wrapper!.unmount();
    mountLayout({ userId: "teacher-b" });
    expect(sidebar().classes()).not.toContain("is-rail");
    expect(railToggle().attributes("aria-pressed")).toBe("false");

    wrapper!.unmount();
    mountLayout({ userId: "teacher-a" });
    expect(sidebar().classes()).toContain("is-rail");
  });

  it("names the exam workspace beside the brand and offers it the phone page slot", () => {
    mountLayout({ routeName: "exam-workspace", appId: "" });

    expect(wrapper!.get(".topbar .topbar-brand").text()).toBe("SkriptoteketProvredigering");
    expect(wrapper!.get(".topbar #app-topbar-page-slot").element.childElementCount).toBe(0);

    wrapper!.unmount();
    mountLayout();

    expect(wrapper!.get(".topbar .topbar-brand").text()).toBe("Skriptoteket");
    expect(wrapper!.find(".topbar #app-topbar-page-slot").exists()).toBe(true);
  });

  it("gives immersive game routes only the way back, Hjälp and Logga ut", async () => {
    mountLayout({ appId: "games.flunk_out_frenzy" });

    expect(wrapper!.find(".sidebar").exists()).toBe(false);
    expect(wrapper!.find(".topbar-menu-button").exists()).toBe(false);
    expect(wrapper!.find(".topbar-sidebar-toggle").exists()).toBe(false);
    expect(wrapper!.find(".topbar-focus-toggle").exists()).toBe(false);
    expect(wrapper!.get(".topbar .topbar-back-link").text()).toBe("Tillbaka till katalogen");
    expect(document.body.classList.contains("app-shell-game-mode")).toBe(true);

    await topbarHelpButton().trigger("click");
    expect(useHelp().isOpen.value).toBe(true);

    await wrapper!.get(".topbar button.topbar-logout").trigger("click");
    expect(wrapper!.emitted("logout")).toHaveLength(1);
  });

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
      return wrapper!.get(".sidebar button[aria-label='Stäng menyn']").element as HTMLElement;
    }

    it("wraps Tab and Shift+Tab inside the open drawer and makes the page behind inert", async () => {
      mountLayout();
      await menuButton().trigger("click");
      await flushPromises();

      expect(wrapper!.get(".topbar").attributes("inert")).toBeDefined();
      expect(wrapper!.get("main").attributes("inert")).toBeDefined();

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
      expect(wrapper!.get(".topbar").attributes("inert")).toBeUndefined();
      expect(wrapper!.get("main").attributes("inert")).toBeUndefined();
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
      expect(wrapper!.emitted()).not.toHaveProperty("dismiss");
      expect(wrapper!.get("main").attributes("inert")).toBeUndefined();
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
      expect(wrapper!.get("main").attributes("inert")).toBeUndefined();
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
      expect(wrapper!.get("main").attributes("inert")).toBeUndefined();

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
  });

  describe("top-bar slots stay put across state changes", () => {
    it("keeps the sidebar toggle's slot in focus mode instead of removing it", async () => {
      mountLayout();
      await topbarFocusButton().trigger("click");

      const toggle = wrapper!.find(".topbar .topbar-sidebar-toggle");
      expect(toggle.exists()).toBe(true);
      expect(wrapper!.get(".topbar").classes()).toContain("topbar--focus-mode");
    });

    it("reserves the pending logout word so the logout slot keeps its width", () => {
      mountLayout();
      const reserve = wrapper!.get(".topbar-logout .shell-bar-button__word-reserve");
      expect(reserve.text()).toBe("Loggar ut…");
      expect(reserve.attributes("aria-hidden")).toBe("true");
      expect(wrapper!.get(".topbar-logout").attributes("aria-label")).toBe("Logga ut");

      wrapper!.unmount();
      mountLayout({ logoutInProgress: true });
      const logout = wrapper!.get(".topbar-logout");
      expect(logout.attributes("aria-label")).toBe("Loggar ut…");
      expect(logout.attributes("disabled")).toBeDefined();
      expect(logout.get(".shell-bar-button__word-reserve").text()).toBe("Loggar ut…");
    });
  });
});
