/**
 * Generate the ST-29-12 symbol inventory reasoning artifact.
 *
 * Relationships:
 * - Reads the installed `lucide-vue-next` package used by the Skriptoteket SPA.
 * - Reads current shared icon wrappers from `src/components/icons`.
 * - Reads direct Lucide imports from the SPA source tree so symbol drift is
 *   visible before runtime decisions are made in PR-0292 and later slices.
 */

import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, extname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const generatorDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(generatorDir, "../../..");
const frontendRoot = join(repoRoot, "frontend/apps/skriptoteket");
const sourceRoot = join(frontendRoot, "src");
const iconWrapperRoot = join(sourceRoot, "components/icons");
const lucideRoot = join(frontendRoot, "node_modules/lucide-vue-next");
const lucidePackage = JSON.parse(
  readFileSync(join(lucideRoot, "package.json"), "utf8"),
);
const lucideCjs = readFileSync(
  join(lucideRoot, "dist/cjs/lucide-vue-next.js"),
  "utf8",
);

const seedSemanticRows = [
  ["actual-share-link", "IconLink2 / Link2", "current, restrict", "Use for public/internal share links and copy-link affordances only."],
  ["keep-near-rule", "Candidates: Magnet, Handshake, UsersRound", "drift", "Current Link2 overlap is semantic drift because proximity rules are not actual links."],
  ["keep-apart-rule", "IconBan / Ban", "current, review", "Represents separation/avoidance; compare with Unlink or ShieldBan if conflict semantics are preferred."],
  ["near-teacher-rule", "IconGraduationCap / GraduationCap", "current, review", "Teacher anchor candidate; compare with School only if the slot means classroom/building context."],
  ["grouping-mode", "Candidates: UsersRound, Group, PanelsTopLeft", "unresolved", "Needs a dedicated group-workspace symbol rather than generic student/list reuse."],
  ["seating-mode", "IconArmchair / Armchair", "current, review", "Current seating-place symbol; verify it reads as classroom seating at toolbar size."],
  ["overview-mode", "IconClipboardList / ClipboardList", "current, review", "Current overview/list affordance."],
  ["rules-mode", "IconPresentation / Presentation", "current, review", "Review because the user has flagged screen/TV readings in this family."],
  ["class-list", "Candidates: ClipboardList, ListChecks, UsersRound", "unresolved", "Should distinguish roster/list semantics from student-group semantics."],
  ["classroom", "IconSchool / School", "current, review", "Good for school/classroom context, but may be too broad for one classroom."],
  ["students", "IconUsersRound / UsersRound", "current, review", "Avoid reusing this slot for grouping itself if a clearer group symbol is chosen."],
  ["pdf-file", "FileText", "current", "Current share/export file-type candidate."],
  ["spreadsheet-file", "FileSpreadsheet", "current", "Current share/export spreadsheet file-type candidate."],
  ["download-action", "IconDownload / Download", "current", "Outward file save/download action, not file type."],
  ["configure-context", "IconAdjustments -> SlidersHorizontal", "locked replacement", "Replace the custom SVG with Lucide SlidersHorizontal while preserving wrapper semantics."],
  ["fit-view", "IconFitView -> Fullscreen", "locked replacement", "Use Lucide Fullscreen behind the fit-view wrapper name; the control remains fit-view, not fullscreen behavior."],
  ["remove-decrement", "IconMinus -> Minus", "locked replacement", "Replace the custom SVG with Lucide Minus and keep it paired with IconPlus."],
  ["zoom-in", "IconZoomIn -> ZoomIn", "locked replacement", "Replace the custom SVG with Lucide ZoomIn."],
  ["zoom-out", "IconZoomOut -> ZoomOut", "locked replacement", "Replace the custom SVG with Lucide ZoomOut."],
];
const seedSemanticMap = seedSemanticRows.map(([slot, symbol, status, note]) => ({
  slot,
  symbol,
  status,
  note,
}));

