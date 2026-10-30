/**
 * Purpose:
 *     Render the minimal cross-site theme sample page.
 *
 * Relationships:
 *     - themePreference.ts reads and stores the cookie this page drives.
 *     - theme-sample.html mounts it through a consumer-owned entry file.
 */

import { readThemeChoice, storeThemeChoice, type ThemeChoice } from "./themePreference";

const PRIMARY_HOSTNAME = "hule.education";
const COMPANION_HOSTNAME = "skriptoteket.hule.education";
const THEME_SAMPLE_PATH = "/theme-sample";

const THEME_OPTIONS: readonly { choice: ThemeChoice; label: string }[] = [
  { choice: "light", label: "Ljust" },
  { choice: "midnight", label: "Midnatt" },
  { choice: "dark", label: "Bläck" },
  { choice: "system", label: "Följ enheten" },
];

function choiceLabel(choice: ThemeChoice): string {
  const option = THEME_OPTIONS.find((candidate) => candidate.choice === choice);
  return option?.label ?? "Följ enheten";
}

function companionSampleUrl(): string {
  const hostname = window.location.hostname;
  const host = hostname === PRIMARY_HOSTNAME ? COMPANION_HOSTNAME : PRIMARY_HOSTNAME;
  return `https://${host}${THEME_SAMPLE_PATH}`;
}

function stylePageShell(root: HTMLElement): void {
  root.style.padding = "24px";
  document.body.style.margin = "0";
  document.body.style.minHeight = "100vh";
  document.body.style.background = "var(--huleedu-paper)";
  document.body.style.color = "var(--huleedu-navy)";
  document.body.style.fontFamily = "var(--huleedu-font-sans)";
}

export function mountThemeSample(root: HTMLElement): void {
  stylePageShell(root);
  root.replaceChildren();

  const heading = document.createElement("h1");
  heading.textContent = "Tema";

  const buttonRow = document.createElement("div");
  buttonRow.style.display = "flex";
  buttonRow.style.gap = "8px";

  const status = document.createElement("p");
  const writeStatus = (choice: ThemeChoice): void => {
    status.textContent = `Lagrat val: ${choiceLabel(choice)}. Värd: ${window.location.hostname}`;
  };

  const buttons = THEME_OPTIONS.map(({ choice, label }) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.setAttribute("aria-pressed", String(choice === readThemeChoice()));
    buttonRow.append(button);
    return button;
  });

  buttons.forEach((button, index) => {
    button.addEventListener("click", () => {
      const choice = THEME_OPTIONS[index].choice;
      storeThemeChoice(choice);
      buttons.forEach((otherButton, otherIndex) => {
        otherButton.setAttribute("aria-pressed", String(otherIndex === index));
      });
      writeStatus(choice);
    });
  });

  const link = document.createElement("a");
  link.href = companionSampleUrl();
  link.textContent = `Öppna ${link.href}`;

  writeStatus(readThemeChoice());
  root.append(heading, buttonRow, status, link);
}
