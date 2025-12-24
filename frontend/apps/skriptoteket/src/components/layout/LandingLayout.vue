<script setup lang="ts">
import HelpButton from "../help/HelpButton.vue";
</script>

<template>
  <!-- Landing header: Logo only, no nav links -->
  <header class="landing-header">
    <div class="landing-header-inner">
      <RouterLink
        to="/"
        class="landing-brand"
      >
        Skriptoteket
      </RouterLink>
      <div class="landing-header-actions">
        <RouterLink
          to="/register"
          class="landing-register"
        >
          Skapa konto
        </RouterLink>
        <HelpButton />
      </div>
    </div>
  </header>

  <!-- Landing main content -->
  <main class="landing-main">
    <slot />
  </main>
</template>

<style scoped>
.landing-header {
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-navy);
  background-color: var(--huleedu-canvas);
}

.landing-header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--huleedu-space-4) var(--huleedu-space-4);
  gap: var(--huleedu-space-4);
}

.landing-brand {
  font-family: var(--huleedu-font-serif);
  font-weight: var(--huleedu-font-bold);
  font-size: var(--huleedu-text-xl);
  letter-spacing: var(--huleedu-tracking-tight);
  color: var(--huleedu-navy);
  text-decoration: none;
}

.landing-brand:hover {
  color: var(--huleedu-burgundy);
}

.landing-header-actions {
  display: flex;
  align-items: center;
  gap: var(--huleedu-space-3);
}

.landing-register {
  padding: var(--huleedu-space-2) var(--huleedu-space-3);
  border: var(--huleedu-border-width) solid var(--huleedu-navy);
  background-color: var(--huleedu-navy);
  color: var(--huleedu-canvas);
  font-size: var(--huleedu-text-xs);
  font-weight: var(--huleedu-font-semibold);
  letter-spacing: var(--huleedu-tracking-label);
  text-transform: uppercase;
  text-decoration: none;
  box-shadow: var(--huleedu-shadow-brutal-xs);
  transition: background-color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.landing-register:hover {
  background-color: var(--huleedu-burgundy);
}

.landing-main {
  max-width: var(--huleedu-max-width-6xl);
  margin: 0 auto;
  padding: var(--huleedu-space-8) var(--huleedu-space-6);
}
</style>
