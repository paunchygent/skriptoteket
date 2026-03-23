/**
 * Flunk-Out Frenzy bootstrap loader.
 *
 * This composable owns the initial app-shell bootstrap fetch so the bespoke
 * view can stay rendering-focused while still consuming a typed backend
 * contract.
 */

import { onMounted, ref } from "vue";

import { apiGet, isApiError } from "../../api/client";
import type { FlunkOutFrenzyBootstrap } from "./flunkOutFrenzyTypes";

const BOOTSTRAP_PATH = "/api/v1/apps/games.flunk_out_frenzy/bootstrap";

export function useFlunkOutFrenzyBootstrap() {
  const bootstrap = ref<FlunkOutFrenzyBootstrap | null>(null);
  const bootstrapError = ref<string | null>(null);
  const isBootstrapping = ref(true);

  async function loadBootstrap(): Promise<void> {
    isBootstrapping.value = true;
    bootstrapError.value = null;

    try {
      bootstrap.value = await apiGet<FlunkOutFrenzyBootstrap>(BOOTSTRAP_PATH);
    } catch (error: unknown) {
      bootstrap.value = null;
      bootstrapError.value = isApiError(error)
        ? error.message
        : error instanceof Error
          ? error.message
          : "Kunde inte ladda Flunk-Out Frenzy.";
    } finally {
      isBootstrapping.value = false;
    }
  }

  onMounted(() => {
    void loadBootstrap();
  });

  return {
    bootstrap,
    bootstrapError,
    isBootstrapping,
    loadBootstrap,
  };
}
