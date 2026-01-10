# Tables and Ledgers

**Responsibility**: Data tables as information architecture. State through structure.

---

## 1. Ledger Structure (Tailwind)

```vue
<div class="w-full border border-navy bg-white shadow-brutal-sm">
  <div class="grid grid-cols-[2fr_1fr_1fr] border-b border-navy bg-canvas text-xs font-semibold uppercase tracking-wide text-navy/70">
    <div class="px-4 py-3">Titel</div>
    <div class="px-4 py-3">Status</div>
    <div class="px-4 py-3">Senast</div>
  </div>
  <div class="group grid grid-cols-[2fr_1fr_1fr] border-b border-navy/15 bg-white hover:bg-canvas transition-colors">
    <div class="px-4 py-3 group-hover:underline group-hover:underline-offset-4">
      Algebra 1
    </div>
    <div class="px-4 py-3 text-navy/70">Draft</div>
    <div class="px-4 py-3 text-navy/70">2026-01-02</div>
  </div>
</div>
```

---

## 2. State Through Structure

State is communicated through structural changes, not decorative badges.

```vue
<div
  class="grid grid-cols-[2fr_1fr_1fr] border-b border-navy/15 bg-white"
  :class="{
    'border-l-4 border-burgundy bg-burgundy/5': state === 'attention',
    'border-l-4 border-burgundy': state === 'processing',
  }"
>
  <div class="px-4 py-3">Process</div>
  <div class="px-4 py-3 text-navy/70">{{ state }}</div>
  <div class="px-4 py-3">
    <span
      v-if="state === 'processing'"
      class="inline-block h-3 w-3 border-2 border-navy/30 border-t-navy rounded-full animate-spin"
      aria-label="Processing"
    />
  </div>
</div>
```

---

## 3. Row Hover

Use background shift + underline; avoid transforms on hard-edged surfaces.

---

## 4. Progress Indicators

```html
<div class="h-[6px] w-full bg-navy/20">
  <div class="h-full bg-navy" style="width: 40%"></div>
</div>
```

Active attention state:

```html
<div class="h-[6px] w-full bg-navy/20">
  <div class="h-full bg-burgundy" style="width: 70%"></div>
</div>
```

---

## 5. Anti-Patterns

- Over-decorated status indicators (multiple colors, icon spam)
- Transforms (`scale`, `translate`) on hard borders/shadows
- Default palette colors (`bg-slate-*`, `text-gray-*`)
