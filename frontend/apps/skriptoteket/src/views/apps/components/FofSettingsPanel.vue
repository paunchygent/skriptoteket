<script setup lang="ts">
import type { FlunkOutFrenzyBootstrap } from "../flunkOutFrenzyTypes";

defineProps<{
  isSettingsOpen: boolean;
  bootstrap: FlunkOutFrenzyBootstrap;
  featureFlagRows: Array<{ label: string; value: string }>;
}>();

defineEmits<{
  (e: "close"): void;
}>();
</script>

<template>
  <Transition name="fof-settings">
    <div
      v-if="isSettingsOpen"
      class="fof-settings"
      @click.self="$emit('close')"
    >
      <aside
        data-test="settings-panel"
        class="fof-settings__panel"
      >
        <div class="fof-settings__header">
          <div>
            <p class="fof-settings__eyebrow">
              System & bootstrap
            </p>
            <h2 class="fof-settings__title">
              Spelinställningar
            </h2>
          </div>
          <button
            class="fof-action fof-action--ghost"
            type="button"
            @click="$emit('close')"
          >
            Stäng
          </button>
        </div>

        <dl class="fof-settings__meta">
          <div>
            <dt>Appversion</dt>
            <dd>{{ bootstrap.app_version }}</dd>
          </div>
          <div>
            <dt>Ruleset</dt>
            <dd data-test="ruleset-id">
              {{ bootstrap.ruleset_id }}
            </dd>
          </div>
        </dl>

        <dl class="fof-settings__flags">
          <div
            v-for="flag in featureFlagRows"
            :key="flag.label"
            class="fof-settings__flag"
          >
            <dt>{{ flag.label }}</dt>
            <dd>{{ flag.value }}</dd>
          </div>
        </dl>
      </aside>
    </div>
  </Transition>
</template>
