<script setup lang="ts">
import { computed } from "vue";

import { useLoginModal } from "../composables/useLoginModal";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const loginModal = useLoginModal();

const isAuthenticated = computed(() => auth.isAuthenticated);
const canSeeContributor = computed(() => auth.hasAtLeastRole("contributor"));
const userName = computed(() => {
  if (!auth.user) return null;
  return auth.user.email.split("@")[0];
});
</script>

<template>
  <div>
    <!-- Pre-login: Hero + Features -->
    <template v-if="!isAuthenticated">
      <!-- Hero Section -->
      <section class="py-12 text-center">
        <h1
          class="font-serif text-4xl md:text-5xl font-bold text-navy tracking-tighter leading-tight"
        >
          Verktyg för lärare
        </h1>
        <p class="mt-3 text-lg text-navy/70">
          Ladda upp en fil, välj ett verktyg, ladda ned resultatet.
        </p>
        <p class="mt-8">
          <button
            type="button"
            class="px-6 py-3 bg-navy text-canvas border border-navy shadow-brutal-sm font-semibold uppercase tracking-wide hover:bg-burgundy transition-colors"
            @click="loginModal.open()"
          >
            Logga in
          </button>
        </p>
      </section>

      <!-- Features Section -->
      <section class="py-12 border-t border-navy/10">
        <div class="grid gap-12 md:grid-cols-3 max-w-5xl mx-auto px-4">
          <!-- Card 1 -->
          <div class="relative">
            <div
              class="absolute -top-3 -left-2 w-8 h-8 bg-burgundy border border-navy flex items-center justify-center"
            >
              <span class="text-canvas font-bold text-sm">1</span>
            </div>
            <div class="pt-6 pl-5 border-l-2 border-navy min-h-[120px]">
              <h3 class="font-semibold text-navy text-lg">Dela och återanvänd</h3>
              <p class="mt-2 text-sm text-navy/70 leading-relaxed">
                Slipp skriva samma skript om och om igen. Hitta färdiga verktyg
                eller bidra med egna idéer.
              </p>
            </div>
          </div>

          <!-- Card 2 -->
          <div class="relative">
            <div
              class="absolute -top-3 -left-2 w-8 h-8 bg-burgundy border border-navy flex items-center justify-center"
            >
              <span class="text-canvas font-bold text-sm">2</span>
            </div>
            <div class="pt-6 pl-5 border-l-2 border-navy min-h-[120px]">
              <h3 class="font-semibold text-navy text-lg">Enkel uppladdning</h3>
              <p class="mt-2 text-sm text-navy/70 leading-relaxed">
                Ladda upp en fil, kör, ladda ner resultatet. Ingen IDE, ingen
                terminal, ingen installation.
              </p>
            </div>
          </div>

          <!-- Card 3 -->
          <div class="relative">
            <div
              class="absolute -top-3 -left-2 w-8 h-8 bg-burgundy border border-navy flex items-center justify-center"
            >
              <span class="text-canvas font-bold text-sm">3</span>
            </div>
            <div class="pt-6 pl-5 border-l-2 border-navy min-h-[120px]">
              <h3 class="font-semibold text-navy text-lg">Tryggt och lokalt</h3>
              <p class="mt-2 text-sm text-navy/70 leading-relaxed">
                Alla filer behandlas säkert på vår server. Verktyg granskas
                innan publicering.
              </p>
            </div>
          </div>
        </div>
      </section>
    </template>

    <!-- Post-login: Greeting + Quick Nav -->
    <template v-else>
      <div class="py-10 max-w-2xl">
        <!-- Greeting -->
        <section class="mb-10">
          <h1 class="text-3xl font-semibold text-navy">
            Välkommen<template v-if="userName">, {{ userName }}</template>
          </h1>
          <p class="mt-2 text-navy/60">Vad vill du göra?</p>
        </section>

        <!-- Quick Navigation -->
        <section>
          <div class="grid gap-5 sm:grid-cols-2">
            <!-- Hitta verktyg -->
            <RouterLink
              to="/browse"
              class="group block p-5 border border-navy bg-white shadow-brutal-sm hover:shadow-brutal hover:translate-x-[-2px] hover:translate-y-[-2px] transition-all"
            >
              <div class="flex items-start justify-between">
                <h3 class="font-semibold text-navy group-hover:text-burgundy">
                  Hitta verktyg
                </h3>
                <span class="text-burgundy text-lg">&rarr;</span>
              </div>
              <p class="mt-2 text-sm text-navy/60">
                Bläddra i katalogen och kör det du behöver.
              </p>
            </RouterLink>

            <!-- Mina körningar -->
            <RouterLink
              to="/my-runs"
              class="group block p-5 border border-navy bg-white shadow-brutal-sm hover:shadow-brutal hover:translate-x-[-2px] hover:translate-y-[-2px] transition-all"
            >
              <div class="flex items-start justify-between">
                <h3 class="font-semibold text-navy group-hover:text-burgundy">
                  Mina körningar
                </h3>
                <span class="text-burgundy text-lg">&rarr;</span>
              </div>
              <p class="mt-2 text-sm text-navy/60">
                Se resultat från tidigare körningar.
              </p>
            </RouterLink>

            <!-- Contributor+ cards -->
            <template v-if="canSeeContributor">
              <!-- Mina verktyg -->
              <RouterLink
                to="/my-tools"
                class="group block p-5 border border-navy bg-white shadow-brutal-sm hover:shadow-brutal hover:translate-x-[-2px] hover:translate-y-[-2px] transition-all"
              >
                <div class="flex items-start justify-between">
                  <h3 class="font-semibold text-navy group-hover:text-burgundy">
                    Mina verktyg
                  </h3>
                  <span class="text-burgundy text-lg">&rarr;</span>
                </div>
                <p class="mt-2 text-sm text-navy/60">
                  Hantera verktyg du ansvarar för.
                </p>
              </RouterLink>

              <!-- Föreslå verktyg -->
              <RouterLink
                to="/suggestions/new"
                class="group block p-5 border border-navy bg-white shadow-brutal-sm hover:shadow-brutal hover:translate-x-[-2px] hover:translate-y-[-2px] transition-all"
              >
                <div class="flex items-start justify-between">
                  <h3 class="font-semibold text-navy group-hover:text-burgundy">
                    Föreslå verktyg
                  </h3>
                  <span class="text-burgundy text-lg">&rarr;</span>
                </div>
                <p class="mt-2 text-sm text-navy/60">
                  Har du en idé? Skicka in ett förslag.
                </p>
              </RouterLink>
            </template>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>
