<script setup lang="ts">
import { computed, onMounted } from "vue";

import FavoritesSection from "../components/home/FavoritesSection.vue";
import HomeCreateDraftTool from "../components/home/HomeCreateDraftTool.vue";
import RecentToolsSection from "../components/home/RecentToolsSection.vue";
import SectionHeader from "../components/home/SectionHeader.vue";
import { IconArrow } from "../components/icons";
import { useHomeDashboard } from "../composables/home/useHomeDashboard";
import { useLoginModal } from "../composables/useLoginModal";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const loginModal = useLoginModal();
const {
  loadDashboard,
  dashboardError,
  favorites,
  recentNonFavorites,
  isToggling,
  handleFavoriteToggled,
  runsLoading,
  runsCount,
  currentMonth,
  runsInList,
  formatCount,
  toolsLoading,
  toolsTotal,
  toolsPublished,
  adminPendingReview,
  adminLoading,
} = useHomeDashboard();

const isAuthenticated = computed(() => auth.isAuthenticated);
const canSeeContributor = computed(() => auth.hasAtLeastRole("contributor"));
const canSeeAdmin = computed(() => auth.hasAtLeastRole("admin"));
const userName = computed(() => auth.displayName);

onMounted(async () => {
  if (!isAuthenticated.value) return;

  // Load all dashboard data in parallel
  await loadDashboard({
    isContributor: canSeeContributor.value,
    isAdmin: canSeeAdmin.value,
  });
});
</script>

