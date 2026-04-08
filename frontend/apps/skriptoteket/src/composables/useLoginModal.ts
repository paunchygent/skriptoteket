/**
 * Shared login-modal state.
 *
 * This composable keeps the active login modal redirect target in one place so
 * the current transitional modal-based auth entry can survive auth redirects
 * without losing router state.
 *
 * The planned forward direction is the dedicated `/auth/login` auth-entry page
 * tracked in ST-32-10 / PR-0242.
 */

import type { RouteLocationRaw } from "vue-router";
import { ref } from "vue";

const isOpen = ref(false);
const redirectTo = ref<RouteLocationRaw | null>(null);

export function useLoginModal() {
  function open(redirect?: RouteLocationRaw | null) {
    redirectTo.value = redirect ?? null;
    isOpen.value = true;
  }

  function close() {
    isOpen.value = false;
    redirectTo.value = null;
  }

  return {
    isOpen,
    redirectTo,
    open,
    close,
  };
}
