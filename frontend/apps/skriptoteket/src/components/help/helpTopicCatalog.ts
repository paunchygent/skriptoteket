/**
 * Help topic catalog and route coverage contract.
 *
 * This module is the single SPA-side source for help topic identifiers, route
 * mappings, planner context overrides, and role-aware help-index entries.
 */
import type { RouteRecordName } from "vue-router";

export type HelpTopicId =
  | "home"
  | "login"
  | "auth_lifecycle"
  | "provisioning_required"
  | "browse_professions"
  | "browse_categories"
  | "browse_tools"
  | "tools_run"
  | "my_runs"
  | "tools_result"
  | "vault"
  | "profile"
  | "my_tools"
  | "editor_hub"
  | "apps_detail"
  | "conversion_tools"
  | "suggestions_new"
  | "admin_suggestions"
  | "admin_tools"
  | "admin_editor"
  | "admin_users"
  | "forbidden"
  | "route_recovery"
  | "planner_overview"
  | "planner_seating"
  | "planner_grouping"
  | "planner_rules";

export type HelpIndexSection = "logged_out" | "starter" | "contributor" | "admin" | "superuser";

export type HelpIndexItem = {
  topic: HelpTopicId;
  title: string;
  description?: string;
};

type HelpTopicCatalogEntry = HelpIndexItem & {
  routes?: readonly string[];
  contexts?: readonly string[];
  indexSection?: HelpIndexSection;
};

export const HELP_TOPIC_CATALOG: readonly HelpTopicCatalogEntry[] = [
  {
    topic: "login",
    title: "Logga in",
    description: "Fortsätt via HuleEdu.",
    routes: ["auth-login", "auth-callback"],
    indexSection: "logged_out",
  },
  {
    topic: "auth_lifecycle",
    title: "Konto och lösenord",
    description: "Skapa konto, byt lösenord och bekräfta e-post.",
    routes: ["register", "forgot-password", "reset-password", "verify-email"],
    indexSection: "logged_out",
  },
  {
    topic: "provisioning_required",
    title: "Kontot behöver aktiveras",
    routes: ["auth-provisioning-required"],
  },
  {
    topic: "home",
    title: "Start",
    description: "Din utgångspunkt i Skriptoteket.",
    routes: ["home"],
    indexSection: "starter",
  },
  {
    topic: "browse_professions",
    title: "Katalog",
    description: "Hitta verktyg via yrke och kategori.",
    routes: ["browse", "browse-professions"],
    indexSection: "starter",
  },
  {
    topic: "browse_categories",
    title: "Katalog: kategorier",
    routes: ["browse-categories"],
  },
  {
    topic: "browse_tools",
    title: "Katalog: verktyg och appar",
    routes: ["browse-tools"],
  },
  {
    topic: "tools_run",
    title: "Kör ett verktyg",
    description: "Fyll i fält, ladda upp filer och starta.",
    routes: ["tool-run"],
    indexSection: "starter",
  },
  {
    topic: "my_runs",
    title: "Mina körningar",
    description: "Tidigare körningar och deras status.",
    routes: ["my-runs"],
  },
  {
    topic: "tools_result",
    title: "Körningsresultat",
    routes: ["my-runs-detail"],
  },
  {
    topic: "vault",
    title: "Mina filer",
    description: "Sparade filer och exporter.",
    routes: ["vault"],
    indexSection: "starter",
  },
  {
    topic: "profile",
    title: "Min profil",
    description: "Konto, roller och inställningar.",
    routes: ["profile"],
    indexSection: "starter",
  },
  {
    topic: "my_tools",
    title: "Mina verktyg",
    description: "Verktyg du ansvarar för.",
    routes: ["my-tools"],
    indexSection: "contributor",
  },
  {
    topic: "editor_hub",
    title: "Kodredigerare",
    description: "Starta eller fortsätt bygga verktyg.",
    routes: ["editor-hub"],
    indexSection: "contributor",
  },
  {
    topic: "suggestions_new",
    title: "Föreslå verktyg",
    description: "Beskriv ett verktyg du saknar.",
    routes: ["suggestion-new"],
    indexSection: "starter",
  },
  {
    topic: "apps_detail",
    title: "App",
    description: "Större arbetsytor med flera steg.",
    routes: ["app-detail", "public-app-detail", "public-app-capability-detail"],
  },
  {
    topic: "conversion_tools",
    title: "Konvertera material",
    description: "Omvandla prov, ljud och dokument.",
    routes: [
      "exam-converter-authenticated",
      "audio-transcription-authenticated",
      "document-converter-authenticated",
    ],
  },
  {
    topic: "admin_suggestions",
    title: "Förslag",
    description: "Granska och fatta beslut.",
    routes: ["admin-suggestions", "admin-suggestion-detail"],
    indexSection: "admin",
  },
  {
    topic: "admin_tools",
    title: "Hantera verktyg",
    description: "Publicera, avpublicera och redigera.",
    routes: ["admin-tools"],
    indexSection: "admin",
  },
  {
    topic: "admin_editor",
    title: "Redigera verktyg",
    description: "Bygg, testkör och publicera versioner.",
    routes: ["admin-tool-editor", "admin-tool-version-editor"],
    indexSection: "admin",
  },
  {
    topic: "admin_users",
    title: "Administrera användare",
    description: "Hantera lokala roller.",
    routes: ["admin-users", "admin-user-detail"],
    indexSection: "superuser",
  },
  {
    topic: "forbidden",
    title: "Åtkomst saknas",
    routes: ["forbidden"],
  },
  {
    topic: "route_recovery",
    title: "Sidan hittades inte",
    routes: ["not-found", "public-app-route-recovery"],
  },
  {
    topic: "planner_overview",
    title: "Översikt: klass och klassrum",
    contexts: ["planner_overview"],
  },
  {
    topic: "planner_grouping",
    title: "Grupper",
    contexts: ["planner_grouping"],
  },
  {
    topic: "planner_seating",
    title: "Sittplatser",
    contexts: ["planner_seating"],
  },
  {
    topic: "planner_rules",
    title: "Regler och sammanfattning",
    contexts: ["planner_rules"],
  },
];

