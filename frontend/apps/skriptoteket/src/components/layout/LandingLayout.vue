<script setup lang="ts">
import BrandLogo from "../brand/BrandLogo.vue";
import HelpButton from "../help/HelpButton.vue";
</script>

<template>
  <div class="landing-shell">
    <!-- Landing header: Logo only, no nav links -->
    <header class="landing-header">
      <div class="landing-header-inner">
        <RouterLink
          to="/"
          class="landing-brand"
        >
          <BrandLogo height="28px" />
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
  </div>
</template>

<style scoped>
.landing-shell {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
}

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
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  max-width: var(--huleedu-max-width-6xl);
  margin: 0 auto;
  padding: var(--huleedu-space-8) var(--huleedu-space-6);
  width: 100%;
}
</style>
