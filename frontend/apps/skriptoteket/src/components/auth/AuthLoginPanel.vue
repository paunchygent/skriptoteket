<script setup lang="ts">
/**
 * Hule Education browser-auth ceremony panel.
 *
 * Purpose:
 *   Provide a fallback link to the shared browser-navigable inloggning without
 *   collecting local Skriptoteket passwords.
 *
 * Relationships:
 *   - `AuthLoginView` provides the durable auth-entry route.
 *   - `sharedAuth.ts` owns the external auth ceremony URL contract.
 */

import { computed } from "vue";
import { useRoute } from "vue-router";

import { sharedAuthCeremonyUrl } from "../../api/sharedAuth";
import { readAuthContinuation } from "../../composables/auth/authEntryNavigation";

withDefaults(
  defineProps<{
    introCopy?: string;
    primaryLabel?: string;
    showAccountLinks?: boolean;
  }>(),
  {
    introCopy: "Om inloggningen inte öppnas automatiskt kan du öppna den igen här.",
    primaryLabel: "Öppna inloggningen",
    showAccountLinks: true,
  },
);

const route = useRoute();
const continuation = computed(() => readAuthContinuation(route.query, window.history.state));
const loginUrl = computed(() =>
  sharedAuthCeremonyUrl({
    nextPath: continuation.value.nextPath,
    origin: window.location.origin,
  }),
);
const registerUrl = computed(() =>
  sharedAuthCeremonyUrl({
    kind: "register",
    nextPath: continuation.value.nextPath,
    origin: window.location.origin,
  }),
);
const passwordResetUrl = computed(() =>
  sharedAuthCeremonyUrl({
    kind: "password-reset",
    nextPath: continuation.value.nextPath,
    origin: window.location.origin,
  }),
);
</script>

<template>
  <div class="border border-navy bg-canvas p-6 shadow-brutal md:p-8">
    <div class="space-y-4 text-sm leading-6 text-navy/75">
      <p>
        {{ introCopy }}
      </p>
      <p v-if="showAccountLinks">
        Saknar du konto?
        <a
          class="font-semibold text-navy underline decoration-navy/40 underline-offset-4"
          :href="registerUrl"
        >
          Skapa ett Skriptoteket-konto
        </a>.
      </p>
      <p v-if="showAccountLinks">
        <a
          class="font-semibold text-navy underline decoration-navy/40 underline-offset-4"
          :href="passwordResetUrl"
        >
          Glömt lösenordet?
        </a>
      </p>
    </div>

    <a
      class="btn-primary mt-6 block w-full text-center"
      :href="loginUrl"
    >
      {{ primaryLabel }}
    </a>
  </div>
</template>
