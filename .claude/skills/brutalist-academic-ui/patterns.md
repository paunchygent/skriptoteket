# Brutalist Academic UI Patterns

**Responsibility**: Implementation templates. Copy-paste ready.

---

## 1. Academic Document Layout (Vue + Tailwind)

For documentation, papers, institutional content.

```vue
<article class="mx-auto max-w-[65ch] px-6 py-12 font-serif text-lg leading-relaxed text-navy space-y-6">
  <header class="space-y-2">
    <h1 class="text-3xl font-semibold leading-tight">
      Skriptoteket
    </h1>
    <p class="text-sm text-navy/70">
      Verktyg och manus för lärare.
    </p>
  </header>

  <section class="space-y-4">
    <h2 class="text-xl font-semibold">Bakgrund</h2>
    <p>Content...</p>
    <p>More content...</p>
  </section>
</article>
```

---

## 2. Data-Heavy Interface (Ledger List)

For dashboards, tables, and admin lists.

```vue
<ul class="border border-navy bg-white shadow-brutal-sm divide-y divide-navy/15">
  <li class="p-4">
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <div class="text-base font-semibold text-navy truncate">Titel</div>
        <div class="text-xs text-navy/60">Meta</div>
        <div class="text-xs text-navy/70">Beskrivning…</div>
      </div>
      <span class="status-pill border border-navy/30 bg-canvas/40 text-navy/70">
        Draft
      </span>
    </div>
  </li>
</ul>
```

---

## 3. Navigation

```vue
<nav class="flex items-center gap-6 border-b border-navy py-4 text-xs font-semibold uppercase tracking-wide">
  <RouterLink class="text-navy/70 hover:text-burgundy hover:underline hover:underline-offset-4" to="/">
    Hem
  </RouterLink>
  <RouterLink class="text-burgundy underline underline-offset-4" to="/browse">
    Katalog
  </RouterLink>
  <RouterLink class="text-navy/70 hover:text-burgundy hover:underline hover:underline-offset-4" to="/profile">
    Profil
  </RouterLink>
</nav>
```

---

## 4. Grid Layout

```vue
<section class="grid grid-cols-12 gap-6">
  <aside class="col-span-12 lg:col-span-3 border-r border-navy/20 pr-6">
    Filter
  </aside>
  <main class="col-span-12 lg:col-span-9 space-y-6">
    Content
  </main>
</section>
```

---

## 5. Section Rhythm

```vue
<section class="py-20 border-t border-navy/20">
  <header class="mb-8 space-y-2">
    <h2 class="text-2xl font-semibold text-navy">Sektion</h2>
    <p class="max-w-[65ch] text-navy/60">Kort beskrivning av innehåll.</p>
  </header>
  <div class="space-y-4">
    <p>Content…</p>
  </div>
</section>
```

---

## 6. Editor Workspace Layout (IDE Surface)

Use this pattern for CodeMirror-heavy views and “workspaces” with drawers.

Key rules:

- Outer surface: `border border-navy bg-white shadow-brutal-sm`
- Full-height: `min-h-0` everywhere; only intentional areas scroll.
- Drawer: reuse a right-side rail/column; don’t add a second sidebar.
- Nested panels: **no stacked shadows**; use `panel-inset*` (or `border-2 border-navy/20`) + `shadow-none`.

```vue
<div class="border border-navy bg-white shadow-brutal-sm flex flex-col min-h-0 h-full">
  <header class="border-b border-navy/20 p-3 grid gap-2 md:grid-cols-[minmax(0,1fr)_auto]">
    <div class="min-w-0">
      <h1 class="text-base font-semibold text-navy truncate">Titel</h1>
      <p class="text-xs text-navy/70 truncate">Kort sammanfattning…</p>
    </div>
    <div class="flex items-start justify-end">
      <span class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">Statusrad</span>
    </div>
  </header>

	  <div class="flex-1 min-h-0 grid md:grid-cols-[minmax(0,1fr)_clamp(280px,34vw,360px)]">
	    <main class="min-h-0 p-3 overflow-hidden">
	      <div class="h-full min-h-0 panel-inset-canvas overflow-hidden">
	        <!-- CodeMirror -->
	      </div>
	    </main>
	    <aside class="hidden md:block min-h-0 border-l-2 border-navy/20 bg-canvas shadow-none overflow-hidden">
	      <!-- Drawer content -->
	    </aside>
	  </div>
	</div>
```