<template>
  <div>
    <!-- ═══════════════════════════════════════════════════════════════════════
         PRE-LOGIN: Hero + Features
         ═══════════════════════════════════════════════════════════════════════ -->
    <template v-if="!isAuthenticated">
      <!-- Hero Section -->
      <section class="py-16 text-center">
        <h1
          class="font-serif text-5xl md:text-6xl font-bold text-navy tracking-tighter leading-tight"
        >
          Skriptoteket
        </h1>
        <p class="mt-2 text-xl text-navy/80 font-medium">
          Verktyg av lärare, för lärande
        </p>
        <p class="mt-4 text-lg text-navy/70 max-w-2xl mx-auto">
          Ta koden i egna händer. Beskriv din idé och vad du vill uppnå –
          kodassistenten omsätter den till ett fungerande skript och plattformen sköter resten.
        </p>
        <p class="mt-10">
          <button
            type="button"
            class="btn-primary px-8 py-4 text-sm font-semibold tracking-wide"
            @click="loginModal.open()"
          >
            Logga in
          </button>
        </p>
      </section>

      <!-- Features Section -->
      <section class="py-16 border-t border-navy/10">
        <div class="grid gap-12 md:grid-cols-2 lg:grid-cols-4 max-w-6xl mx-auto">
          <!-- Card 1: Skriv utan tekniska hinder -->
          <div class="relative">
            <div
              class="absolute -top-3 -left-2 w-8 h-8 bg-burgundy border border-navy flex items-center justify-center"
            >
              <span class="text-canvas font-bold text-sm">1</span>
            </div>
            <div class="pt-6 pl-5 border-l-2 border-navy min-h-[140px]">
              <h3 class="font-semibold text-navy text-lg">Skapa utan tekniska hinder</h3>
              <p class="mt-2 text-sm text-navy/70 leading-relaxed">
                Automatisera det som tar tid; skapa verktyg för dokumentation, lektionsplanering
                eller experimentera fritt – plattformen har inga åsikter om vad du behöver.
              </p>
            </div>
          </div>

          <!-- Card 2: Dela inom professionen -->
          <div class="relative">
            <div
              class="absolute -top-3 -left-2 w-8 h-8 bg-burgundy border border-navy flex items-center justify-center"
            >
              <span class="text-canvas font-bold text-sm">2</span>
            </div>
            <div class="pt-6 pl-5 border-l-2 border-navy min-h-[140px]">
              <h3 class="font-semibold text-navy text-lg">Dela med dina kollegor</h3>
              <p class="mt-2 text-sm text-navy/70 leading-relaxed">
                Publicera verktyg till kollegor och ta del av andras lösningar.
                Varje skript granskas innan publicering. Föreslå förbättringar, diskutera idéer –
                skripten växer tillsammans.
              </p>
            </div>
          </div>

          <!-- Card 3: Kör verktyg direkt -->
          <div class="relative">
            <div
              class="absolute -top-3 -left-2 w-8 h-8 bg-burgundy border border-navy flex items-center justify-center"
            >
              <span class="text-canvas font-bold text-sm">3</span>
            </div>
            <div class="pt-6 pl-5 border-l-2 border-navy min-h-[140px]">
              <h3 class="font-semibold text-navy text-lg">Kom igång direkt</h3>
              <p class="mt-2 text-sm text-navy/70 leading-relaxed">
                Du behöver inte kunna programmera. Har du en bra idé och kan beskriva den,
                hjälper kodassistenten dig att bygga helt fungerande appar och verktyg.
              </p>
            </div>
          </div>

          <!-- Card 4: GDPR-säkrad datahantering -->
          <div class="relative">
            <div
              class="absolute -top-3 -left-2 w-8 h-8 bg-burgundy border border-navy flex items-center justify-center"
            >
              <span class="text-canvas font-bold text-sm">4</span>
            </div>
            <div class="pt-6 pl-5 border-l-2 border-navy min-h-[140px]">
              <h3 class="font-semibold text-navy text-lg">GDPR-säkrad datahantering</h3>
              <p class="mt-2 text-sm text-navy/70 leading-relaxed">
                All databehandling sker lokalt och ingen data kan lämna servern utan aktivt samtycke.
                Datahanteringen följer GDPR, med tydliga regler för gallring.
              </p>
            </div>
          </div>
        </div>
      </section>
    </template>

    <!-- ═══════════════════════════════════════════════════════════════════════
         POST-LOGIN: Role-guarded Dashboard
         ═══════════════════════════════════════════════════════════════════════ -->
    <template v-else>
      <div class="max-w-4xl space-y-10">
        <!-- Error message -->
        <div
          v-if="dashboardError"
          class="p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
        >
          {{ dashboardError }}
        </div>

        <!-- Greeting -->
        <section class="space-y-1">
          <h1 class="font-serif text-3xl font-bold text-navy">
            Välkommen<template v-if="userName">, {{ userName }}</template>
          </h1>
          <p class="text-sm text-navy/70">Vad vill du göra?</p>
        </section>

        <!-- ═══════════════════════════════════════════════════════════════════
             PERSONALIZED SECTIONS: Favorites and Recent Tools
             ═══════════════════════════════════════════════════════════════════ -->
        <FavoritesSection
          :items="favorites"
          :is-toggling="isToggling"
          @favorite-toggled="handleFavoriteToggled"
        />

        <RecentToolsSection
          :items="recentNonFavorites"
          :is-toggling="isToggling"
          @favorite-toggled="handleFavoriteToggled"
        />

        <!-- ═══════════════════════════════════════════════════════════════════
             USER SECTION: All authenticated users
             ═══════════════════════════════════════════════════════════════════ -->
        <section class="space-y-4">
          <div class="grid gap-5 sm:grid-cols-2">
            <!-- Senaste körningar -->
            <RouterLink
              to="/my-runs"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Senaste körningar</span>
                <IconArrow
                  :size="18"
                  class="card-arrow"
                />
              </div>
              <div class="card-stats">
                <span
                  v-if="runsLoading"
                  class="text-navy/40"
                >...</span>
                <span
                  v-else
                  class="stat-number"
                >{{ formatCount(runsCount) }}</span>
                <span class="stat-label">körningar i {{ currentMonth }}</span>
              </div>
              <p class="card-description">
                Se de senaste {{ runsInList }} körningarna.
              </p>
            </RouterLink>

            <!-- Hitta verktyg -->
            <RouterLink
              to="/browse"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Hitta verktyg</span>
                <IconArrow
                  :size="18"
                  class="card-arrow"
                />
              </div>
              <p class="card-description mt-4">
                Sök och filtrera bland tillgängliga verktyg.
              </p>
            </RouterLink>
          </div>
        </section>

        <!-- ═══════════════════════════════════════════════════════════════════
             CONTRIBUTOR SECTION: contributor+ only
             ═══════════════════════════════════════════════════════════════════ -->
        <section
          v-if="canSeeContributor"
          class="space-y-4"
        >
          <SectionHeader title="Bidragsgivare" />
          <div class="grid gap-5 sm:grid-cols-2">
            <!-- Mina verktyg -->
            <RouterLink
              to="/my-tools"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Mina verktyg</span>
                <IconArrow
                  :size="18"
                  class="card-arrow"
                />
              </div>
              <div class="card-stats">
                <span
                  v-if="toolsLoading"
                  class="text-navy/40"
                >...</span>
                <template v-else>
                  <span class="stat-number">{{ toolsTotal }}</span>
                  <span class="stat-label">
                    verktyg
                    <span
                      v-if="toolsPublished > 0"
                      class="text-success"
                    >
                      ({{ toolsPublished }} publicerade)
                    </span>
                  </span>
                </template>
              </div>
              <p class="card-description">
                Hantera verktyg du ansvarar för.
              </p>
            </RouterLink>

            <!-- Föreslå verktyg -->
            <RouterLink
              to="/suggestions/new"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Föreslå verktyg</span>
                <IconArrow
                  :size="18"
                  class="card-arrow"
                />
              </div>
              <p class="card-description mt-4">
                Har du en idé? Skicka in ett förslag.
              </p>
            </RouterLink>
          </div>
        </section>

        <!-- ═══════════════════════════════════════════════════════════════════
             ADMIN SECTION: admin+ only
             ═══════════════════════════════════════════════════════════════════ -->
        <section
          v-if="canSeeAdmin"
          class="space-y-4"
        >
          <SectionHeader title="Administration" />
          <div class="grid gap-5 sm:grid-cols-2">
            <!-- Att granska -->
            <RouterLink
              to="/admin/tools"
              class="dashboard-card group"
              :class="{ 'border-warning': adminPendingReview > 0 }"
            >
              <div class="card-header">
                <span class="card-label">Att granska</span>
                <IconArrow
                  :size="18"
                  class="card-arrow"
                />
              </div>
              <div class="card-stats">
                <span
                  v-if="adminLoading"
                  class="text-navy/40"
                >...</span>
                <template v-else>
                  <span
                    class="stat-number"
                    :class="{ 'text-warning': adminPendingReview > 0 }"
                  >
                    {{ adminPendingReview }}
                  </span>
                  <span class="stat-label">väntar på granskning</span>
                </template>
              </div>
              <p class="card-description">
                Granska och publicera verktyg.
              </p>
            </RouterLink>

            <!-- Skapa nytt verktyg -->
            <HomeCreateDraftTool />
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* Dashboard card */
:deep(.dashboard-card) {
  display: block;
  padding: 1.25rem;
  border: 1px solid var(--color-navy);
  background-color: white;
  box-shadow: 4px 4px 0 0 var(--color-navy);
  text-decoration: none;
  transition: all 0.15s ease;
}