const candidateIconNames = new Set([
  "Armchair",
  "Ban",
  "Check",
  "CircleHelp",
  "ClipboardList",
  "Copy",
  "Download",
  "FileSpreadsheet",
  "FileText",
  "Fullscreen",
  "GraduationCap",
  "Group",
  "Handshake",
  "History",
  "Link2",
  "Magnet",
  "Minus",
  "PanelsTopLeft",
  "Presentation",
  "School",
  "Settings",
  "Settings2",
  "ShieldBan",
  "SlidersHorizontal",
  "Trash2",
  "Unlink",
  "UsersRound",
  "ZoomIn",
  "ZoomOut",
]);

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function toKebabCase(value) {
  return value.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase();
}

function listFiles(root, extensions) {
  const results = [];
  const stack = [root];
  while (stack.length > 0) {
    const current = stack.pop();
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      const path = join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(path);
      } else if (extensions.includes(extname(entry.name))) {
        results.push(path);
      }
    }
  }
  return results.sort();
}

function parseAttributes(raw) {
  const attrs = [];
  const attrPattern = /["']?([a-zA-Z0-9:-]+)["']?\s*:\s*"([^"]*)"/g;
  let attrMatch;
  while ((attrMatch = attrPattern.exec(raw)) !== null) {
    const [, key, value] = attrMatch;
    if (key !== "key") {
      attrs.push(`${key}="${escapeHtml(value)}"`);
    }
  }
  return attrs.join(" ");
}

function parseIconNodes(raw) {
  const nodes = [];
  const nodePattern = /\[\s*"([a-z]+)"\s*,\s*\{([\s\S]*?)\}\s*\]/g;
  let nodeMatch;
  while ((nodeMatch = nodePattern.exec(raw)) !== null) {
    const [, tag, attrs] = nodeMatch;
    nodes.push(`<${tag} ${parseAttributes(attrs)} />`);
  }
  return nodes.join("");
}

function parseLucideIcons() {
  const icons = [];
  const iconPattern =
    /const ([A-Za-z0-9]+) = createLucideIcon\("([^"]+)", \[([\s\S]*?)\]\);/g;
  let iconMatch;
  while ((iconMatch = iconPattern.exec(lucideCjs)) !== null) {
    const [, componentName, kebabName, nodeSource] = iconMatch;
    icons.push({
      componentName,
      kebabName,
      svg: parseIconNodes(nodeSource),
      isCandidate: candidateIconNames.has(componentName),
    });
  }
  return icons.sort((left, right) =>
    left.componentName.localeCompare(right.componentName),
  );
}

function parseLucideImportNames(source) {
  const names = [];
  const importPattern =
    /import\s+\{([^}]+)\}\s+from\s+["']lucide-vue-next["'];?/g;
  let importMatch;
  while ((importMatch = importPattern.exec(source)) !== null) {
    for (const rawName of importMatch[1].split(",")) {
      const name = rawName.trim().split(/\s+as\s+/)[0]?.trim();
      if (name) {
        names.push(name);
      }
    }
  }
  return names;
}

function normalizeCustomSvg(source) {
  const match = source.match(/<svg[\s\S]*?<\/svg>/);
  if (!match) {
    return "";
  }
  return match[0]
    .replace(/:width="size \?\? 24"/, 'width="24"')
    .replace(/:height="size \?\? 24"/, 'height="24"')
    .replace(/stroke-width="2\.5"/, 'stroke-width="2.25"')
    .replace(/\s+/g, " ")
    .trim();
}

function parseWrapperInventory() {
  return listFiles(iconWrapperRoot, [".vue"]).map((file) => {
    const source = readFileSync(file, "utf8");
    const imports = parseLucideImportNames(source);
    const hasCustomSvg = source.includes("<svg");
    return {
      wrapper: basename(file, ".vue"),
      source: imports.length > 0 ? imports.join(", ") : "custom svg",
      path: relative(repoRoot, file),
      custom: hasCustomSvg && imports.length === 0,
      svg: hasCustomSvg && imports.length === 0 ? normalizeCustomSvg(source) : "",
    };
  });
}

