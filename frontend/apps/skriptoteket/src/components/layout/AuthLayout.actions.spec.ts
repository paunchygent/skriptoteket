/**
 * Authenticated shell action tests.
 *
 * These tests mount the real sidebar, top bar and shared help opener together
 * to prove that Hjälp, focus mode and logout stay wired through both the drawer
 * and the desktop top bar. Drawer cases run for the ordinary and planner shell
 * routes, because the planner's wider desktop cutoff is what left the drawer as
 * the only action surface at intermediate widths. They assert action state,
 * shared help state, focus return and emitted shell events; rendered breakpoint
 * geometry is proven by the parent's browser walk, not by jsdom.
 */

import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useHelp } from "../help/useHelp";
import { useLayoutStore } from "../../stores/layout";
import AuthLayout from "./AuthLayout.vue";

const shellRoutes = [
  {
    label: "ordinary shell",
    appId: "chemistry.reagent_prep_chef",
    preferXl: false,
  },
  {
    label: "planner shell",
    appId: "classroom.group-seating-studio",
    preferXl: true,
  },
] as const;

const routeMocks = vi.hoisted(() => ({
  route: {
    name: "app-detail",
    params: {
      appId: "chemistry.reagent_prep_chef",
    },
  },
}));

vi.mock("vue-router", () => ({
  RouterLink: {
    template: "<a><slot /></a>",
  },
  useRoute: () => routeMocks.route,
}));

let wrapper: VueWrapper | null = null;

function mountLayout(options: { appId?: string; logoutInProgress?: boolean } = {}): VueWrapper {
  routeMocks.route.params.appId = options.appId ?? shellRoutes[0].appId;

  wrapper = mount(AuthLayout, {
    attachTo: document.body,
    props: {
      user: { id: "user-1", email: "teacher@example.com", role: "user" },
      profile: null,
      aiPolicy: null,
      canSeeContributor: false,
      canSeeAdmin: false,
      canSeeSuperuser: false,
      logoutInProgress: options.logoutInProgress ?? false,
    },
    global: {
      stubs: {
        BrandLogo: true,
        RouterLink: {
          template: "<a><slot /></a>",
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
  return wrapper!.get("button.hamburger");
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
  return wrapper!.get(".sidebar-footer .sidebar-logout-btn");
}

function topbarHelpButton() {
  return wrapper!.get(".top-user-bar button[aria-controls='help-panel']");
}

function topbarFocusButton() {
  return wrapper!.get(".top-user-bar .focus-mode-toggle");
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
  describe.each(shellRoutes)("drawer actions in the $label", ({ appId, preferXl }) => {
    it("opens and closes the drawer from the Meny button", async () => {
      mountLayout({ appId });

      expect(sidebar().classes().includes("sidebar--xl-desktop-breakpoint")).toBe(preferXl);
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
      const topbarLogout = wrapper!.get(".top-user-bar .logout-btn");

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

    await wrapper!.get(".top-user-bar .logout-btn").trigger("click");

    expect(wrapper!.emitted("logout")).toHaveLength(1);
  });
});
