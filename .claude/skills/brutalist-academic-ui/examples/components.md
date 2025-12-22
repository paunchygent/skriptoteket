# Components

**Responsibility**: Reusable UI elements. Copy-paste ready.

---

## 1. Hard Shadow Button

Skriptoteket already ships brutalist buttons. Prefer these instead of inventing new button styles.

```html
<!-- Primary CTA (burgundy) -->
<button class="huleedu-btn">Publicera</button>

<!-- Functional action (navy) -->
<button class="huleedu-btn huleedu-btn-navy">Logga in</button>

<!-- Secondary/cancel (outline) -->
<button class="huleedu-btn huleedu-btn-secondary">Avbryt</button>
```

---

## 2. Cards

```html
<section class="huleedu-card">
  <header class="huleedu-card-header">
    <h2>Card title</h2>
  </header>
  <p>Content…</p>
</section>

<!-- Nested/flat context -->
<section class="huleedu-card-flat">
  <p>Flat card…</p>
</section>
```

---

## 3. Links

```html
<a class="huleedu-link" href="/docs">Läs mer</a>
```

---

## 4. Tags/Labels

```html
<span class="huleedu-badge">DRAFT</span>
<span class="huleedu-badge huleedu-badge-burgundy">ATGÄRD</span>
<span class="huleedu-badge huleedu-badge-navy">PUBLISHED</span>
```

---

## 5. Dividers

```css
hr {
  border: none;
  border-top: var(--huleedu-border-width) solid var(--huleedu-navy-20);
  margin: var(--huleedu-space-8) 0;
}

/* Heavy divider */
hr.heavy {
  border-top: var(--huleedu-border-width-2) solid var(--huleedu-border-color);
}
```

---

## 6. Badges (Minimal)

Only when semantically necessary.

```css
.badge {
  font-family: var(--huleedu-font-mono);
  font-size: var(--huleedu-text-xs);
  font-weight: var(--huleedu-font-medium);
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
}

.badge-error { color: var(--huleedu-error); }
.badge-warning { color: var(--huleedu-warning); }
.badge-ok { color: var(--huleedu-navy); } /* Skriptoteket convention: success = navy */
```

No backgrounds. No pills. Text color only.

---

## 7. Loading States

```html
<span class="huleedu-spinner" aria-label="Loading"></span>
<span class="huleedu-spinner huleedu-spinner-sm" aria-label="Loading"></span>
```
