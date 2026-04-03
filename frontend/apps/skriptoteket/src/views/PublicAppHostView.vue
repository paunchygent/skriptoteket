<script setup lang="ts">
/**
 * Public curated app host view.
 *
 * This view powers the dedicated public curated-app entry route and only loads
 * public-safe bootstrap metadata from the parallel public API namespace.
 */

import { apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import CuratedAppHostSurface from "./CuratedAppHostSurface.vue";
import { useCuratedAppHost } from "./useCuratedAppHost";

type PublicAppBootstrapResponse = components["schemas"]["PublicAppBootstrapResponse"];

const { errorMessage, hostView, hostViewProps, isLoading, shouldBlock } = useCuratedAppHost({
  hostMode: "public",
  loadApp: async (appId) => {
    return apiGet<PublicAppBootstrapResponse>(`/api/v1/public/apps/${encodeURIComponent(appId)}`);
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
