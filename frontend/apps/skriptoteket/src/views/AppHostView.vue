<script setup lang="ts">
/**
 * Curated app host view.
 *
 * This view resolves a curated app deep link, fetches the generic app detail
 * metadata, and selects either a bespoke SPA surface or the generic fallback
 * view depending on the registered `ui_mode`.
 */

import { apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import AppDetailView from "./AppDetailView.vue";
import CuratedAppHostSurface from "./CuratedAppHostSurface.vue";
import { useCuratedAppHost } from "./useCuratedAppHost";

type AppDetailResponse = components["schemas"]["AppDetailResponse"];

const { errorMessage, hostView, hostViewProps, isLoading, shouldBlock } = useCuratedAppHost({
  hostMode: "authenticated",
  loadApp: async (appId) => {
    return apiGet<AppDetailResponse>(`/api/v1/apps/${encodeURIComponent(appId)}`);
  },
  getErrorMessage: (error) => {
    if (isApiError(error)) {
      return error.message;
    }
    if (error instanceof Error) {
      return error.message;
    }
    return "Det gick inte att ladda appen.";
  },
});
</script>

<template>
  <CuratedAppHostSurface
    :error-message="errorMessage"
    :fallback-view="AppDetailView"
    :fallback-view-props="{}"
    :host-view="hostView"
    :host-view-props="hostViewProps"
    :is-loading="isLoading"
    :should-block="shouldBlock"
  />
</template>
