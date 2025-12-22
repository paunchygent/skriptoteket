# Brutalist Academic UI Patterns

**Responsibility**: Implementation templates. Copy-paste ready.

---

## 1. Academic Document Layout

For documentation, papers, institutional content.

```css
body {
  font-family: var(--huleedu-font-serif);
  font-size: var(--huleedu-text-lg);
  line-height: var(--huleedu-leading-relaxed);
  color: var(--huleedu-navy);
  background: var(--huleedu-canvas);
}

.document {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--huleedu-space-16) var(--huleedu-space-6);
}

.document h1 {
  font-size: var(--huleedu-text-3xl);
  font-weight: var(--huleedu-font-semibold);
  line-height: var(--huleedu-leading-tight);
  margin-bottom: var(--huleedu-space-8);
}

.document h2 {
  font-size: var(--huleedu-text-xl);
  font-weight: var(--huleedu-font-semibold);
  margin-top: var(--huleedu-space-12);
  margin-bottom: var(--huleedu-space-4);
  padding-bottom: var(--huleedu-space-2);
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-navy-20);
}

.document p + p {
  margin-top: var(--huleedu-space-4);
}
```

---

## 2. Data-Heavy Interface

For dashboards, tables, system information.

```css
body {
  font-family: var(--huleedu-font-mono);
  font-size: var(--huleedu-text-sm);
  line-height: var(--huleedu-leading-normal);
  color: var(--huleedu-navy);
  background: var(--huleedu-canvas);
}

/* Skriptoteket already ships .huleedu-table. Add a dense modifier when needed. */
.huleedu-table.huleedu-table-dense th,
.huleedu-table.huleedu-table-dense td {
  padding: var(--huleedu-space-2) var(--huleedu-space-3);
}
```

---

## 3. Navigation

```css
.nav {
  display: flex;
  gap: var(--huleedu-space-8);
  padding: var(--huleedu-space-4) 0;
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-border-color);
}

.nav a {
  color: var(--huleedu-navy);
  text-decoration: none;
  font-size: var(--huleedu-text-sm);
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-wide);
}

.nav a:hover,
.nav a[aria-current="page"] {
  text-decoration: underline;
  text-underline-offset: 4px;
}
```

---

## 4. Grid Layout

```css
.layout {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--huleedu-space-8);
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 var(--huleedu-space-12);
}

/* Sidebar + Content */
.layout-sidebar {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: var(--huleedu-space-12);
}

/* Three columns */
.layout-thirds {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--huleedu-space-8);
}
```

---

## 5. Section Rhythm

```css
section {
  padding: var(--huleedu-space-20) 0;
}

section + section {
  border-top: var(--huleedu-border-width) solid var(--huleedu-navy-20);
}

.section-header {
  margin-bottom: var(--huleedu-space-8);
}

.section-header h2 {
  font-size: var(--huleedu-text-2xl);
  font-weight: var(--huleedu-font-semibold);
  margin-bottom: var(--huleedu-space-2);
}

.section-header p {
  color: var(--huleedu-navy-60);
  max-width: 65ch;
}
```
