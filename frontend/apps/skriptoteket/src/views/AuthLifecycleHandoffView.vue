<script setup lang="ts">
/**
 * HuleEdu lifecycle ceremony handoff page.
 *
 * Purpose:
 *   Keep Skriptoteket's old registration, password, and verification URLs as
 *   browser handoff surfaces for the HuleEdu Gateway lifecycle ceremonies.
 *
 * Relationships:
 *   - `routes.ts` maps `/register`, `/forgot-password`, `/reset-password`, and
 *     `/verify-email` here.
 *   - `sharedAuth.ts` builds the provider-approved app/realm/return URLs.
 */

import { computed } from "vue";
import { useRoute } from "vue-router";

import { sharedAuthCeremonyUrl, type SharedAuthCeremonyKind } from "../api/sharedAuth";
import { readAuthContinuation } from "../composables/auth/authEntryNavigation";

type LifecycleRouteName = "register" | "forgot-password" | "reset-password" | "verify-email";

type LifecycleCopy = {
  kind: SharedAuthCeremonyKind;
  tokenAware: boolean;
  eyebrow: string;
  title: string;
  body: string;
  action: string;
};

const LIFECYCLE_COPY: Record<LifecycleRouteName, LifecycleCopy> = {
  register: {
    kind: "register",
    tokenAware: false,
    eyebrow: "Skriptoteket",
    title: "Skapa konto",
    body: "Fortsätt till Hule Education för att skapa ett Skriptoteket-konto.",
    action: "Fortsätt till registrering",
  },
  "forgot-password": {
    kind: "password-reset",
    tokenAware: false,
    eyebrow: "Skriptoteket",
    title: "Återställ lösenord",
    body: "Fortsätt till Hule Education för att återställa lösenordet för Skriptoteket.",
    action: "Fortsätt till återställning",
  },
  "reset-password": {
    kind: "password-reset",
    tokenAware: true,
    eyebrow: "Skriptoteket",
    title: "Välj nytt lösenord",
    body: "Fortsätt till Hule Education för att slutföra lösenordsbytet.",
    action: "Fortsätt till lösenordsbyte",
  },
  "verify-email": {
    kind: "email-verification",
    tokenAware: true,
    eyebrow: "Skriptoteket",
    title: "Verifiera e-post",
    body: "Fortsätt till Hule Education för att verifiera e-posten för Skriptoteket.",
    action: "Fortsätt till verifiering",
  },
};

const route = useRoute();

const lifecycleCopy = computed(() => {
  const routeName = route.name;
  if (typeof routeName === "string" && routeName in LIFECYCLE_COPY) {
    return LIFECYCLE_COPY[routeName as LifecycleRouteName];
  }

  return LIFECYCLE_COPY.register;
});

const continuation = computed(() => readAuthContinuation(route.query, window.history.state));
const routeToken = computed(() => {
  const token = route.query.token;
  return typeof token === "string" ? token : null;
});
const handoffUrl = computed(() =>
  sharedAuthCeremonyUrl({
    kind: lifecycleCopy.value.kind,
    nextPath: continuation.value.nextPath,
    origin: window.location.origin,
    token: lifecycleCopy.value.tokenAware ? routeToken.value : null,
  }),
);
const loginLocation = computed(() => ({
  name: "auth-login",
  query: continuation.value.nextPath ? { next: continuation.value.nextPath } : undefined,
}));
</script>

<template>
  <div class="flex min-h-[60vh] items-center justify-center px-4 py-10">
    <section class="w-full max-w-md space-y-5 text-center">
      <p
        class="text-xs font-semibold tracking-[var(--huleedu-tracking-label)] text-navy/60 uppercase"
      >
        {{ lifecycleCopy.eyebrow }}
      </p>
      <h1 class="font-serif text-4xl font-semibold tracking-[-0.03em] text-navy">
        {{ lifecycleCopy.title }}
      </h1>
      <p class="text-sm leading-6 text-navy/70">
        {{ lifecycleCopy.body }}
      </p>
      <a
        class="btn-primary inline-block"
        :href="handoffUrl"
      >
        {{ lifecycleCopy.action }}
      </a>
      <RouterLink
        class="block text-sm font-semibold text-navy underline decoration-navy/40 underline-offset-4"
        :to="loginLocation"
      >
        Gå till inloggning
      </RouterLink>
    </section>
  </div>
</template>