function classifySurface(path) {
  if (path.includes("/src/components/icons/")) {
    return "shared icon wrapper";
  }
  if (path.includes("/src/views/apps/components/Planner")) {
    return "Klassrumskartan";
  }
  if (path.includes("/src/components/ui/")) {
    return "shared UI";
  }
  if (path.includes("/src/components/auth/")) {
    return "auth UI";
  }
  return "SPA surface";
}

function parseDirectLucideImports() {
  return listFiles(sourceRoot, [".vue", ".ts"])
    .map((file) => {
      const source = readFileSync(file, "utf8");
      return {
        path: relative(repoRoot, file),
        surface: classifySurface(file),
        imports: parseLucideImportNames(source),
      };
    })
    .filter((entry) => entry.imports.length > 0)
    .sort((left, right) => left.path.localeCompare(right.path));
}

function iconSvg(icon) {
  return `<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icon.svg}</svg>`;
}

function renderRows(rows, renderCells) {
  return rows.map((row) => `<tr>${renderCells(row).join("")}</tr>`).join("\n");
}

function renderCandidateStrip(icons) {
  const candidates = icons.filter((icon) => icon.isCandidate);
  return candidates
    .map(
      (icon) => `
        <article class="icon-card icon-card--candidate" data-icon="${escapeHtml(icon.componentName)}" data-kebab="${escapeHtml(icon.kebabName)}">
          ${iconSvg(icon)}
          <div class="icon-name">${escapeHtml(icon.componentName)}</div>
          <div class="icon-kebab">${escapeHtml(icon.kebabName)}</div>
        </article>`,
    )
    .join("\n");
}

function renderCustomWrapperStrip(wrappers) {
  return wrappers
    .filter((wrapper) => wrapper.custom)
    .map(
      (wrapper) => `
        <article class="icon-card icon-card--custom" data-icon="${escapeHtml(wrapper.wrapper)}">
          ${wrapper.svg}
          <div class="icon-name">${escapeHtml(wrapper.wrapper)}</div>
          <div class="icon-kebab">custom svg</div>
        </article>`,
    )
    .join("\n");
}

function renderIconGrid(icons) {
  return icons
    .map(
      (icon) => `
        <article class="icon-card" data-icon="${escapeHtml(icon.componentName)}" data-kebab="${escapeHtml(icon.kebabName)}">
          ${iconSvg(icon)}
          <div class="icon-name">${escapeHtml(icon.componentName)}</div>
          <div class="icon-kebab">${escapeHtml(icon.kebabName)}</div>
        </article>`,
    )
    .join("\n");
}

const lucideIcons = parseLucideIcons();
const wrappers = parseWrapperInventory();
const directImports = parseDirectLucideImports();
const wrapperCount = wrappers.length;
const customWrapperCount = wrappers.filter((wrapper) => wrapper.custom).length;
const directImportCount = directImports.reduce(
  (total, entry) => total + entry.imports.length,
  0,
);
const directImportSymbols = [
  ...new Set(directImports.flatMap((entry) => entry.imports)),
].sort();

