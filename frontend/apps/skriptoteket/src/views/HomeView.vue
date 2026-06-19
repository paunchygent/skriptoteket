<script setup lang="ts">
/**
 * Auth-adaptive home surface.
 *
 * Relationships:
 * - keeps the signed-out landing hero focused on the public Klassrumskartan entry
 * - composes the approved authenticated app-first home surface with
 *   `HomeWorkAppsSection` and role-gated continuation ledgers
 */

import { computed, onMounted } from "vue";

import { sharedAuthCeremonyUrl } from "../api/sharedAuth";
import HomeWorkAppsSection from "../components/home/HomeWorkAppsSection.vue";
import { HOME_PRIMARY_WORK_APPS } from "../components/home/homeWorkApps";
import LandingAuthenticatedPreview from "../components/home/LandingAuthenticatedPreview.vue";
import LandingClassroomPreview from "../components/home/LandingClassroomPreview.vue";
import LandingFeaturedClassroom from "../components/home/LandingFeaturedClassroom.vue";
import { IconArrow } from "../components/icons";
import { useHomeDashboard } from "../composables/home/useHomeDashboard";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const publicClassroomPlannerPath = "/public/apps/classroom.group-seating-studio";
const { loadDashboard, dashboardError, adminPendingReview } = useHomeDashboard();

const isAuthenticated = computed(() => auth.isAuthenticated);
const canSeeContributor = computed(() => auth.hasAtLeastRole("contributor"));
const canSeeAdmin = computed(() => auth.hasAtLeastRole("admin"));
const userName = computed(() => auth.displayName);
const workApps = HOME_PRIMARY_WORK_APPS;

type SecondaryLedgerEntry = {
  title: string;
  to: string;
  description: string;
};

type SecondaryLedgerSection = {
  id: string;
  title: string;
  description?: string;
  entries: SecondaryLedgerEntry[];
};

const registerUrl = computed(() =>
  sharedAuthCeremonyUrl({
    kind: "register",
    nextPath: "/apps/classroom.group-seating-studio",
    origin: window.location.origin,
  }),
);
const contributorLedgerEntries = computed<SecondaryLedgerEntry[]>(() =>
  canSeeContributor.value
    ? [
        {
          title: "Mina verktyg",
          to: "/my-tools",
          description: "Hantera verktyg du ansvarar för.",
        },
        {
          title: "Föreslå verktyg",
          to: "/suggestions/new",
          description: "Har du en idé? Skicka in ett förslag.",
        },
      ]
    : [],
);
const adminLedgerEntries = computed<SecondaryLedgerEntry[]>(() =>
  canSeeAdmin.value
    ? [
        {
          title: "Att granska",
          to: "/admin/tools",
          description:
            adminPendingReview.value > 0
              ? `${adminPendingReview.value} verktyg väntar på granskning just nu.`
              : "Granska och publicera verktyg.",
        },
      ]
    : [],
);
const secondaryLedgerSections = computed<SecondaryLedgerSection[]>(() => {
  const sections: SecondaryLedgerSection[] = [
    {
      id: "materials",
      title: "Filer och katalog",
      entries: [
        {
          title: "Mina filer",
          to: "/vault",
          description: "Öppna sparade filer och exporter.",
        },
        {
          title: "Katalog",
          to: "/browse",
          description: "Sök och filtrera bland tillgängliga verktyg.",
        },
      ],
    },
  ];

  if (contributorLedgerEntries.value.length > 0) {
    sections.push({
      id: "contribution",
      title: "Skapa och utveckla",
      entries: contributorLedgerEntries.value,
    });
  }

  if (adminLedgerEntries.value.length > 0) {
    sections.push({
      id: "review",
      title: "Granskning",
      entries: adminLedgerEntries.value,
    });
  }

  return sections;
});

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
              <a
                :href="registerUrl"
                class="font-medium text-navy underline decoration-1 underline-offset-3 transition-colors hover:text-action focus-visible:outline focus-visible:outline-2 focus-visible:outline-action/40 focus-visible:outline-offset-2"
              >
                skapa ett konto
              </a>
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
        <div
          v-if="dashboardError"
          class="border border-error bg-panel px-4 py-3 text-sm text-error"
        >
          {{ dashboardError }}
        </div>

        <section class="max-w-[40rem] space-y-2">
          <h1 class="font-serif text-3xl font-semibold text-navy md:text-[2.75rem]">
            Välkommen<template v-if="userName">, {{ userName }}</template>
          </h1>
          <p class="text-sm leading-6 text-navy/70 md:text-base">
            Vad vill du göra?
          </p>
        </section>

        <HomeWorkAppsSection :apps="workApps" />

        <section
          data-testid="home-secondary-ledgers"
          class="grid gap-4 xl:grid-cols-2"
        >
          <section
            v-for="section in secondaryLedgerSections"
            :key="section.id"
            class="border border-navy bg-panel"
          >
            <header class="border-b border-navy/15 px-5 py-4">
              <h2 class="text-lg font-semibold text-navy">
                {{ section.title }}
              </h2>
              <p
                v-if="section.description"
                class="mt-1 text-sm leading-6 text-navy/70"
              >
                {{ section.description }}
              </p>
            </header>

            <ul class="divide-y divide-navy/15">
              <li
                v-for="entry in section.entries"
                :key="entry.title"
              >
                <RouterLink
                  :to="entry.to"
                  class="group flex items-start justify-between gap-4 px-5 py-4 no-underline transition-colors hover:bg-paper focus-visible:outline focus-visible:outline-2 focus-visible:outline-action/40 focus-visible:outline-offset-[-2px]"
                >
                  <div class="min-w-0">
                    <p class="text-base font-semibold text-navy">
                      {{ entry.title }}
                    </p>
                    <p class="mt-1 text-sm leading-6 text-navy/70">
                      {{ entry.description }}
                    </p>
                  </div>
                  <IconArrow
                    :size="16"
                    class="mt-1 shrink-0 text-navy/55 transition-transform duration-150 group-hover:translate-x-1 group-hover:text-action"
                    aria-hidden="true"
                  />
                </RouterLink>
              </li>
            </ul>
          </section>
        </section>
      </div>
    </template>
  </div>
</template>
