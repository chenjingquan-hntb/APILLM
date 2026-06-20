# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** APILLM Relay
**Generated:** 2026-06-20 09:19:57
**Category:** Developer Tool / API Infrastructure

---

## Global Rules

### Color Palette

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Background (Deep) | `#080808` | `--color-bg` |
| Background (Card) | `#111111` | `--color-card` |
| Border | `#1A1A1A` | `--color-border` |
| Primary Text | `#FAFAFA` | `--color-text` |
| Secondary Text | `#888888` | `--color-text-secondary` |
| Accent (Blue) | `#3B82F6` | `--color-accent` |
| Accent (Green) | `#22C55E` | `--color-accent-green` |
| Code Background | `#0D1117` | `--color-code-bg` |

**Color Notes:** OLED-optimized dark. Only 2 accent colors: Blue for CTAs/links, Green for status/success. No gradients, no box-shadows — pure flat dark.

### Typography

- **Heading Font:** Outfit
- **Body Font:** Inter
- **Code Font:** JetBrains Mono
- **Mood:** geometric, precise, minimal, professional
- **Google Fonts:** [Outfit + Inter + JetBrains Mono](https://fonts.google.com/share?selection.family=Inter:wght@300;400;500;600|Outfit:wght@400;500;600;700;800|JetBrains+Mono:wght@400;500)

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
```

### Spacing Variables

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` / `0.25rem` | Tight gaps |
| `--space-sm` | `8px` / `0.5rem` | Icon gaps, inline spacing |
| `--space-md` | `16px` / `1rem` | Standard padding |
| `--space-lg` | `24px` / `1.5rem` | Section padding |
| `--space-xl` | `32px` / `2rem` | Large gaps |
| `--space-2xl` | `48px` / `3rem` | Section margins |
| `--space-3xl` | `64px` / `4rem` | Hero padding |
| `--space-4xl` | `120px` / `7.5rem` | Section dividers |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `none` | No shadows in dark mode |
| `--shadow-md` | `0 1px 3px rgba(0,0,0,0.3)` | Cards only |
| `--shadow-lg` | `0 4px 12px rgba(0,0,0,0.4)` | Modals, dropdowns |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: #3B82F6;
  color: white;
  padding: 14px 32px;
  border-radius: 8px;
  font-family: 'Outfit', sans-serif;
  font-weight: 600;
  font-size: 16px;
  letter-spacing: -0.01em;
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  background: #2563EB;
  transform: translateY(-1px);
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: #FAFAFA;
  border: 1px solid rgba(255,255,255,0.15);
  padding: 14px 32px;
  border-radius: 8px;
  font-family: 'Outfit', sans-serif;
  font-weight: 500;
  font-size: 16px;
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-secondary:hover {
  border-color: rgba(255,255,255,0.4);
  background: rgba(255,255,255,0.05);
}
```

### Cards

```css
.card {
  background: #111111;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 32px;
  transition: all 300ms ease;
  cursor: pointer;
}

.card:hover {
  background: #181818;
  border-color: rgba(255,255,255,0.12);
  transform: translateY(-4px);
}
```

### Code Blocks

```css
.code-block {
  background: #0D1117;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 24px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  line-height: 1.7;
  overflow-x: auto;
}
```

---

## Style Guidelines

**Style:** Exaggerated Minimalism × Dark Mode OLED

**Keywords:** Dark, minimal, bold typography, oversized text, high contrast, negative space, geometric, professional, precise

**Best For:** Developer tools, API platforms, tech infrastructure, engineering products, SaaS, B2B

**Key Effects:** Oversized typography (clamp 3rem-8rem), repeating text matrix background, scroll-triggered fade-in, subtle hover lifts, 200-600ms transitions, backdrop-blur navbar

### Page Pattern

**Pattern Name:** Single Column Vertical + Bento Grid Showcase

- **Conversion Strategy:** Hero statement → Problem/Value → Feature showcase → Quick start → CTA. Single vertical flow, minimal navigation.
- **CTA Placement:** Hero center (dual CTA: primary + secondary), repeated in footer
- **Section Order:** 1. Hero (100vh, text matrix background), 2. What (3-sentence intro), 3. Features (Bento Grid), 4. Quick Start (code block), 5. Status (optional), 6. Footer
- **Color Strategy:** OLED dark (#080808) dominant, blue (#3B82F6) accent for CTAs, green (#22C55E) for status indicators. No gradients, no box shadows — pure flat dark with 1px hairline borders.
- **Typography:** Outfit (Display/Heading) + Inter (Body) + JetBrains Mono (Code). Giant hero text with tracking-tighter, body text with leading-relaxed.

---

## Anti-Patterns (Do NOT Use)

- ❌ Flat design without depth (we use subtle lifts, not shadows)
- ❌ Text-heavy pages
- ❌ Gradients or colorful backgrounds
- ❌ Box shadows in dark mode
- ❌ More than 2 accent colors

### Additional Forbidden Patterns

- ❌ **Emojis as icons** — Use SVG icons (Lucide, Heroicons)
- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y
- ❌ **Scroll-jacking** — Never force scroll behavior
- ❌ **Infinite animations on UI elements** — Only for hero background and status indicators

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Dark mode: text contrast 4.5:1 minimum (achieved: #FAFAFA on #080808 = 18:1)
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile
- [ ] Page load < 2s (Lighthouse)