const html = `<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ST-29-12 Symbol Inventory</title>
  <style>
    :root {
      --navy: #1c2e4a;
      --canvas: #f7f5ef;
      --line: rgba(28, 46, 74, 0.22);
      --muted: rgba(28, 46, 74, 0.68);
      --soft: rgba(28, 46, 74, 0.06);
      --drift: #7a1730;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--canvas);
      color: var(--navy);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main { width: min(1440px, calc(100% - 40px)); margin: 0 auto; padding: 28px 0 48px; }
    h1, h2, h3 { font-family: Georgia, "Times New Roman", serif; letter-spacing: 0; }
    h1 { margin: 0 0 8px; font-size: 38px; }
    h2 { margin: 34px 0 12px; font-size: 25px; }
    h3 { margin: 0 0 10px; font-size: 18px; }
    p { max-width: 920px; color: var(--muted); line-height: 1.45; }
    code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    .meta { display: flex; gap: 8px; flex-wrap: wrap; margin: 16px 0 28px; }
    .pill {
      border: 1px solid var(--line);
      background: white;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 750;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .panel {
      border: 1px solid var(--line);
      background: white;
      padding: 16px;
      box-shadow: 4px 4px 0 var(--navy);
    }
    .inventory-actions {
      position: sticky;
      top: 0;
      z-index: 1;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: center;
      margin: 24px 0 16px;
      background: var(--canvas);
      padding: 12px 0;
    }
    .search {
      min-height: 44px;
      border: 1px solid var(--line);
      background: white;
      color: var(--navy);
      padding: 0 12px;
      font: inherit;
      font-weight: 650;
    }
    table { width: 100%; border-collapse: collapse; background: white; border: 1px solid var(--line); }
    th, td { border-bottom: 1px solid var(--line); padding: 10px 12px; text-align: left; vertical-align: top; }
    th { font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); }
    td { font-size: 13px; }
    .semantic-id { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }
    .status { font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; }
    .status--drift { color: var(--drift); }
    .icon-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
    .icon-card {
      min-height: 92px;
      display: grid;
      grid-template-rows: 32px auto auto;
      gap: 6px;
      align-items: center;
      justify-items: start;
      border: 1px solid var(--line);
      background: white;
      padding: 10px;
    }
    .icon-card--candidate { background: var(--soft); border-color: var(--navy); }
    .icon-card--custom { border-color: var(--drift); background: #fffafa; }
    .icon-card svg { color: var(--navy); }
    .icon-name { font-size: 12px; font-weight: 750; line-height: 1.15; word-break: break-word; }
    .icon-kebab { font-size: 11px; color: var(--muted); word-break: break-word; }
    .note { border: 1px solid var(--line); background: white; padding: 14px 16px; }
    .path { color: var(--muted); font-size: 12px; }
    .count { color: var(--muted); font-size: 12px; font-weight: 750; text-transform: uppercase; letter-spacing: 0.08em; }
    @media (max-width: 720px) {
      main { width: min(100% - 20px, 1440px); }
      .inventory-actions { grid-template-columns: 1fr; }
      th, td { padding: 8px; }
    }
  </style>
</head>
<body>
  <main>
    <h1>ST-29-12 Symbol Inventory</h1>
    <p>This artifact is a reasoning surface for the canonical symbol-language pass. It combines the current Skriptoteket icon wrapper registry, direct Lucide imports in the SPA, a seed semantic map for Klassrumskartan/site actions, and the complete local Lucide component inventory available from <code>${escapeHtml(lucidePackage.name)}@${escapeHtml(lucidePackage.version)}</code>.</p>
    <div class="meta">
      <span class="pill">${lucideIcons.length} Lucide components</span>
      <span class="pill">${wrapperCount} current wrappers</span>
      <span class="pill">${customWrapperCount} custom wrappers</span>
      <span class="pill">${directImportSymbols.length} direct symbols across ${directImports.length} files</span>
      <span class="pill">Generated from local dependencies</span>
    </div>

    <section class="panel">
      <h3>Use this as inventory, not decision.</h3>
      <p>The backlog story and PR tasks decide the final semantic assignments. This page deliberately keeps unresolved candidates visible so symbol drift can be discussed before code changes. Context7 confirms Lucide Vue usage as named tree-shakable components; this artifact uses the installed package as runtime truth.</p>
    </section>
    <section class="panel"><h3>HuleEdu Fallback Research</h3><p><a href="huleedu-iconify-research.html">Open the Iconify fallback board</a> for Lucide Lab and Tabler candidates across classroom, maps, proximity/short-distance, groups, cooperation, ideation, teacher, hand-in, bench, homework, exam, grade, learning, assessment, AI, language, and writing semantics.</p></section>

    <h2>Seed Semantic Map</h2>
    <table>
      <thead><tr><th>Semantic slot</th><th>Current or candidate symbol</th><th>Status</th><th>Decision note</th></tr></thead>
      <tbody>
${renderRows(seedSemanticMap, (row) => [
  `<td class="semantic-id">${escapeHtml(row.slot)}</td>`,
  `<td>${escapeHtml(row.symbol)}</td>`,
  `<td class="status ${row.status.includes("drift") ? "status--drift" : ""}">${escapeHtml(row.status)}</td>`,
  `<td>${escapeHtml(row.note)}</td>`,
])}
      </tbody>
    </table>

    <h2>Current Custom SVG Wrappers</h2>
    <p>These wrappers are currently hand-authored SVGs. They must remain visible in this inventory so PR-0292 can decide whether Lucide or a compatible EdTech-oriented add-on library can replace them.</p>
    <div class="icon-grid">
${renderCustomWrapperStrip(wrappers)}
    </div>

    <h2>High-Value Candidate Icons</h2>
    <p>Candidate icons from the current semantic questions are pulled out here, then repeated in the complete inventory below.</p>
    <div class="icon-grid">
${renderCandidateStrip(lucideIcons)}
    </div>

    <h2>Current Shared Icon Wrappers</h2>
    <table>
      <thead><tr><th>Wrapper</th><th>Source</th><th>Path</th></tr></thead>
      <tbody>
${renderRows(wrappers, (wrapper) => [
  `<td class="semantic-id">${escapeHtml(wrapper.wrapper)}</td>`,
  `<td>${escapeHtml(wrapper.source)}</td>`,
  `<td class="path">${escapeHtml(wrapper.path)}</td>`,
])}
      </tbody>
    </table>

    <h2>Direct Lucide Imports In The SPA</h2>
    <p>This table shows every current <code>lucide-vue-next</code> import in the SPA source tree, including the shared wrappers. Runtime decisions after PR-0292 should prefer canonical wrappers for repeated semantics.</p>
    <table>
      <thead><tr><th>Surface</th><th>Imported symbols</th><th>Path</th></tr></thead>
      <tbody>
${renderRows(directImports, (entry) => [
  `<td>${escapeHtml(entry.surface)}</td>`,
  `<td class="semantic-id">${escapeHtml(entry.imports.join(", "))}</td>`,
  `<td class="path">${escapeHtml(entry.path)}</td>`,
])}
      </tbody>
    </table>

    <div class="inventory-actions">
      <input class="search" type="search" placeholder="Filtrera Lucide-symboler..." aria-label="Filtrera Lucide-symboler" />
      <div class="count" aria-live="polite">${lucideIcons.length} symbols</div>
    </div>

    <h2>Complete Local Lucide Component Inventory</h2>
    <div class="icon-grid" id="lucide-grid">
${renderIconGrid(lucideIcons)}
    </div>
  </main>
  <script>
    const search = document.querySelector(".search");
    const count = document.querySelector(".count");
    const cards = [...document.querySelectorAll("#lucide-grid .icon-card")];
    search?.addEventListener("input", () => {
      const query = search.value.trim().toLowerCase();
      let visible = 0;
      for (const card of cards) {
        const haystack = \`\${card.dataset.icon} \${card.dataset.kebab}\`.toLowerCase();
        const matched = haystack.includes(query);
        card.hidden = !matched;
        if (matched) visible += 1;
      }
      count.textContent = \`\${visible} symbols\`;
    });
  </script>
</body>
</html>
`;

writeFileSync(join(generatorDir, "index.html"), html);
console.log(
  `Generated index.html with ${lucideIcons.length} Lucide components, ${wrapperCount} wrappers, and ${directImportCount} direct imports.`,
);
