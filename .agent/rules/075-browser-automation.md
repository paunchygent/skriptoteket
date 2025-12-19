---
id: "075-browser-automation"
type: "quality"
created: 2025-12-19
scope: "testing"
---

# 075: Browser Automation

## Available Tools

| Tool | Language | Install |
|------|----------|---------|
| Playwright | Python | `pdm install -G dev` (included) |
| Selenium | Python | `pdm install -G dev` (included) |
| Puppeteer | Node.js | `npm install puppeteer` |

## Running Scripts

All browser automation scripts go in `scripts/` and run via terminal:

```bash
pdm run python scripts/my_visual_test.py
```

## Playwright (Recommended)

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://127.0.0.1:8000/login')
    page.fill('input[name="email"]', 'superuser@local.dev')
    page.fill('input[name="password"]', 'superuser-password')
    page.click('button[type="submit"]')
    page.wait_for_url('**/dashboard**')
    page.screenshot(path='screenshot.png')
    browser.close()
```

## Selenium

```python
from selenium import webdriver
from selenium.webdriver.common.by import By

options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)
driver.get('http://127.0.0.1:8000/login')
driver.find_element(By.NAME, 'email').send_keys('superuser@local.dev')
driver.find_element(By.NAME, 'password').send_keys('superuser-password')
driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
driver.save_screenshot('screenshot.png')
driver.quit()
```

## Puppeteer (Node.js)

```javascript
await page.goto('http://127.0.0.1:8000/login', { waitUntil: 'networkidle0' });
await page.type('input[name="email"]', 'superuser@local.dev');
await page.type('input[name="password"]', 'superuser-password');
await page.evaluate(() => document.querySelector('form').submit());
await new Promise(r => setTimeout(r, 1500));
```

## Project-Specific Notes

### HTMX Forms

HTMX forms don't trigger standard navigation events. Avoid:
```javascript
// BAD - times out
await page.click('button[type="submit"]');
await page.waitForNavigation();
```

Use explicit waits instead:
```python
# Playwright
page.wait_for_url('**/dashboard**')

# Selenium
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
WebDriverWait(driver, 10).until(EC.url_contains('/dashboard'))
```

### Test Credentials

From `.env`:
- Email: `superuser@local.dev`
- Password: `superuser-password`
