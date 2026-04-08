/**
 * Route recovery view tests.
 *
 * These tests verify that malformed public app links and generic unmatched
 * URLs render the correct recovery guidance without changing the canonical
 * public app route contract.
 */

import { mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";

import { routes } from "../router/routes";
import RouteRecoveryView from "./RouteRecoveryView.vue";

function createRouterLinkStub() {
  return {
    props: ["to"],
    template: "<a :href='typeof to === \"string\" ? to : to.path'><slot /></a>",
  };
}

function resolveRecoveryProps(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes,
  });
  const resolved = router.resolve(path);
  const props = resolved.matched.at(-1)?.props.default;

  if (typeof props !== "function") {
    return {};
  }

  return (props as (route: unknown) => unknown)(resolved) as {
    missingAppsPrefix?: boolean;
    missingAppsPrefixAppId?: string | null;
  };
}

describe("RouteRecoveryView", () => {
  it("renders malformed public-route guidance with the canonical path", () => {
    const wrapper = mount(RouteRecoveryView, {
      props: {
        missingAppsPrefixAppId: "classroom.group-seating-studio",
      },
      global: {
        stubs: {
          RouterLink: createRouterLinkStub(),
        },
      },
    });

    expect(wrapper.get("[data-test='public-route-recovery']").text()).toContain(
      "Publika applänkar behöver börja med /public/apps/.",
    );
    expect(wrapper.get("[data-test='recovery-primary-link']").attributes("href")).toBe(
      "/public/apps/classroom.group-seating-studio",
    );
    expect(wrapper.get("[data-test='recovery-canonical-path']").text()).toContain(
      "/public/apps/classroom.group-seating-studio",
    );
  });

  it("renders generic unmatched-route recovery", () => {
    const wrapper = mount(RouteRecoveryView, {
      global: {
        stubs: {
          RouterLink: createRouterLinkStub(),
        },
      },
    });

    expect(wrapper.get("[data-test='not-found-recovery']").text()).toContain(
      "Den sidan finns inte här.",
    );
    expect(wrapper.get("[data-test='recovery-primary-link']").attributes("href")).toBe("/");
    expect(wrapper.get("[data-test='recovery-secondary-link']").attributes("href")).toBe(
      "/public/apps/classroom.group-seating-studio",
    );
  });

  it("renders /public/apps as malformed public recovery without showing /public/apps/apps", () => {
    const wrapper = mount(RouteRecoveryView, {
      props: resolveRecoveryProps("/public/apps"),
      global: {
        stubs: {
          RouterLink: createRouterLinkStub(),
        },
      },
    });

    expect(wrapper.get("[data-test='public-route-recovery']").text()).toContain(
      "Publika applänkar behöver börja med /public/apps/.",
    );
    expect(wrapper.text()).not.toContain("/public/apps/apps");
    expect(wrapper.get("[data-test='recovery-primary-link']").attributes("href")).toBe(
      "/public/apps/classroom.group-seating-studio",
    );
    expect(wrapper.find("[data-test='recovery-canonical-path']").exists()).toBe(false);
  });
});
