<script setup lang="ts">
// No props or emits - simple layout wrapper
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

.landing-main {
  max-width: var(--huleedu-max-width-6xl);
  margin: 0 auto;
  padding: var(--huleedu-space-8) var(--huleedu-space-6);
}
</style>
