<script setup lang="ts">
/**
 * Auth-adaptive home surface.
 *
 * This view keeps the signed-out landing hero focused on the public
 * Klassrumskartan entry while authenticated users continue into the existing
 * role-aware dashboard.
 */

import { computed, onMounted } from "vue";

import FavoritesSection from "../components/home/FavoritesSection.vue";
import HomeCreateDraftTool from "../components/home/HomeCreateDraftTool.vue";
import LandingAuthenticatedPreview from "../components/home/LandingAuthenticatedPreview.vue";
import LandingClassroomPreview from "../components/home/LandingClassroomPreview.vue";
import LandingFeaturedClassroom from "../components/home/LandingFeaturedClassroom.vue";
import RecentToolsSection from "../components/home/RecentToolsSection.vue";
import { IconArrow } from "../components/icons";
import { useHomeDashboard } from "../composables/home/useHomeDashboard";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const publicClassroomPlannerPath = "/public/apps/classroom.group-seating-studio";
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
      <section class="border-b border-navy py-12 md:py-16 lg:py-20">
        <div class="grid items-start gap-10 lg:grid-cols-[minmax(0,7fr)_minmax(18rem,5fr)] lg:gap-16">
          <div class="max-w-[40rem]">
            <h1
              class="max-w-[14ch] font-serif text-5xl leading-[0.98] font-semibold tracking-[-0.03em] text-navy md:text-6xl lg:text-[4.25rem]"
            >
              Lektionsplanera direkt i webbläsaren.
            </h1>
            <div
              class="mt-8 h-[2px] w-24 bg-navy"
              aria-hidden="true"
            />
            <p class="mt-6 max-w-[42ch] text-lg leading-8 text-navy md:text-[1.15rem]">
              Klassrumskartan är en av Skriptotekets appar. Den är öppen för alla.
              Du behöver inget konto för att komma igång.
            </p>

            <div class="mt-8">
              <RouterLink
                :to="publicClassroomPlannerPath"
                class="btn-cta group gap-3 px-6 py-4 text-sm no-underline md:px-7"
              >
                Öppna Klassrumskartan
                <IconArrow
                  :size="18"
                  class="transition-transform duration-150 group-hover:translate-x-1"
                />
              </RouterLink>
            </div>

            <p class="mt-5 text-sm leading-6 text-navy/70">
              eller
              <RouterLink
                to="/register"
                class="font-medium text-navy underline decoration-1 underline-offset-3 transition-colors hover:text-burgundy focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2"
              >
                skapa ett konto
              </RouterLink>
              för att spara ditt arbete.
            </p>
          </div>

          <LandingClassroomPreview />
        </div>
      </section>

      <LandingFeaturedClassroom />
      <LandingAuthenticatedPreview />
    </template>

    <!-- ═══════════════════════════════════════════════════════════════════════
         POST-LOGIN: Role-guarded Dashboard
         ═══════════════════════════════════════════════════════════════════════ -->
    <template v-else>
      <div class="space-y-10">
        <!-- Error message -->
        <div
          v-if="dashboardError"
          class="p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
        >
          {{ dashboardError }}
        </div>

        <!-- Greeting -->
        <section class="space-y-1 max-w-[40rem]">
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
             UNIFIED ACTION CARDS GRID
             All cards flow together in one grid. Section markers span full row.
             ═══════════════════════════════════════════════════════════════════ -->
        <section class="expand-left-64">
          <div class="action-cards-grid">
            <!-- USER CARDS: All authenticated users -->
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

            <!-- CONTRIBUTOR CARDS -->
            <template v-if="canSeeContributor">
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

              <RouterLink
                to="/editor"
                class="dashboard-card group"
              >
                <div class="card-header">
                  <span class="card-label">Kodredigerare</span>
                  <IconArrow
                    :size="18"
                    class="card-arrow"
                  />
                </div>
                <p class="card-description mt-4">
                  Fortsätt där du slutade eller välj ett verktyg att redigera.
                </p>
              </RouterLink>

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
            </template>

            <!-- ADMIN CARDS -->
            <template v-if="canSeeAdmin">
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

              <HomeCreateDraftTool />
            </template>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* Unified action cards grid - all cards flow together */
.action-cards-grid {
  display: grid;
  gap: 1.25rem;
  grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
}

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
