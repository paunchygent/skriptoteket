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

All screenshots/recordings go to `/tmp/` with descriptive names:

- `/tmp/admin-tools-1440x900.png`
- `/tmp/script-editor.png`

## Skriptoteket Login (CRITICAL)

Credentials are in `.env`:

- Email: `BOOTSTRAP_SUPERUSER_EMAIL` (usually `superuser@local.dev`)
- Password: `BOOTSTRAP_SUPERUSER_PASSWORD` (usually `superuser-password`)

**Login pattern** - use `form.submit()` and wait with timeout:

```javascript
await page.goto('http://127.0.0.1:8000/login', { waitUntil: 'networkidle0' });
await page.type('input[name="email"]', 'superuser@local.dev');
await page.type('input[name="password"]', 'superuser-password');
await page.evaluate(() => document.querySelector('form').submit());
await new Promise(r => setTimeout(r, 1500)); // Wait for redirect
```

**DO NOT** use `page.click()` + `waitForNavigation()` - it times out with HTMX forms.

## Quick Workflow

```javascript
const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  // Login
  await page.goto('http://127.0.0.1:8000/login', { waitUntil: 'networkidle0' });
  await page.type('input[name="email"]', 'superuser@local.dev');
  await page.type('input[name="password"]', 'superuser-password');
  await page.evaluate(() => document.querySelector('form').submit());
  await new Promise(r => setTimeout(r, 1500));

  // Navigate and screenshot
  await page.goto('http://127.0.0.1:8000/admin/tools', { waitUntil: 'networkidle0' });
  await page.screenshot({ path: '/tmp/admin-tools.png' });

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
