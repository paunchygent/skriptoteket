# Tables and Ledgers

**Responsibility**: Data tables as information architecture. State through structure.

---

## 1. Ledger Structure

```css
.ledger {
  width: 100%;
  border: var(--huleedu-border-width-2) solid var(--huleedu-border-color);
  background: #fff;
}

.ledger-header {
  display: grid;
  border-bottom: var(--huleedu-border-width-2) solid var(--huleedu-border-color);
  background: var(--huleedu-navy-02);
  font-size: var(--huleedu-text-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
}

.ledger-row {
  display: grid;
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-border-color);
  background: #fff;
  cursor: pointer;
}

.ledger-cell {
  padding: var(--huleedu-space-4);
  border-right: var(--huleedu-border-width) solid var(--huleedu-border-color);
}

.ledger-cell:last-child {
  border-right: none;
}
```

---

## 2. State Through Structure

State is communicated through structural changes, not decorative badges.

### Processing State

```html
<div class="ledger-row ledger-row-processing" data-state="processing">
  <div class="ledger-cell">
    <span class="huleedu-badge huleedu-badge-burgundy">Processing</span>
  </div>
  <div class="ledger-cell">
    <span class="huleedu-spinner huleedu-spinner-sm" aria-label="Processing"></span>
  </div>
</div>
```

### Attention Required

```html
<div class="ledger-row ledger-row-attention" data-state="attention">
  <div class="ledger-cell">
    <span class="huleedu-badge huleedu-badge-burgundy">Action</span>
  </div>
</div>
```

### Complete State

```html
<div class="ledger-row" data-state="complete">
  <div class="ledger-cell">
    <span class="huleedu-badge">Done</span>
  </div>
</div>
```

```css
.ledger-row-processing {
  border-left: 4px solid var(--huleedu-burgundy);
}

.ledger-row-attention {
  border-bottom: var(--huleedu-border-width-2) solid var(--huleedu-burgundy);
  background: var(--huleedu-burgundy-05);
}
```

---

## 3. Row Hover

```css
/* Hard outline, background shift */
.ledger-row:hover {
  background: var(--huleedu-navy-02);
  outline: var(--huleedu-border-width-2) solid var(--huleedu-border-color);
  outline-offset: -2px;
  position: relative;
  z-index: 1;
}

/* Underline on primary text */
.ledger-row:hover .ledger-title {
  text-decoration: underline;
  text-decoration-thickness: 2px;
  text-underline-offset: 4px;
}

/* Banned */
.ledger-row:hover {
  box-shadow: 0 10px 40px rgba(0,0,0,0.1); /* No */
  transform: scale(1.01); /* No */
}
```

---

## 4. State Transitions (Websocket)

Brief flash on state change. Not bounce, not slide.

```css
@keyframes state-change {
  0%, 100% { background-color: transparent; }
  50% { background-color: var(--huleedu-burgundy-10); }
}

.ledger-row[data-state-changed] {
  animation: state-change 0.4s ease;
}
```

```javascript
row.setAttribute('data-state-changed', '');
row.addEventListener('animationend', () => {
  row.removeAttribute('data-state-changed');
}, { once: true });
```

---

## 5. Progress Indicators

```css
.progress-track {
  width: 100%;
  height: 6px;
  background: var(--huleedu-navy-20);
  /* No border-radius. A bar is a bar. */
}

.progress-fill {
  height: 100%;
  background: var(--huleedu-navy);
  transition: width 0.3s ease;
}

.progress-fill[data-active] {
  background: var(--huleedu-burgundy);
}
```

---

## 6. Anti-Patterns

- **Status pills with big border-radius** = decorating, not communicating
- **Multiple competing colors**: One accent for attention. Everything else is ink or muted.
- **Icons for every state**: Checkmark next to "Complete" is redundant
- **Animated progress for complete items**: If done, it's done.
- **Hover effects that obscure**: Enhance readability, don't compete with it.
