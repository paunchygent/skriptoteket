/**
 * Generate the HuleEdu semantic-family fallback icon research board.
 *
 * Relationships:
 * - Uses the public Iconify API as an inventory/search layer only.
 * - Compares Lucide Lab and Tabler candidates for education-facing semantics.
 * - Produces a static HTML artifact linked from the ST-29-12 inventory bundle.
 */

import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const generatorDir = dirname(fileURLToPath(import.meta.url));
const prefixes = [
  { id: "lucide-lab", label: "Lucide Lab", role: "Lucide-family first fallback" },
  { id: "tabler", label: "Tabler Icons", role: "Broader stroke-compatible fallback" },
];

const irrelevantIconTokens = new Set(["bottle", "card", "penguin", "pineapple", "shirt", "slot", "trousers"]);

const families = [
  ["classroom", ["classroom", "school", "chalkboard", "presentation"]],
  ["maps", ["map", "map-pin", "route", "navigation", "location"]],
  ["proximity-distance", ["near", "close", "distance", "short-distance", "ruler", "spacing", "minimize", "magnet"]],
  ["groups", ["group", "users", "team", "network", "cluster"]],
  ["cooperation", ["cooperation", "collaboration", "handshake", "helping", "together"]],
  ["ideation", ["idea", "brainstorm", "bulb", "spark", "mind"]],
  ["teacher", ["teacher", "school", "presentation", "user-star", "chalkboard"]],
  ["hand-in", ["hand-in", "submit", "upload", "turn in", "assignment"]],
  ["bench", ["bench", "desk", "table", "seat", "chair"]],
  ["homework", ["homework", "assignment", "book", "notebook", "pencil"]],
  ["exam", ["exam", "test", "certificate", "clipboard-check", "file-check"]],
  ["grade", ["grade", "score", "star", "award", "chart"]],
  ["learning", ["learning", "book", "brain", "graduation", "school"]],
  ["assessment", ["assessment", "rubric", "checklist", "clipboard", "chart"]],
  ["AI", ["sparkles", "bot", "robot", "brain", "circuit", "cpu"]],
  ["language", ["language", "translate", "letters", "text", "speech"]],
  ["writing", ["writing", "pencil", "pen-line", "edit", "notebook"]],
];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Iconify request failed ${response.status}: ${url}`);
  }
  return response.json();
}

async function fetchSvg(iconId) {
  const response = await fetch(`https://api.iconify.design/${iconId}.svg?height=24`);
  if (!response.ok) {
    return "";
  }
  return (await response.text()).replace(/<svg /, '<svg aria-hidden="true" ');
}

function scoreIcon(name, query) {
  if (name.includes("-off") || name.includes("filled") || name.includes("fill")) {
    return -Infinity;
  }
  let score = 0;
  const namePart = name.split(":").at(-1) ?? name;
  const iconTokens = namePart.toLowerCase().split(/[-_\s]+/);
  if (iconTokens.some((token) => irrelevantIconTokens.has(token))) {
    return -Infinity;
  }
  const queryTokens = query
    .split(/[-_\s]+/)
    .map((token) => token.toLowerCase())
    .filter(Boolean);
  for (const token of queryTokens) {
    if (iconTokens.includes(token)) {
      score += 8;
    }
  }
  const queryPhrase = queryTokens.join("-");
  if (queryPhrase && namePart.toLowerCase() === queryPhrase) {
    score += 12;
  }
  if (queryTokens.length > 1) {
    for (let index = 0; index <= iconTokens.length - queryTokens.length; index += 1) {
      const candidate = iconTokens.slice(index, index + queryTokens.length).join("-");
      if (candidate === queryPhrase) {
        score += 6;
        break;
      }
    }
  }
  return score;
}

async function collectFamily(prefix, familyId, queries) {
  const scored = new Map();
  for (const query of queries) {
    const params = new URLSearchParams({ query, prefix, limit: "64" });
    const data = await fetchJson(`https://api.iconify.design/search?${params}`);
    for (const icon of data.icons ?? []) {
      const current = scored.get(icon) ?? { score: -Infinity, queries: new Set() };
      current.score = Math.max(current.score, scoreIcon(icon, query));
      current.queries.add(query);
      scored.set(icon, current);
    }
  }
  const icons = [...scored.entries()]
    .filter(([, meta]) => meta.score > 0)
    .sort((left, right) => right[1].score - left[1].score || left[0].localeCompare(right[0]))
    .slice(0, 8);
  return Promise.all(
    icons.map(async ([icon, meta]) => ({
      icon,
      svg: await fetchSvg(icon),
      queries: [...meta.queries].join(", "),
    })),
  );
}

