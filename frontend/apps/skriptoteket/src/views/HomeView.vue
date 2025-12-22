<script setup lang="ts"></script>

<template>
  <div class="max-w-2xl space-y-4">
    <h1 class="text-2xl font-semibold text-navy">
      Välkommen
    </h1>

    <div class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/80 space-y-2">
      <p>
        Skriptoteket håller på att flytta över till SPA.
      </p>
      <RouterLink
        to="/browse"
        class="inline-block underline text-burgundy hover:text-navy font-semibold"
      >
        Öppna katalogen →
      </RouterLink>
    </div>
  </div>
</template>
