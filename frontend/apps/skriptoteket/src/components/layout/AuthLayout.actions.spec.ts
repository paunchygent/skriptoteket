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
 * Keyboard modality lives in `AuthLayout.keyboard.spec.ts`, stable top-bar
 * slots in `AuthTopBar.slots.spec.ts`.
 */

import { flushPromises } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { useHelp } from "../help/useHelp";
import { useLayoutStore } from "../../stores/layout";
import { createShellHarness, shellRoutes } from "./authLayoutShellHarness";

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

const {
  wrapper,
  mountLayout,
  menuButton,
  sidebar,
  drawerHelpButton,
  drawerFocusButton,
  drawerLogoutButton,
  topbarHelpButton,
  topbarFocusButton,
} = createShellHarness(routeMocks.route);

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
      expect(wrapper().emitted("logout")).toHaveLength(1);
    });

    it("keeps the drawer logout disabled and silent while logout is pending", async () => {
      mountLayout({ appId, logoutInProgress: true });

      await menuButton().trigger("click");

      const drawerLogout = drawerLogoutButton();
      const topbarLogout = wrapper().get(".topbar button.topbar-logout");

      expect(drawerLogout.attributes("disabled")).toBeDefined();
      expect(topbarLogout.attributes("disabled")).toBeDefined();

      (drawerLogout.element as HTMLButtonElement).click();
      (topbarLogout.element as HTMLButtonElement).click();
      await flushPromises();

      expect(sidebar().classes()).toContain("is-open");
      expect(wrapper().emitted("logout")).toBeUndefined();
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

    await wrapper().get(".topbar button.topbar-logout").trigger("click");

    expect(wrapper().emitted("logout")).toHaveLength(1);
  });

  it("moves focus into the opened drawer and gives it back to Meny on Escape and on the backdrop", async () => {
    mountLayout();

    await menuButton().trigger("click");
    await flushPromises();

    expect(document.activeElement).toBe(wrapper().get(".sidebar button[aria-label='Stäng menyn']").element);

    await sidebar().trigger("keydown", { key: "Escape" });

    expect(sidebar().classes()).not.toContain("is-open");
    expect(menuButton().attributes("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(menuButton().element);

    await menuButton().trigger("click");
    await wrapper().get(".auth-nav-backdrop").trigger("click");

    expect(sidebar().classes()).not.toContain("is-open");
    expect(wrapper().find(".auth-nav-backdrop").exists()).toBe(false);
    expect(document.activeElement).toBe(menuButton().element);
  });

  it("keeps the rail per user and independent of focus mode", async () => {
    mountLayout({ userId: "teacher-a" });
    const railToggle = () => wrapper().get(".topbar button.topbar-sidebar-toggle");

    expect(railToggle().attributes("aria-label")).toBe("Fäll ihop menyn");
    await railToggle().trigger("click");

    expect(railToggle().attributes("aria-pressed")).toBe("true");
    expect(railToggle().attributes("aria-label")).toBe("Fäll ut menyn");
    expect(sidebar().classes()).toContain("is-rail");

    await topbarFocusButton().trigger("click");
    await topbarFocusButton().trigger("click");
    expect(sidebar().classes()).toContain("is-rail");

    wrapper().unmount();
    mountLayout({ userId: "teacher-b" });
    expect(sidebar().classes()).not.toContain("is-rail");
    expect(railToggle().attributes("aria-pressed")).toBe("false");

    wrapper().unmount();
    mountLayout({ userId: "teacher-a" });
    expect(sidebar().classes()).toContain("is-rail");
  });

  it("names the exam workspace beside the brand and offers it the phone page slot", () => {
    mountLayout({ routeName: "exam-workspace", appId: "" });

    expect(wrapper().get(".topbar .topbar-brand").text()).toBe("SkriptoteketProvredigering");
    expect(wrapper().get(".topbar #app-topbar-page-slot").element.childElementCount).toBe(0);

    wrapper().unmount();
    mountLayout();

    expect(wrapper().get(".topbar .topbar-brand").text()).toBe("Skriptoteket");
    expect(wrapper().find(".topbar #app-topbar-page-slot").exists()).toBe(true);
  });

  it("gives immersive game routes only the way back, Hjälp and Logga ut", async () => {
    mountLayout({ appId: "games.flunk_out_frenzy" });

    expect(wrapper().find(".sidebar").exists()).toBe(false);
    expect(wrapper().find(".topbar-menu-button").exists()).toBe(false);
    expect(wrapper().find(".topbar-sidebar-toggle").exists()).toBe(false);
    expect(wrapper().find(".topbar-focus-toggle").exists()).toBe(false);
    expect(wrapper().get(".topbar .topbar-back-link").text()).toBe("Tillbaka till katalogen");
    expect(document.body.classList.contains("app-shell-game-mode")).toBe(true);

    await topbarHelpButton().trigger("click");
    expect(useHelp().isOpen.value).toBe(true);

    await wrapper().get(".topbar button.topbar-logout").trigger("click");
    expect(wrapper().emitted("logout")).toHaveLength(1);
  });
});
