/**
 * Curated app host view registry.
 *
 * This module maps curated app ids to the bespoke SPA views used by the
 * authenticated and public host routes so the host-layer authority stays
 * separate from app-specific presentation.
 */

import { defineAsyncComponent } from "vue";
import type { Component } from "vue";

export type CuratedAppHostMode = "authenticated" | "public";

type AsyncHostLoader = () => Promise<{ default: Component }>;

type CuratedAppHostViewConfig = {
  loader: AsyncHostLoader;
  props?: Record<string, unknown>;
};

type CuratedAppHostRegistration = {
  authenticated?: CuratedAppHostViewConfig;
  public?: CuratedAppHostViewConfig;
};

export type CuratedAppHostResolution = {
  component: Component;
  props: Record<string, unknown>;
};

const curatedAppHostRegistry: Record<string, CuratedAppHostRegistration> = {
  "chemistry.reagent_prep_chef": {
    authenticated: {
      loader: () => import("./apps/ReagentPrepChefView.vue"),
    },
  },
  "classroom.group-seating-studio": {
    authenticated: {
      loader: () => import("./apps/ClassroomPlannerEntryView.vue"),
      props: { hostMode: "authenticated" },
    },
    public: {
      loader: () => import("./apps/ClassroomPlannerEntryView.vue"),
      props: { hostMode: "public" },
    },
  },
  "documents.conversion_hub": {
    authenticated: {
      loader: () => import("./apps/ExamConverterAuthenticatedView.vue"),
    },
    public: {
      loader: () => import("./apps/ExamConverterPublicView.vue"),
    },
  },
  "games.flunk_out_frenzy": {
    authenticated: {
      loader: () => import("./apps/FlunkOutFrenzyView.vue"),
    },
  },
};

export function resolveCuratedAppHostView(
  appId: string,
  hostMode: CuratedAppHostMode,
): CuratedAppHostResolution | null {
  const registration = curatedAppHostRegistry[appId];
  if (!registration) {
    return null;
  }

  const viewConfig = hostMode === "public" ? registration.public : registration.authenticated;
  if (!viewConfig) {
    return null;
  }

  return {
    component: defineAsyncComponent(viewConfig.loader),
    props: viewConfig.props ?? {},
  };
}
