---
name: puppeteer-visual-testing
description: Screenshot capture and visual testing with Puppeteer v24.x for Vue frontend. (project)
---

# Puppeteer Visual Testing

## When to Use

- After creating/modifying templates or CSS
- Verify visual changes after design updates
- Validate responsive layouts
- Mentions: "screenshot", "visual test", "visual regression"

## Prerequisites

- Dev server running: `pdm run dev` at `http://127.0.0.1:8000`
- Puppeteer installed in `tools/puppeteer/` (run `npm install` there)
- ffmpeg installed (for screencast)

## Running Scripts

Run puppeteer scripts from project root using the local installation:

```bash
node -e "..."
# Or with explicit path:
NODE_PATH=tools/puppeteer/node_modules node script.js
```

## Output

All screenshots/recordings go under `.artifacts/` with descriptive names:

- `.artifacts/puppeteer/admin-tools-1440x900.png`
- `.artifacts/puppeteer/script-editor.png`

## Skriptoteket Login (CRITICAL)

Credentials must be provided via a gitignored dotenv file (default: `.env`, override via `DOTENV_PATH`) or
exported env vars.

For dev/local, use:

- `BOOTSTRAP_SUPERUSER_EMAIL` / `BOOTSTRAP_SUPERUSER_PASSWORD`

For prod smoke runs, prefer a separate `.env.prod-smoke` with:

- `BASE_URL`
- `PLAYWRIGHT_EMAIL` / `PLAYWRIGHT_PASSWORD`

**Login pattern** (assumes `baseUrl`, `email`, `password` are set; see workflow below) - use `form.submit()` and wait with timeout:

```javascript
await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle0' });
await page.type('input[name="email"]', email);
await page.type('input[name="password"]', password);
await page.evaluate(() => document.querySelector('form').submit());
await page.waitForFunction(() => document.body.textContent?.includes('Inloggad som'), { timeout: 10_000 });
```

**DO NOT** use `page.click()` + `waitForNavigation()` - it times out with HTMX forms.

## Quick Workflow

```javascript
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

function readDotenv(filePath = path.resolve(process.cwd(), '.env')) {
  if (!fs.existsSync(filePath)) return {};
  const out = {};
  for (const rawLine of fs.readFileSync(filePath, 'utf8').split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const idx = line.indexOf('=');
    out[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
  }
  return out;
}

(async () => {
  const dotenv = readDotenv(process.env.DOTENV_PATH || path.resolve(process.cwd(), '.env'));
  const baseUrl = process.env.BASE_URL || dotenv.BASE_URL || 'http://127.0.0.1:8000';
  const email = process.env.PLAYWRIGHT_EMAIL || dotenv.PLAYWRIGHT_EMAIL
    || process.env.BOOTSTRAP_SUPERUSER_EMAIL || dotenv.BOOTSTRAP_SUPERUSER_EMAIL;
  const password = process.env.PLAYWRIGHT_PASSWORD || dotenv.PLAYWRIGHT_PASSWORD
    || process.env.BOOTSTRAP_SUPERUSER_PASSWORD || dotenv.BOOTSTRAP_SUPERUSER_PASSWORD;
  if (!email || !password) throw new Error('Missing credentials (PLAYWRIGHT_* or BOOTSTRAP_SUPERUSER_*)');

  const artifactsDir = path.resolve(process.cwd(), '.artifacts/puppeteer');
  fs.mkdirSync(artifactsDir, { recursive: true });

  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  // Login
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle0' });
  await page.type('input[name="email"]', email);
  await page.type('input[name="password"]', password);
  await page.evaluate(() => document.querySelector('form').submit());
  await page.waitForFunction(() => document.body.textContent?.includes('Inloggad som'), { timeout: 10_000 });

  // Navigate and screenshot
  await page.goto(`${baseUrl}/admin/tools`, { waitUntil: 'networkidle0' });
  await page.screenshot({ path: path.join(artifactsDir, 'admin-tools.png'), fullPage: true });

  await browser.close();
})();
```

## Skriptoteket Routes

| Route | Description |
|-------|-------------|
| `/` | Home page |
| `/login` | Login page |
| `/admin/tools` | Tool management |
| `/admin/tool-versions/{uuid}` | Script editor |
| `/admin/suggestions` | Suggestion review |

## Reference

- [reference.md](reference.md) - v24.x API (locator, screencast, emulateMediaFeatures)
- [patterns.md](patterns.md) - Copy-paste test patterns
