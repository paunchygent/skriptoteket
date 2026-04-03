/**
 * Shared curated-app host loader state.
 *
 * This composable keeps authenticated and public host routes aligned on route
 * param parsing, metadata loading, and bespoke shell resolution while letting
 * each route choose its own bootstrap endpoint and authority model.
 */

import { computed, ref, shallowRef, watch } from "vue";
import type { Component } from "vue";
import { useRoute } from "vue-router";

import {
  resolveCuratedAppHostView,
  type CuratedAppHostMode,
} from "./curatedAppHostRegistry";

export type CuratedAppHostMetadata = {
  app_id: string;
  ui_mode: "generic_ok" | "bespoke_required";
};

type UseCuratedAppHostOptions<TApp extends CuratedAppHostMetadata> = {
  hostMode: CuratedAppHostMode;
  loadApp: (appId: string) => Promise<TApp>;
  getErrorMessage: (error: unknown) => string;
};

export function useCuratedAppHost<TApp extends CuratedAppHostMetadata>(
  options: UseCuratedAppHostOptions<TApp>,
) {
  const route = useRoute();

  const appId = computed(() => {
    const param = route.params.appId;
    return typeof param === "string" ? param : "";
  });

  const app = ref<TApp | null>(null);
  const isLoading = ref(true);
  const errorMessage = ref<string | null>(null);
  const hostView = shallowRef<Component | null>(null);
  const hostViewProps = ref<Record<string, unknown>>({});

  const shouldBlock = computed(() => {
    return app.value?.ui_mode === "bespoke_required" && hostView.value === null;
  });

  function resolveHostView(appIdValue: string): void {
    const resolution = resolveCuratedAppHostView(appIdValue, options.hostMode);
    hostView.value = resolution?.component ?? null;
    hostViewProps.value = resolution?.props ?? {};
  }

  async function load(): Promise<void> {
    if (!appId.value) {
      errorMessage.value = "Saknar app-id i länken.";
      isLoading.value = false;
      return;
    }

    isLoading.value = true;
    errorMessage.value = null;
    app.value = null;

    try {
      app.value = await options.loadApp(appId.value);
    } catch (error: unknown) {
      errorMessage.value = options.getErrorMessage(error);
    } finally {
      isLoading.value = false;
    }
  }

  watch(
    appId,
    (value) => {
      resolveHostView(value);
      void load();
    },
    { immediate: true },
  );

  return {
    app,
    appId,
    errorMessage,
    hostView,
    hostViewProps,
    isLoading,
    shouldBlock,
  };
}
