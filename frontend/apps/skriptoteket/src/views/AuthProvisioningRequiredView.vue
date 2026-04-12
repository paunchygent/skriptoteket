<script setup lang="ts">
/**
 * Authenticated but unprovisioned Skriptoteket account page.
 *
 * Purpose:
 *   Give teachers a deliberate fail-closed state when the shared browser edge
 *   proves their session but Skriptoteket has no local app projection.
 *
 * Relationships:
 *   - Reached by the router guard when app-continuation returns the
 *     provisioning-required or linking-required reason.
 *   - Keeps provisioning separate from browser auth ceremony.
 */
</script>

<template>
  <div class="flex min-h-[60vh] items-center justify-center px-4 py-10">
    <section class="w-full max-w-lg space-y-5 text-center">
      <p class="text-xs font-semibold tracking-[var(--huleedu-tracking-label)] text-navy/60 uppercase">
        Skriptoteket
      </p>
      <h1 class="font-serif text-4xl font-semibold tracking-normal text-navy">
        Åtkomsten behöver aktiveras
      </h1>
      <p class="text-sm leading-6 text-navy/70">
        Du är inloggad, men ditt Skriptoteket-konto är ännu inte aktiverat.
        Kontakta administratören för Skriptoteket så hjälper vi dig vidare.
      </p>
      <RouterLink
        class="btn-primary inline-block"
        :to="{ name: 'auth-login' }"
      >
        Till inloggningen
      </RouterLink>
    </section>
  </div>
</template>
