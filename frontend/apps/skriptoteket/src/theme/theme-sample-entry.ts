/**
 * Purpose:
 *     Mount the shared theme-sample page with Skriptoteket's theme preference.
 *
 * Relationships:
 *     - `theme-sample.html` loads this consumer-owned entry file.
 *     - `theme-sample.css` loads Tailwind and the adopted shared stylesheets in
 *       the package's documented order, without the app's own global layout.
 *     - `ThemeSamplePage` from the shared barrel renders the page; the page
 *       drives the choice through `themePreference.ts`, so it writes the same
 *       `.hule.education` cookie `theme-head.js` applies before first paint.
 *     - `public/logo-horizontal.svg` is the synced
 *       `skriptoteket-logo-horizontal` export; `BrandLogo.vue` reads the same
 *       file the same way.
 */

import { createApp } from "vue";

import logoArtwork from "/logo-horizontal.svg?raw";
import { ThemeSamplePage } from "../components/ui/shared";
import "./theme-sample.css";
import {
  applyThemeChoice,
  readThemeChoice,
  storeThemeChoice,
} from "./themePreference";

const root = document.querySelector<HTMLElement>("#theme-sample");

if (root !== null) {
  createApp(ThemeSamplePage, {
    themePreference: {
      read: readThemeChoice,
      apply: applyThemeChoice,
      store: storeThemeChoice,
    },
    skriptoteketLogoSvg: logoArtwork,
  }).mount(root);
}
