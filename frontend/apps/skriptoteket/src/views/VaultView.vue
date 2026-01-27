<script setup lang="ts">
import VaultPanel from "../components/vault/VaultPanel.vue";
</script>

<template>
  <div class="page">
    <header class="page-header max-w-[52rem]">
      <div class="max-w-[44rem]">
        <h1 class="page-title">Valv</h1>
        <p class="page-description">
          Dina sparade filer. Här kan du hitta, ta bort och återställa filer, samt se din kvot.
        </p>
      </div>
    </header>

    <VaultPanel mode="manage" />
  </div>
</template>
