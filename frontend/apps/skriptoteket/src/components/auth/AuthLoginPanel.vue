<script setup lang="ts">
/**
 * Hule Education browser-auth ceremony panel.
 *
 * Purpose:
 *   Send signed-out teachers to the shared browser-navigable inloggning
 *   without collecting local Skriptoteket passwords.
 *
 * Relationships:
 *   - `AuthLoginView` provides the durable auth-entry route.
 *   - `sharedAuth.ts` owns the external auth ceremony URL contract.
 */

import { computed } from "vue";
import { useRoute } from "vue-router";

import { sharedAuthCeremonyUrl } from "../../api/sharedAuth";
import { readAuthContinuation } from "../../composables/auth/authEntryNavigation";

const route = useRoute();
const continuation = computed(() => readAuthContinuation(route.query, window.history.state));
const loginUrl = computed(() =>
  sharedAuthCeremonyUrl({
    nextPath: continuation.value.nextPath,
    origin: window.location.origin,
  }),
);
</script>

<template>
  <div class="border border-navy bg-canvas p-6 shadow-brutal md:p-8">
    <div class="space-y-4 text-sm leading-6 text-navy/75">
      <p>
        Logga in för att fortsätta till Skriptoteket.
      </p>
      <p>
        Saknar du åtkomst? Kontakta administratören för Skriptoteket.
      </p>
    </div>

    <a
      class="btn-primary mt-6 block w-full text-center"
      :href="loginUrl"
    >
      Fortsätt till inloggning
    </a>
  </div>
</template>
