<script setup lang="ts">
/**
 * Route recovery view.
 *
 * This view gives the SPA one calm recovery surface for malformed public app
 * paths and generic unmatched URLs while letting the existing landing or auth
 * shells stay responsible for the surrounding chrome.
 *
 * Relationships:
 * - Rendered by the explicit `/public/:appId` recovery route.
 * - Rendered by the final SPA catch-all route.
 */

import { computed } from "vue";

const props = defineProps<{
  missingAppsPrefixAppId?: string | null;
  missingAppsPrefix?: boolean;
}>();

const defaultPublicAppPath = "/public/apps/classroom.group-seating-studio";

const canonicalPublicPath = computed(() => {
  if (!props.missingAppsPrefixAppId) {
    return null;
  }
  return `/public/apps/${props.missingAppsPrefixAppId}`;
});

const isMalformedPublicRoute = computed(() => {
  return canonicalPublicPath.value !== null || props.missingAppsPrefix === true;
});

const primaryRecoveryPath = computed(() => {
  if (isMalformedPublicRoute.value) {
    return canonicalPublicPath.value ?? defaultPublicAppPath;
  }
  return "/";
});
</script>

<template>
  <section
    class="route-recovery"
    :data-test="isMalformedPublicRoute ? 'public-route-recovery' : 'not-found-recovery'"
  >
    <div class="route-recovery__eyebrow">
      {{ isMalformedPublicRoute ? "Publik länk" : "Hittar inte sidan" }}
    </div>

    <h1 class="route-recovery__title">
      {{
        isMalformedPublicRoute
          ? "Länken blev lite fel."
          : "Den sidan finns inte här."
      }}
    </h1>

    <p class="route-recovery__body">
      {{
        isMalformedPublicRoute
          ? "Publika applänkar behöver börja med /public/apps/. Öppna Klassrumskartan här i stället."
          : "Prova att gå tillbaka till startsidan eller öppna Klassrumskartan från den publika ingången."
      }}
    </p>

    <div class="route-recovery__actions">
      <RouterLink
        :to="primaryRecoveryPath"
        class="btn-cta"
        data-test="recovery-primary-link"
      >
        {{ isMalformedPublicRoute ? "Öppna rätt länk" : "Gå till startsidan" }}
      </RouterLink>

      <RouterLink
        :to="isMalformedPublicRoute ? '/' : defaultPublicAppPath"
        class="btn-ghost"
        data-test="recovery-secondary-link"
      >
        {{ isMalformedPublicRoute ? "Gå till startsidan" : "Öppna Klassrumskartan" }}
      </RouterLink>
    </div>

    <p
      v-if="canonicalPublicPath"
      class="route-recovery__hint"
      data-test="recovery-canonical-path"
    >
      Rätt väg: <code>{{ canonicalPublicPath }}</code>
    </p>
  </section>
</template>

<style scoped>
.route-recovery {
  display: grid;
  gap: var(--huleedu-space-5);
  max-width: 44rem;
  padding: clamp(var(--huleedu-space-6), 5vw, var(--huleedu-space-10));
  border: var(--huleedu-border-width) solid var(--huleedu-navy);
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--huleedu-sand) 45%, white) 0%, white 100%);
  box-shadow: var(--huleedu-shadow-brutal);
}

.route-recovery__eyebrow {
  font-size: var(--huleedu-text-xs);
  font-weight: var(--huleedu-font-semibold);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--huleedu-terracotta);
}

.route-recovery__title {
  font-size: clamp(2rem, 4vw, 3rem);
  line-height: 0.95;
  font-weight: var(--huleedu-font-black);
  letter-spacing: -0.04em;
  color: var(--huleedu-navy);
}

.route-recovery__body,
.route-recovery__hint {
  max-width: 36rem;
  font-size: var(--huleedu-text-base);
  line-height: 1.6;
  color: var(--huleedu-navy-70);
}

.route-recovery__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--huleedu-space-3);
}

.route-recovery__hint code {
  font-family: var(--huleedu-font-mono);
  font-size: 0.95em;
  color: var(--huleedu-navy);
}

@media (max-width: 40rem) {
  .route-recovery {
    padding: var(--huleedu-space-5);
  }

  .route-recovery__actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
