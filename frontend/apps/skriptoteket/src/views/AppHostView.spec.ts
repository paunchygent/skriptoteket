/**
 * Curated app host tests.
 *
 * These tests verify that the app host resolves bespoke curated apps to their
 * dedicated view components and blocks gracefully when a bespoke view is
 * missing.
 */

import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AppHostView from "./AppHostView.vue";
import type { components } from "../api/openapi";

type AppDetailResponse = components["schemas"]["AppDetailResponse"];
type FlunkOutFrenzyBootstrap = {
  app_id: string;
  title: string;
  summary: string;
  app_version: string;
  ruleset_id: string;
  feature_flags: {
    audio_enabled: boolean;
    replay_capture_enabled: boolean;
    score_submission_enabled: boolean;
  };
};

const routeMocks = vi.hoisted(() => ({
  route: {
    params: {
      appId: "games.flunk_out_frenzy",
    },
  },
}));

const clientMocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  isApiError: vi.fn(),
}));

vi.mock("vue-router", () => ({
  useRoute: () => routeMocks.route,
}));

vi.mock("../api/client", () => ({
  apiGet: clientMocks.apiGet,
  isApiError: clientMocks.isApiError,
}));

vi.mock("./AppDetailView.vue", () => ({
  default: {
    template: "<div>AppDetailViewStub</div>",
  },
}));

async function flushPromises(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
  await nextTick();
  await nextTick();
  await vi.dynamicImportSettled();
  await nextTick();
}

function createAppDetail(
  overrides: Partial<AppDetailResponse> = {},
): AppDetailResponse {
  return {
    app_id: "games.flunk_out_frenzy",
    tool_id: "3b891fb1-851a-5b11-a368-3b0a0f7fbcad",
    title: "Flunk-Out Frenzy",
    summary: "Local browser pinball with future official high scores.",
    min_role: "user",
    ui_mode: "bespoke_required",
    ...overrides,
  };
}

function createBootstrap(
  overrides: Partial<FlunkOutFrenzyBootstrap> = {},
): FlunkOutFrenzyBootstrap {
  return {
    app_id: "games.flunk_out_frenzy",
    title: "Flunk-Out Frenzy",
    summary: "Local browser pinball with future official high scores.",
    app_version: "app:0.2.0",
    ruleset_id: "flunk_out_frenzy.prototype_alpha.v1",
    feature_flags: {
      audio_enabled: true,
      replay_capture_enabled: false,
      score_submission_enabled: false,
    },
    ...overrides,
  };
}

describe("AppHostView", () => {
  beforeEach(() => {
    routeMocks.route.params.appId = "games.flunk_out_frenzy";
    clientMocks.apiGet.mockReset();
    clientMocks.isApiError.mockReset();
    clientMocks.isApiError.mockReturnValue(false);
  });

  it("renders the dedicated Flunk-Out Frenzy shell for the bespoke app route", async () => {
    clientMocks.apiGet.mockImplementation(async (path: string) => {
      if (path === "/api/v1/apps/games.flunk_out_frenzy") {
        return createAppDetail();
      }
      if (path === "/api/v1/apps/games.flunk_out_frenzy/bootstrap") {
        return createBootstrap();
      }
      throw new Error(`Unexpected apiGet path: ${path}`);
    });

    const wrapper = mount(AppHostView);
    await flushPromises();
    await flushPromises();

    expect(clientMocks.apiGet).toHaveBeenCalledWith("/api/v1/apps/games.flunk_out_frenzy");
    expect(clientMocks.apiGet).toHaveBeenCalledWith("/api/v1/apps/games.flunk_out_frenzy/bootstrap");
    expect(wrapper.text()).toContain("Flunk-Out Frenzy");
    expect(wrapper.find("[data-test='bootstrap-ready']").exists()).toBe(true);
    expect(wrapper.text()).not.toContain("AppDetailViewStub");

    wrapper.unmount();
  });

  it("shows the bespoke-app blocking message when a required view is missing", async () => {
    routeMocks.route.params.appId = "games.missing_shell";
    clientMocks.apiGet.mockResolvedValue(
      createAppDetail({
        app_id: "games.missing_shell",
        title: "Missing shell",
      }),
    );

    const wrapper = mount(AppHostView);
    await flushPromises();

    expect(wrapper.text()).toContain("kräver en anpassad vy");
    expect(wrapper.text()).not.toContain("AppDetailViewStub");

    wrapper.unmount();
  });
});
