<script setup lang="ts">
import HelpButton from "../help/HelpButton.vue";

defineProps<{
  user: { email: string; role: string } | null;
  logoutInProgress: boolean;
}>();

const emit = defineEmits<{
  logout: [];
}>();

function onLogout(): void {
  emit("logout");
}
</script>

<template>
  <header class="top-user-bar">
    <div class="top-user-bar-left">
      <span class="user-info">
        {{ user?.email }}
        <span class="user-role">({{ user?.role }})</span>
      </span>
    </div>
    <div class="top-user-bar-right">
      <HelpButton />
      <span class="user-separator">|</span>
      <button
        type="button"
        class="logout-btn"
        :disabled="logoutInProgress"
        @click="onLogout"
      >
        {{ logoutInProgress ? "Loggar ut…" : "Logga ut" }}
      </button>
    </div>
  </header>
</template>

<style scoped>
.top-user-bar {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: var(--huleedu-space-3) var(--huleedu-space-6);
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-navy);
  background-color: var(--huleedu-canvas);
  color: var(--huleedu-navy);
  position: sticky;
  top: 0;
  z-index: 30;
}

@media (min-width: 768px) {
  .top-user-bar {
    display: flex;
  }
}

.top-user-bar-left {
  /* Future: breadcrumb */
}

.top-user-bar-right {
  display: flex;
  align-items: center;
  gap: var(--huleedu-space-3);
}

.user-info {
  font-size: var(--huleedu-text-xs);
  font-family: var(--huleedu-font-mono);
  color: var(--huleedu-navy);
}

.user-role {
  opacity: 0.6;
}

.user-separator {
  color: var(--huleedu-navy);
  opacity: 0.3;
}

.logout-btn {
  padding: var(--huleedu-space-1) var(--huleedu-space-2);
  border: none;
  background: none;
  font-size: var(--huleedu-text-xs);
  font-weight: var(--huleedu-font-semibold);
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
  color: var(--huleedu-navy);
  cursor: pointer;
  transition: color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.logout-btn:hover {
  color: var(--huleedu-burgundy);
}

.logout-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
