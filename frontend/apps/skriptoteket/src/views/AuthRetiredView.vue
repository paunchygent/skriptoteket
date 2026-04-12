<script setup lang="ts">
/**
 * Retired public auth ceremony page.
 *
 * Purpose:
 *   Provide deliberate old-link behavior for auth flows now owned outside
 *   Skriptoteket.
 *
 * Relationships:
 *   - Used by legacy register, password, and verification routes.
 *   - The login route remains the only browser auth handoff in this SPA.
 */
</script>

<template>
  <div class="flex min-h-[60vh] items-center justify-center px-4 py-10">
    <section class="w-full max-w-md space-y-5 text-center">
      <p class="text-xs font-semibold tracking-[var(--huleedu-tracking-label)] text-navy/60 uppercase">
        Skriptoteket
      </p>
      <h1 class="font-serif text-4xl font-semibold tracking-[-0.03em] text-navy">
        Kontohanteringen har flyttat
      </h1>
      <p class="text-sm leading-6 text-navy/70">
        Registrering, verifiering och lösenord hanteras via inloggningen för
        Skriptoteket. Kontakta administratören för Skriptoteket om du saknar åtkomst.
      </p>
      <RouterLink
        class="btn-primary inline-block"
        :to="{ name: 'auth-login' }"
      >
        Fortsätt till inloggning
      </RouterLink>
    </section>
  </div>
</template>
