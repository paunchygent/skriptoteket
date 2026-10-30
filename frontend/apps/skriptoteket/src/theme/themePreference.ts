/**
 * Purpose:
 *     Read, apply and store the theme choice shared by hule.education sites.
 *
 * Relationships:
 *     - theme-head.js applies the same huleedu_theme cookie before first paint.
 *     - themeSample.ts drives the choice through these functions.
 */

export type ThemeChoice = "light" | "dark" | "midnight" | "system";

const THEME_COOKIE_NAME = "huleedu_theme";
const THEME_COOKIE_MAX_AGE_SECONDS = 31536000;
const THEME_COOKIE_DOMAIN = ".hule.education";
const THEME_CHOICES: readonly ThemeChoice[] = ["light", "dark", "midnight", "system"];

function isThemeChoice(value: string): value is ThemeChoice {
  return (THEME_CHOICES as readonly string[]).includes(value);
}

function readCookieValue(name: string): string | null {
  const cookies = document.cookie ? document.cookie.split(";") : [];
  for (const cookie of cookies) {
    const separator = cookie.indexOf("=");
    if (separator === -1) {
      continue;
    }
    if (cookie.slice(0, separator).trim() === name) {
      return cookie.slice(separator + 1);
    }
  }
  return null;
}

export function readThemeChoice(): ThemeChoice {
  const stored = readCookieValue(THEME_COOKIE_NAME);
  return stored !== null && isThemeChoice(stored) ? stored : "system";
}

export function applyThemeChoice(choice: ThemeChoice): void {
  document.documentElement.dataset.theme = choice;
}

function themeCookieDomain(): string | null {
  const { hostname } = window.location;
  if (hostname === "hule.education" || hostname.endsWith(THEME_COOKIE_DOMAIN)) {
    return THEME_COOKIE_DOMAIN;
  }
  return null;
}

export function storeThemeChoice(choice: ThemeChoice): void {
  const attributes = [
    `${THEME_COOKIE_NAME}=${choice}`,
    "Path=/",
    `Max-Age=${THEME_COOKIE_MAX_AGE_SECONDS}`,
    "SameSite=Lax",
  ];
  if (window.location.protocol === "https:") {
    attributes.push("Secure");
  }
  const domain = themeCookieDomain();
  if (domain !== null) {
    attributes.push(`Domain=${domain}`);
  }
  document.cookie = attributes.join("; ");
  applyThemeChoice(choice);
}
