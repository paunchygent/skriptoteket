---
name: selenium-testing
description: Browser automation with Selenium WebDriver for Python. (project)
---

# Selenium Testing

## When to Use

- Browser automation, visual testing
- Mentions: "selenium", "webdriver", "screenshot"

## Run

```bash
pdm run python scripts/my_test.py
```

## Quick Pattern

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)
driver.set_window_size(1440, 900)

# Login
driver.get('http://127.0.0.1:8000/login')
driver.find_element(By.NAME, 'email').send_keys('superuser@local.dev')
driver.find_element(By.NAME, 'password').send_keys('superuser-password')
driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
WebDriverWait(driver, 10).until(EC.url_contains('/dashboard'))

# Screenshot
driver.get('http://127.0.0.1:8000/admin/tools')
driver.save_screenshot('/tmp/admin-tools.png')
driver.quit()
```

## HTMX Caveat

Use explicit `WebDriverWait` with `EC.url_contains()` instead of implicit waits.

## Context7

Use `mcp__context7__get-library-docs` with `/seleniumhq/selenium` for API details.
