# Components

**Responsibility**: Reusable UI elements. Copy-paste ready.

---

## 1. Button Primitives (SPA)

Skriptoteket ships brutalist buttons in the SPA entry stylesheet. Prefer these before inventing new button styles.

```html
<button class="btn-primary">Spara</button>
<button class="btn-cta">Publicera</button>
<button class="btn-ghost">Redigera</button>
```

### Async button with spinner

```vue
<button class="btn-cta" :disabled="isRunning">
  <span
    v-if="isRunning"
    class="inline-block h-3 w-3 border-2 border-canvas/30 border-t-canvas rounded-full animate-spin"
    aria-hidden="true"
  />
  <span v-else>Kör</span>
</button>
```

---

## 2. Cards

```html
<section class="border border-navy bg-white shadow-brutal-sm p-4 space-y-3">
  <header class="space-y-1">
    <h2 class="text-lg font-semibold text-navy">Card title</h2>
    <p class="text-sm text-navy/70">Subtitle</p>
  </header>
  <p>Content…</p>
</section>
```

---

## 3. Links

```html
<a class="text-navy underline underline-offset-4 hover:text-burgundy" href="/docs">Läs mer</a>
```

---

## 4. Status Pills

Use the shared `.status-pill` base class and add token-driven colors.

```html
<span class="status-pill border border-navy/30 bg-canvas/40 text-navy/70">Draft</span>
<span class="status-pill border border-warning bg-warning/10 text-navy">Granskas</span>
<span class="status-pill border border-success bg-success/10 text-success">OK</span>
<span class="status-pill border border-burgundy/40 bg-burgundy/10 text-burgundy">Åtgärd</span>
```

---

## 5. Utility Buttons (Dense Toolbars)

Use `.btn-ghost` with overrides for micro controls.

```html
<button
  class="btn-ghost shadow-none h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas leading-none"
>
  Formatera
</button>
```

---

## 6. Loading States

```html
<span
  class="inline-block h-4 w-4 border-2 border-navy/30 border-t-navy rounded-full animate-spin"
  aria-label="Laddar"
></span>
```
