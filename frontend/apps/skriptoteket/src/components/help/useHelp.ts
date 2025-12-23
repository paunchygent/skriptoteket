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
  | "admin_editor";

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

export function resolveHelpTopic(
  routeName: RouteRecordName | null | undefined,
): HelpTopicId | null {
  if (!routeName) {
    return null;
  }
  const key = typeof routeName === "string" ? routeName : routeName.toString();
  return ROUTE_TOPIC_MAP[key] ?? null;
}

const isOpen = ref(false);
const activeTopic = ref<HelpTopicId | null>(null);

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

  return {
    isOpen,
    activeTopic,
    open,
    close,
    toggle,
    showIndex,
    showTopic,
  };
}
