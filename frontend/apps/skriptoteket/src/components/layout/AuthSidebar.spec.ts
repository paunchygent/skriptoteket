/**
 * Authenticated sidebar navigation tests.
 *
 * These tests keep the persistent shell navigation aligned with the current
 * app-first product surface, where retired run-history links are not exposed
 * as primary teacher navigation.
 */

import { RouterLinkStub, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import AuthSidebar from "./AuthSidebar.vue";

const helpMocks = vi.hoisted(() => ({
  open: vi.fn(),
}));

vi.mock("../help/useHelp", () => ({
  useHelp: () => ({
    open: helpMocks.open,
  }),
}));

function mountSidebar() {
  return mount(AuthSidebar, {
    props: {
      isOpen: true,
      isFocusMode: false,
      preferXlDesktopBreakpoint: false,
      user: { email: "teacher@example.com" },
      canSeeContributor: false,
      canSeeAdmin: false,
      canSeeSuperuser: false,
      logoutInProgress: false,
    },
    global: {
      stubs: {
        BrandLogo: true,
        RouterLink: RouterLinkStub,
      },
    },
  });
}

describe("AuthSidebar", () => {
  it("does not expose the retired Mina körningar link", () => {
    const wrapper = mountSidebar();
    const linkTargets = wrapper.findAllComponents(RouterLinkStub).map((link) => link.props("to"));

    expect(wrapper.text()).not.toContain("Mina körningar");
    expect(linkTargets).not.toContain("/my-runs");
    expect(wrapper.text()).toContain("Mina filer");
    expect(linkTargets).toContain("/vault");
  });
});
