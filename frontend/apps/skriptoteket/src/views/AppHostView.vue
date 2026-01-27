<script setup lang="ts">
import { computed, defineAsyncComponent, ref, shallowRef, watch } from "vue";
import type { Component } from "vue";
import { useRoute } from "vue-router";

import { apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import AppDetailView from "./AppDetailView.vue";

type AppDetailResponse = components["schemas"]["AppDetailResponse"];
type UiMode = "generic_ok" | "bespoke_required";

const route = useRoute();

const appId = computed(() => {
  const param = route.params.appId;
  return typeof param === "string" ? param : "";
});

const app = ref<AppDetailResponse | null>(null);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);

const bespokeView = shallowRef<Component | null>(null);

const bespokeRegistry: Record<string, () => Promise<{ default: Component }>> = {
  "chemistry.reagent_prep_chef": () => import("./apps/ReagentPrepChefView.vue"),
};

function resolveBespokeView(appIdValue: string): void {
  const loader = bespokeRegistry[appIdValue];
  if (!loader) {
    bespokeView.value = null;
    return;
  }
  bespokeView.value = defineAsyncComponent(loader);
}

const uiMode = computed<UiMode | null>(() => {
  const raw = (app.value as unknown as { ui_mode?: unknown } | null)?.ui_mode;
  if (raw === "generic_ok" || raw === "bespoke_required") return raw;
  return null;
});

const shouldBlock = computed(() => uiMode.value === "bespoke_required" && bespokeView.value === null);

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
    app.value = await apiGet<AppDetailResponse>(`/api/v1/apps/${encodeURIComponent(appId.value)}`);
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att ladda appen.";
    }
  } finally {
    isLoading.value = false;
  }
}

watch(
  appId,
  (value) => {
    resolveBespokeView(value);
    void load();
  },
  { immediate: true },
);
</script>

<template>
  <div
    v-if="isLoading || errorMessage || shouldBlock"
    class="max-w-3xl space-y-6"
  >
    <div
      v-if="isLoading"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-navy/70 text-sm"
    >
      Laddar...
    </div>

    <div
      v-else-if="errorMessage"
      class="p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
    >
      {{ errorMessage }}
    </div>

    <div
      v-else
      class="p-4 border border-burgundy bg-white shadow-brutal-sm space-y-2"
    >
      <p class="text-sm font-semibold text-burgundy">
        Den här appen kräver en anpassad vy som inte är installerad ännu.
      </p>
      <p class="text-sm text-navy/70">
        Kontakta admin eller uppdatera installationen för att få tillgång till appen.
      </p>
    </div>
  </div>

  <component
    :is="bespokeView"
    v-else-if="bespokeView"
  />

  <AppDetailView v-else />
</template>