:deep(.dashboard-card:hover) {
  box-shadow: 6px 6px 0 0 var(--color-navy);
  transform: translate(-2px, -2px);
}

:deep(.card-header) {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

:deep(.card-label) {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-navy);
  transition: color 0.15s ease;
}

:deep(.dashboard-card:hover .card-label) {
  color: var(--color-burgundy);
}

:deep(.card-arrow) {
  color: var(--color-navy);
  flex-shrink: 0;
  transition: transform 0.15s ease, color 0.15s ease;
}

:deep(.dashboard-card:hover .card-arrow) {
  transform: translateX(4px);
  color: var(--color-burgundy);
}

:deep(.card-stats) {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

:deep(.stat-number) {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-navy);
  line-height: 1;
}

:deep(.stat-label) {
  font-size: 0.75rem;
  color: var(--color-navy);
  opacity: 0.6;
}

:deep(.card-description) {
  margin-top: 0.5rem;
  font-size: 0.8125rem;
  color: var(--color-navy);
  opacity: 0.6;
  line-height: 1.4;
}

/* Success color for published counts */
:deep(.text-success) {
  color: var(--huleedu-success);
}

/* Warning color for pending review */
:deep(.text-warning) {
  color: var(--huleedu-warning);
}

:deep(.border-warning) {
  border-color: var(--huleedu-warning);
}
</style>
