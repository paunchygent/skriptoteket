/**
 * Planner workspace action-bar tests.
 *
 * These tests freeze the shared zoned toolbar contract so planner workspaces
 * can reuse stable `primary`, `context`, and `secondary` wrappers instead of
 * rebuilding action-row semantics ad hoc.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerWorkspaceActionBar from "./PlannerWorkspaceActionBar.vue";

describe("PlannerWorkspaceActionBar", () => {
  it("renders stable primary, context, and secondary zone wrappers in order", () => {
    const wrapper = mount(PlannerWorkspaceActionBar, {
      slots: {
        primary: '<button data-test="primary-action">Primary</button>',
        context: '<label data-test="context-control">Context</label>',
        secondary: '<button data-test="secondary-action">Secondary</button>',
      },
    });

    const zoneElements = wrapper.findAll("[data-zone]");
    expect(zoneElements).toHaveLength(3);
    expect(zoneElements.map((zone) => zone.attributes("data-zone"))).toEqual([
      "primary",
      "context",
      "secondary",
    ]);
    expect(wrapper.get('[data-ui="planner-workspace-action-bar"]').classes()).toContain("bg-canvas");
    expect(wrapper.get('[data-ui="planner-workspace-action-bar"]').classes()).not.toContain("bg-panel");

    expect(wrapper.get('[data-zone="primary"] [data-test="primary-action"]').text()).toContain("Primary");
    expect(wrapper.get('[data-zone="context"] [data-test="context-control"]').text()).toContain("Context");
    expect(wrapper.get('[data-zone="secondary"] [data-test="secondary-action"]').text()).toContain("Secondary");
  });

  it("omits zone wrappers when their slots are not provided", () => {
    const wrapper = mount(PlannerWorkspaceActionBar, {
      slots: {
        primary: '<button data-test="primary-action">Primary</button>',
        secondary: '<button data-test="secondary-action">Secondary</button>',
      },
    });

    expect(wrapper.find('[data-zone="primary"]').exists()).toBe(true);
    expect(wrapper.find('[data-zone="context"]').exists()).toBe(false);
    expect(wrapper.find('[data-zone="secondary"]').exists()).toBe(true);
  });
});
