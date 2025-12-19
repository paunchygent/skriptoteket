---
name: playwright-testing
description: Browser automation with Playwright for Python. Recommended for visual testing. (project)
---

# Playwright Testing

## When to Use

- Visual testing, screenshots, UI verification
- Mentions: "playwright", "screenshot", "visual test"

## Run

```bash
pdm run python scripts/my_test.py
```

## Quick Pattern

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_viewport_size({"width": 1440, "height": 900})

    # Login
    page.goto('http://127.0.0.1:8000/login')
    page.fill('input[name="email"]', 'superuser@local.dev')
    page.fill('input[name="password"]', 'superuser-password')
    page.click('button[type="submit"]')
    page.wait_for_url('**/dashboard**')

    # Screenshot
    page.goto('http://127.0.0.1:8000/admin/tools')
    page.screenshot(path='/tmp/admin-tools.png')
    browser.close()
```

## HTMX Caveat

Use `page.wait_for_url()` instead of waiting for navigation events.

## Context7

Use `mcp__context7__get-library-docs` with `/microsoft/playwright-python` for API details.