export const HELP_ROUTE_TOPIC_BY_ROUTE_NAME: Readonly<Record<string, HelpTopicId>> = Object.freeze(
  Object.fromEntries(
    HELP_TOPIC_CATALOG.flatMap((entry) =>
      (entry.routes ?? []).map((routeName) => [routeName, entry.topic]),
    ),
  ) as Record<string, HelpTopicId>,
);

const HELP_CONTEXT_TOPIC_BY_CONTEXT: Readonly<Record<string, HelpTopicId>> = Object.freeze(
  Object.fromEntries(
    HELP_TOPIC_CATALOG.flatMap((entry) =>
      (entry.contexts ?? []).map((context) => [context, entry.topic]),
    ),
  ) as Record<string, HelpTopicId>,
);

export function getHelpIndexItems(section: HelpIndexSection): HelpIndexItem[] {
  return HELP_TOPIC_CATALOG
    .filter((entry) => entry.indexSection === section)
    .map((entry) => ({
      topic: entry.topic,
      title: entry.title,
      description: entry.description,
    }));
}

/**
 * Resolve the help topic for the current route and optional context.
 * Context set by nested workspaces takes priority over route-level topics.
 */
export function resolveHelpTopic(
  routeName: RouteRecordName | null | undefined,
  context?: string | null,
): HelpTopicId | null {
  if (context) {
    const contextTopic = HELP_CONTEXT_TOPIC_BY_CONTEXT[context];
    if (contextTopic) {
      return contextTopic;
    }
  }

  if (!routeName) {
    return null;
  }

  const key = typeof routeName === "string" ? routeName : routeName.toString();
  return HELP_ROUTE_TOPIC_BY_ROUTE_NAME[key] ?? null;
}
