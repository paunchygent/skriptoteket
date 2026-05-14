<script setup lang="ts">
/**
 * Public curated app host view.
 *
 * This view powers the dedicated public curated-app entry route and only loads
 * public-safe bootstrap metadata from the parallel public API namespace.
 */

import { isApiError, publicApiGet } from "../api/client";
import type { components } from "../api/openapi";
import CuratedAppHostSurface from "./CuratedAppHostSurface.vue";
import { useCuratedAppHost, type CuratedAppRouteContext } from "./useCuratedAppHost";

type PublicAppBootstrapResponse = components["schemas"]["PublicAppBootstrapResponse"];
type PublicAppCapabilityBootstrapResponse =
  components["schemas"]["PublicAppCapabilityBootstrapResponse"];

function buildPublicBootstrapPath(appId: string, context: CuratedAppRouteContext): string {
  const encodedAppId = encodeURIComponent(appId);
  if (context.publicCapabilitySlug) {
    return `/api/v1/public/apps/${encodedAppId}/${encodeURIComponent(context.publicCapabilitySlug)}`;
  }
  return `/api/v1/public/apps/${encodedAppId}`;
}

const { errorMessage, hostView, hostViewProps, isLoading, shouldBlock } = useCuratedAppHost({
  hostMode: "public",
  loadApp: async (appId, context) => {
    return publicApiGet<PublicAppBootstrapResponse | PublicAppCapabilityBootstrapResponse>(
      buildPublicBootstrapPath(appId, context),
    );
  },
  getErrorMessage: (error) => {
    if (isApiError(error)) {
      return error.message;
    }
    if (error instanceof Error) {
      return error.message;
    }
    return "Det gick inte att ladda den publika appvyn.";
  },
});
</script>

<template>
  <CuratedAppHostSurface
    :error-message="errorMessage"
    :fallback-view="null"
    :fallback-view-props="{}"
    :host-view="hostView"
    :host-view-props="hostViewProps"
    :is-loading="isLoading"
    :should-block="shouldBlock"
  />
</template>
