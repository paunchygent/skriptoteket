/**
 * Shared mount harness for the AuthLayout shell specs.
 *
 * Relationships:
 * - each spec mocks `vue-router` with its own hoisted route object and passes
 *   that object here, because `vi.mock` is hoisted per spec file
 * - `createShellHarness` registers the per-test reset (fresh Pinia, cleared
 *   storage, closed help) and teardown, mounts the real AuthLayout with its
 *   real sidebar, top bar and help openers, and exposes the shell controls
 */

import { mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach } from "vitest";

import { useHelp } from "../help/useHelp";
import AuthLayout from "./AuthLayout.vue";

export const shellRoutes = [
  { label: "ordinary tool route", appId: "chemistry.reagent_prep_chef" },
  { label: "Klassrumskartan route", appId: "classroom.group-seating-studio" },
] as const;

export type ShellRoute = { name: string; params: Record<string, string> };

export type MountLayoutOptions = {
  appId?: string;
  routeName?: string;
  userId?: string;
  logoutInProgress?: boolean;
};

export function createShellHarness(route: ShellRoute) {
  let current: VueWrapper | null = null;

  function wrapper(): VueWrapper {
    if (!current) {
      throw new Error("AuthLayout is not mounted");
    }
    return current;
  }

  function mountLayout(options: MountLayoutOptions = {}): VueWrapper {
    route.name = options.routeName ?? "app-detail";
    route.params.appId = options.appId ?? shellRoutes[0].appId;

    current = mount(AuthLayout, {
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

    return current;
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();

    const help = useHelp();
    help.close({ restoreFocus: false });
    help.setSuspended(false);
    help.showIndex();
    help.setHelpContext(null);

    document.body.classList.remove("app-shell-game-mode");
  });

  afterEach(() => {
    current?.unmount();
    current = null;
    document.body.innerHTML = "";
    document.body.className = "";
  });

  return {
    wrapper,
    mountLayout,
    menuButton: () => wrapper().get(".topbar button.topbar-menu-button"),
    sidebar: () => wrapper().get(".sidebar"),
    drawerHelpButton: () => wrapper().get(".sidebar-footer button[aria-controls='help-panel']"),
    drawerFocusButton: () => wrapper().get(".sidebar-footer button[aria-pressed]"),
    drawerLogoutButton: () => wrapper().get(".sidebar-footer .sidebar-logout"),
    topbarHelpButton: () => wrapper().get(".topbar button.topbar-help[aria-controls='help-panel']"),
    topbarFocusButton: () => wrapper().get(".topbar button.topbar-focus-toggle"),
  };
}
