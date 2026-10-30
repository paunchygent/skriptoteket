/**
 * Purpose:
 *     Mount the shared theme-sample page with Skriptoteket's design tokens.
 *
 * Relationships:
 *     - `theme-sample.html` loads this consumer-owned entry file.
 *     - `themeSample.ts` renders the page; `../styles/tokens.css` supplies the
 *       shared light and placeholder dark token values.
 */

import "../styles/tokens.css";
import { mountThemeSample } from "./themeSample";

const root = document.querySelector<HTMLElement>("#theme-sample");

if (root !== null) {
  mountThemeSample(root);
}
