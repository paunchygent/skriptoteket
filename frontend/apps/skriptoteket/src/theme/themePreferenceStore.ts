/**
 * Purpose:
 *     Feed the shared theme selector Skriptoteket's theme preference.
 *
 * Relationships:
 *     - Builds the one ThemePreferenceStore both top bars pass to
 *       UiThemeSelector, from the synced themePreference.ts functions.
 *     - The store writes the same `.hule.education` huleedu_theme cookie that
 *       theme-head.js applies before first paint.
 */

import type { ThemePreferenceStore } from "../components/ui/shared";

import {
  applyThemeChoice,
  readThemeChoice,
  storeThemeChoice,
} from "./themePreference";

export const themePreferenceStore: ThemePreferenceStore = {
  read: readThemeChoice,
  apply: applyThemeChoice,
  store: storeThemeChoice,
};
