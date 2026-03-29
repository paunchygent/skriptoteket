/**
 * Help-panel state and contextual topic resolution.
 *
 * This module owns the global help drawer refs that are shared across the SPA.
 * Route-level help is resolved here, while nested shells like Klassrumskartan
 * can temporarily override the route via `helpContext` without introducing a
 * second help surface.
 */
import { ref } from "vue";
import type { RouteRecordName } from "vue-router";

export type HelpTopicId =
  | "home"
  | "login"
  | "browse_professions"
  | "browse_categories"
  | "browse_tools"
  | "tools_run"
  | "tools_result"
  | "my_tools"
  | "apps_detail"
  | "suggestions_new"
  | "admin_suggestions"
  | "admin_tools"
  | "admin_editor"
  | "planner_overview"
  | "planner_seating"
  | "planner_grouping"
  | "planner_rules";

const ROUTE_TOPIC_MAP: Record<string, HelpTopicId> = {
  home: "home",
  login: "login",
  browse: "browse_professions",
  "browse-categories": "browse_categories",
  "browse-tools": "browse_tools",
  "tool-run": "tools_run",
  "my-runs-detail": "tools_result",
  "my-tools": "my_tools",
  "app-detail": "apps_detail",
  "suggestion-new": "suggestions_new",
  "admin-suggestions": "admin_suggestions",
  "admin-suggestion-detail": "admin_suggestions",
  "admin-tools": "admin_tools",
  "admin-tool-editor": "admin_editor",
  "admin-tool-version-editor": "admin_editor",
};

/**
 * Context-based topic map.  When a component sets a help context string
 * (e.g. ``planner_seating``), this map takes priority over the route-
 * based resolution so that sub-views within a single route can show
 * mode-specific help content.
 */
const CONTEXT_TOPIC_MAP: Record<string, HelpTopicId> = {
  planner_overview: "planner_overview",
  planner_seating: "planner_seating",
  planner_grouping: "planner_grouping",
  planner_rules: "planner_rules",
};

/**
 * Resolve the help topic for the current route and optional context.
 * Context (set by sub-views like the planner) takes priority over route.
 */
export function resolveHelpTopic(
  routeName: RouteRecordName | null | undefined,
  context?: string | null,
): HelpTopicId | null {
  if (context) {
    const contextTopic = CONTEXT_TOPIC_MAP[context];
    if (contextTopic) {
      return contextTopic;
    }
  }
  if (!routeName) {
    return null;
  }
  const key = typeof routeName === "string" ? routeName : routeName.toString();
  return ROUTE_TOPIC_MAP[key] ?? null;
}

const isOpen = ref(false);
const activeTopic = ref<HelpTopicId | null>(null);
const helpContext = ref<string | null>(null);

export function useHelp() {
  function open(): void {
    isOpen.value = true;
  }

  function close(): void {
    isOpen.value = false;
  }

  function toggle(): void {
    isOpen.value = !isOpen.value;
  }

  function showIndex(): void {
    activeTopic.value = null;
  }

  function showTopic(topic: HelpTopicId): void {
    activeTopic.value = topic;
  }

  function setHelpContext(ctx: string | null): void {
    helpContext.value = ctx;
  }

  function clearHelpContext(expectedContext?: string | null): void {
    if (expectedContext && helpContext.value !== expectedContext) {
      return;
    }
    helpContext.value = null;
  }

  return {
    isOpen,
    activeTopic,
    helpContext,
    open,
    close,
    toggle,
    showIndex,
    showTopic,
    setHelpContext,
    clearHelpContext,
  };
}
