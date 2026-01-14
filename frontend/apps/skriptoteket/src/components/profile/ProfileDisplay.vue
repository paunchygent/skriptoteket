<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";
import type { RemoteFallbackPreference } from "../../stores/ai";
import ProfileAiSettingsPanel from "./ProfileAiSettingsPanel.vue";

type UserProfile = components["schemas"]["UserProfile"];

const props = defineProps<{
  profile: UserProfile | null;
  email: string;
  createdAt?: string;
  remoteFallbackPreference: RemoteFallbackPreference;
}>();

const emit = defineEmits<{
  edit: [section: "personal" | "email" | "password" | "ai"];
}>();

const initials = computed(() => {
  const first = props.profile?.first_name?.[0] ?? "";
  const last = props.profile?.last_name?.[0] ?? "";
  if (first || last) return (first + last).toUpperCase();
  return props.email[0]?.toUpperCase() ?? "?";
});

const displayName = computed(() => {
  if (props.profile?.display_name) return props.profile.display_name;
  if (props.profile?.first_name || props.profile?.last_name) {
    return `${props.profile.first_name ?? ""} ${props.profile.last_name ?? ""}`.trim();
  }
  return props.email.split("@")[0];
});

const localeLabel = computed(() => {
  const locale = props.profile?.locale ?? "sv-SE";
  return locale === "sv-SE" ? "Svenska" : "English";
});

const memberSince = computed(() => {
  if (!props.createdAt) return null;
  try {
    const date = new Date(props.createdAt);
    return date.toLocaleDateString("sv-SE", { year: "numeric", month: "long" });
  } catch {
    return null;
  }
});
</script>

<template>
  <div class="space-y-6">
    <!-- Header with avatar -->
    <div class="flex items-center gap-4">
      <div
        class="flex h-16 w-16 items-center justify-center border border-navy bg-navy text-2xl font-bold text-canvas shadow-brutal-sm"
      >
        {{ initials }}
      </div>
      <div class="space-y-1">
        <h2 class="text-xl font-semibold text-navy">{{ displayName }}</h2>
        <p class="text-sm text-navy">{{ email }}</p>
        <p
          v-if="memberSince"
          class="text-xs text-navy/70"
        >
          Medlem sedan {{ memberSince }}
        </p>
      </div>
    </div>

    <!-- Personal Information section -->
    <section class="border border-navy bg-white shadow-brutal-sm">
      <div class="flex items-center justify-between border-b border-navy px-4 py-3">
        <div>
          <h3 class="text-sm font-semibold text-navy">Personlig information</h3>
          <p class="text-xs text-navy/70">Namn och visningsnamn</p>
        </div>
        <button
          type="button"
          class="btn-ghost px-3 py-1 text-xs"
          @click="emit('edit', 'personal')"
        >
          Redigera
        </button>
      </div>

      <dl class="divide-y divide-navy/20 px-4 text-sm">
        <div class="grid gap-1 pt-3 pb-1 sm:gap-4 sm:items-baseline sm:grid-cols-[10rem_1fr]">
          <dt class="text-xs font-semibold uppercase tracking-wide text-navy/70">Förnamn</dt>
          <dd class="text-navy">{{ profile?.first_name || "–" }}</dd>
        </div>
        <div class="grid gap-1 pt-3 pb-1 sm:gap-4 sm:items-baseline sm:grid-cols-[10rem_1fr]">
          <dt class="text-xs font-semibold uppercase tracking-wide text-navy/70">Efternamn</dt>
          <dd class="text-navy">{{ profile?.last_name || "–" }}</dd>
        </div>
        <div class="grid gap-1 pt-3 pb-1 sm:gap-4 sm:items-baseline sm:grid-cols-[10rem_1fr]">
          <dt class="text-xs font-semibold uppercase tracking-wide text-navy/70">Visningsnamn</dt>
          <dd class="text-navy">{{ profile?.display_name || "–" }}</dd>
        </div>
        <div class="grid gap-1 pt-3 pb-1 sm:gap-4 sm:items-baseline sm:grid-cols-[10rem_1fr]">
          <dt class="text-xs font-semibold uppercase tracking-wide text-navy/70">Språk</dt>
          <dd class="text-navy">{{ localeLabel }}</dd>
        </div>
      </dl>
    </section>

    <!-- Email section -->
    <section class="border border-navy bg-white shadow-brutal-sm">
      <div class="flex items-center justify-between border-b border-navy px-4 py-3">
        <div>
          <h3 class="text-sm font-semibold text-navy">E-postadress</h3>
          <p class="text-xs text-navy/70">Din inloggningsadress</p>
        </div>
        <button
          type="button"
          class="btn-ghost px-3 py-1 text-xs"
          @click="emit('edit', 'email')"
        >
          Ändra
        </button>
      </div>

      <dl class="divide-y divide-navy/20 px-4 text-sm">
        <div class="grid gap-1 pt-3 pb-1 sm:gap-4 sm:items-baseline sm:grid-cols-[10rem_1fr]">
          <dt class="text-xs font-semibold uppercase tracking-wide text-navy/70">E-post</dt>
          <dd class="text-navy">{{ email }}</dd>
        </div>
      </dl>
    </section>

    <!-- Password section -->
    <section class="border border-navy bg-white shadow-brutal-sm">
      <div class="flex items-center justify-between border-b border-navy px-4 py-3">
        <div>
          <h3 class="text-sm font-semibold text-navy">Lösenord</h3>
          <p class="text-xs text-navy/70">Hantera ditt kontolösenord</p>
        </div>
        <button
          type="button"
          class="btn-ghost px-3 py-1 text-xs"
          @click="emit('edit', 'password')"
        >
          Ändra
        </button>
      </div>

      <dl class="divide-y divide-navy/20 px-4 text-sm">
        <div class="grid gap-1 pt-3 pb-1 sm:gap-4 sm:items-baseline sm:grid-cols-[10rem_1fr]">
          <dt class="text-xs font-semibold uppercase tracking-wide text-navy/70">Lösenord</dt>
          <dd class="text-navy">••••••••</dd>
        </div>
      </dl>
    </section>

    <ProfileAiSettingsPanel
      :remote-fallback-preference="props.remoteFallbackPreference"
      @edit="emit('edit', 'ai')"
    />
  </div>
</template>