async function buildInventory() {
  const rows = [];
  for (const [familyId, queries] of families) {
    const byPrefix = [];
    for (const prefix of prefixes) {
      byPrefix.push({ ...prefix, icons: await collectFamily(prefix.id, familyId, queries) });
    }
    rows.push({ familyId, queries, byPrefix });
  }
  return rows;
}

function renderIcon(icon) {
  return `
    <article class="icon-card">
      ${icon.svg}
      <strong>${escapeHtml(icon.icon)}</strong>
      <span>${escapeHtml(icon.queries)}</span>
    </article>`;
}

function renderPrefixColumn(prefix) {
  const body = prefix.icons.length
    ? prefix.icons.map(renderIcon).join("\n")
    : '<p class="empty">No direct results from this prefix.</p>';
  return `
    <section class="prefix-column">
      <h3>${escapeHtml(prefix.label)}</h3>
      <p>${escapeHtml(prefix.role)}</p>
      <div class="icon-grid">${body}</div>
    </section>`;
}

function renderFamily(row) {
  return `
    <section class="family">
      <header>
        <h2>${escapeHtml(row.familyId)}</h2>
        <p>Queries: ${escapeHtml(row.queries.join(", "))}</p>
      </header>
      <div class="prefix-grid">
        ${row.byPrefix.map(renderPrefixColumn).join("\n")}
      </div>
    </section>`;
}

const inventory = await buildInventory();
const generatedAt = new Date().toISOString();
const html = `<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>HuleEdu Iconify Semantic Fallback Inventory</title>
  <style>
    :root { --navy:#1c2e4a; --canvas:#f7f5ef; --line:rgba(28,46,74,.22); --muted:rgba(28,46,74,.68); --soft:rgba(28,46,74,.06); }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--canvas); color: var(--navy); font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    main { width: min(1480px, calc(100% - 40px)); margin: 0 auto; padding: 28px 0 48px; }
    h1, h2 { font-family: Georgia, "Times New Roman", serif; letter-spacing: 0; }
    h1 { margin: 0 0 8px; font-size: 38px; }
    h2 { margin: 0; font-size: 25px; text-transform: capitalize; }
    h3 { margin: 0 0 4px; font-size: 16px; }
    p { color: var(--muted); line-height: 1.45; }
    a { color: var(--navy); font-weight: 800; }
    .meta, .notice { border: 1px solid var(--line); background: white; padding: 14px 16px; margin: 18px 0; }
    .family { border: 1px solid var(--line); background: white; margin: 18px 0; box-shadow: 4px 4px 0 var(--navy); }
    .family > header { padding: 14px 16px; border-bottom: 1px solid var(--line); }
    .prefix-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .prefix-column { padding: 14px; min-width: 0; }
    .prefix-column + .prefix-column { border-left: 1px solid var(--line); }
    .icon-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(142px, 1fr)); gap: 8px; margin-top: 12px; }
    .icon-card { min-height: 94px; border: 1px solid var(--line); background: var(--soft); padding: 10px; display: grid; grid-template-rows: 28px auto auto; gap: 6px; align-items: center; }
    .icon-card svg { color: var(--navy); }
    .icon-card strong { font-size: 12px; line-height: 1.15; word-break: break-word; }
    .icon-card span, .empty { color: var(--muted); font-size: 11px; }
    @media (max-width: 760px) { main { width: min(100% - 20px, 1480px); } .prefix-grid { grid-template-columns: 1fr; } .prefix-column + .prefix-column { border-left: 0; border-top: 1px solid var(--line); } }
  </style>
</head>
<body>
  <main>
    <h1>HuleEdu Iconify Semantic Fallback Inventory</h1>
    <p>This board uses Iconify as a research/indexing layer for HuleEdu semantic families. It compares <code>lucide-lab</code> and <code>tabler</code> candidates only; it does not approve either set as a runtime dependency.</p>
    <div class="meta">
      <p>Generated: ${escapeHtml(generatedAt)}</p>
      <p>Sources: Iconify search/SVG API, prefixes <code>lucide-lab</code> and <code>tabler</code>. Return to <a href="index.html">the canonical ST-29-12 symbol inventory</a>.</p>
    </div>
    <section class="notice">
      <strong>Decision policy:</strong> use Lucide proper first, then Lucide Lab, then Tabler as fallback. Iconify remains the comparison/search surface unless a later PR explicitly changes runtime dependency policy.
    </section>
    ${inventory.map(renderFamily).join("\n")}
  </main>
</body>
</html>
`;

writeFileSync(join(generatorDir, "huleedu-iconify-research.html"), html);
console.log(`Generated HuleEdu Iconify fallback inventory for ${families.length} semantic families.`);
