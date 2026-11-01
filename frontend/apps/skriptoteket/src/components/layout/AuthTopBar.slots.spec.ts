/**
 * Stable top-bar slot tests.
 *
 * State changes must not move the top bar's neighbours: focus mode keeps the
 * sidebar toggle's slot, and the logout button reserves its pending word.
 * Rendered positions are proven by the browser walk; these cases assert the
 * markup that reserves the slots.
 */

import { describe, expect, it, vi } from "vitest";

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

const { wrapper, mountLayout, topbarFocusButton } = createShellHarness(routeMocks.route);

describe("top-bar slots stay put across state changes", () => {
  it("keeps the sidebar toggle's slot in focus mode instead of removing it", async () => {
    mountLayout();
    await topbarFocusButton().trigger("click");

    const toggle = wrapper().find(".topbar .topbar-sidebar-toggle");
    expect(toggle.exists()).toBe(true);
    expect(wrapper().get(".topbar").classes()).toContain("topbar--focus-mode");
  });

  it("reserves the pending logout word so the logout slot keeps its width", () => {
    mountLayout();
    const reserve = wrapper().get(".topbar-logout .shell-bar-button__word-reserve");
    expect(reserve.text()).toBe("Loggar ut…");
    expect(reserve.attributes("aria-hidden")).toBe("true");
    expect(wrapper().get(".topbar-logout").attributes("aria-label")).toBe("Logga ut");

    wrapper().unmount();
    mountLayout({ logoutInProgress: true });
    const logout = wrapper().get(".topbar-logout");
    expect(logout.attributes("aria-label")).toBe("Loggar ut…");
    expect(logout.attributes("disabled")).toBeDefined();
    expect(logout.get(".shell-bar-button__word-reserve").text()).toBe("Loggar ut…");
  });
});

describe("top-bar theme button", () => {
  function themeButtons() {
    return wrapper().findAll(".topbar button[aria-haspopup='menu']");
  }

  it("renders exactly one theme button between Logga ut and Meny", () => {
    mountLayout();

    expect(themeButtons()).toHaveLength(1);
    const themeButton = themeButtons()[0];
    expect(themeButton.attributes("aria-label")).toMatch(/^Färgtema: /);

    const selectorRoot = themeButton.element.parentElement;
    expect(selectorRoot?.previousElementSibling?.classList.contains("topbar-logout")).toBe(true);
    expect(selectorRoot?.nextElementSibling?.classList.contains("topbar-menu-button")).toBe(true);
  });

  it("keeps the theme button on immersive game routes", () => {
    mountLayout({ appId: "games.flunk_out_frenzy" });

    expect(wrapper().get(".topbar").classes()).toContain("topbar--immersive");
    expect(themeButtons()).toHaveLength(1);
  });
});
