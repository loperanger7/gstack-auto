# Design System — gstack Reply Queue

## Color Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `bg-primary` | `#0d1117` | Page background, input backgrounds |
| `bg-surface` | `#161b22` | Card backgrounds, stat cards, table headers |
| `bg-hover` | `#1c2128` | Hover state on variant rows |
| `border-default` | `#30363d` | Card borders, input borders, button borders |
| `border-subtle` | `#21262d` | Table row dividers, tweet text box border |
| `text-primary` | `#c9d1d9` | Body text |
| `text-emphasis` | `#f0f6fc` | Author names, headings |
| `text-muted` | `#8b949e` | Follower count, labels, empty state |
| `accent` | `#58a6ff` | Links, headings, radio accent, stat values |
| `success` | `#238636` | Approve button background |
| `success-hover` | `#2ea043` | Approve button hover |
| `success-text` | `#3fb950` | Praise sentiment text, green char count |
| `success-bg` | `#1f3d2a` | Praise sentiment badge bg, green char count bg |
| `error-text` | `#f85149` | Criticism sentiment text, red char count, skip hover |
| `error-bg` | `#3d1f1f` | Criticism sentiment badge bg, red char count bg |
| `warning-text` | `#d29922` | Yellow char count text |
| `warning-bg` | `#3d2e1f` | Yellow char count bg |
| `question-text` | `#58a6ff` | Question sentiment text |
| `question-bg` | `#1c2d4a` | Question sentiment badge bg |
| `neutral-text` | `#8b949e` | Neutral sentiment text |
| `neutral-bg` | `#282830` | Neutral sentiment badge bg |

## Typography

| Element | Font | Size | Weight | Color |
|---------|------|------|--------|-------|
| Page heading (h1) | System sans | 1.4rem | default | `accent` |
| Section heading (h2) | System sans | 1.1rem | default | `text-emphasis` |
| Author name | System sans | inherit | 600 | `text-emphasis` |
| Follower count | System sans | 0.85rem | default | `text-muted` |
| Tweet text | SF Mono, Menlo | 0.9rem | default | `text-primary` |
| Variant text | SF Mono, Menlo | 0.85rem | default | `text-primary` |
| Char count badge | System sans | 0.75rem | 600 | traffic-light color |
| Sentiment badge | System sans | 0.75rem | 600 | sentiment color |
| Button text | System sans | 0.85rem | 500 | varies |
| Select text | System sans | 0.85rem | default | `text-primary` |
| Stat value | System sans | 1.6rem | 700 | `accent` |
| Stat label | System sans | 0.8rem | default | `text-muted` |
| Table cell | System sans | 0.85rem | default | `text-primary` |
| Table header | System sans | 0.85rem | 600 | `text-muted` |

**Font stacks:**
- Sans: `-apple-system, system-ui, sans-serif`
- Mono: `'SF Mono', Menlo, monospace`

## Border Radius

| Element | Radius |
|---------|--------|
| Card | 8px |
| Stat card | 8px |
| Table | 8px |
| Sentiment badge | 12px (pill) |
| Button | 6px |
| Input / Select | 6px |
| Tweet text box | 4px |
| Char count badge | 4px |
| Variant hover | 4px |

## Spacing

| Token | Value | Usage |
|-------|-------|-------|
| Page padding | 1rem | Body padding |
| Max content width | 800px | Body max-width |
| Card padding | 1rem | Internal card padding |
| Card gap | 1.2rem | Vertical space between cards |
| Section heading margin | 1.2rem top, 0.6rem bottom | Stats page h2 |
| Action bar gap | 0.5rem | Between buttons |
| Variant padding | 0.5rem | Variant row padding |
| Variant gap | 0.5rem | Between radio and text |
| Variant margin | 0.3rem bottom | Between variant rows |
| Stat grid gap | 0.8rem | Between stat cards |
| Stat grid column min | 140px | Grid auto-fit minimum |

## Components

### Card
Dark surface with 1px border, 8px radius, 1rem padding. Contains:
header (flex, space-between), tweet text (mono, dark bg), variants list, action bar.

### Sentiment Badge
Pill shape (12px radius), 2px/8px padding, uppercase 0.75rem bold.
Four variants: praise (green), question (blue), criticism (red), neutral (gray).

### Character Count Badge
Inline pill, 0.75rem bold, 2px/6px padding, 4px radius.
Three states: green (<=260), yellow (261-270), red (271+).

### Button
6px radius, 1px border, 0.85rem 500-weight text, 0.4rem/0.8rem padding.
Three variants: approve (green fill), edit (transparent, blue text), skip (transparent, gray text, red on hover).

### Stat Card
Surface bg, 1px border, 8px radius, 0.8rem padding, centered.
Large blue number (1.6rem 700) over small gray label (0.8rem).

### Empty State
Centered text, 3rem/1rem padding, muted color, 1.1rem.

## Round 2 UX Improvements

### Navigation Bar
Shared `<nav>` on both dashboard and stats with active link indicator (2px bottom border).
Health dot (green/yellow pulse) shows system status. Pending count badge in nav.

### AJAX Approve/Skip
Form submissions intercepted by `fetch()` for smooth card exit animation (slide up + fade out,
300ms transition). Toast notification on success/error. Falls back to full-page POST if JS disabled.

### Keyboard Shortcuts
`j`/`k` navigate cards, `a` approve, `s` skip, `e` edit, `1`/`2`/`3` select variant.
Disabled when typing in textarea/input. Subtle kbd hint at bottom of page.

### Auto Send Window
Pre-selects nearest ET send window based on current time.

### Character Count Polish
Pulse animation (`char-pulse`) on count badge when approaching 280 chars.
CSS transition on color/background changes.

### Card Focus
Focused card gets blue left border for keyboard navigation visual feedback.

### Stats Bar Chart
Pure CSS horizontal bar chart below send window table. Width proportional to max replies.

### Stats Grid
Changed from `repeat(3,1fr)` to `repeat(auto-fit,minmax(140px,1fr))` with `repeat(2,1fr)` mobile fallback.

### Favicon
Inline SVG lightning bolt favicon on both pages.

## Priority Tier Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `tier-hot-border` | `#d4a574` | Gold left border on hot-tier cards |
| `tier-hot-badge-bg` | `#3d2e1f` | Hot pill badge background |
| `tier-hot-badge-text` | `#d4a574` | Hot pill badge text |
| `tier-warm-border` | `#58a6ff` | Blue left border on warm-tier cards |
| `tier-normal` | (none) | No special treatment |

### Priority Tier Classification

| Tier | Threshold | Visual Treatment |
|------|-----------|-----------------|
| Hot | >= 50,000 followers | Gold left border, "Hot" pill badge |
| Warm | >= 10,000 followers | Blue left border, no badge |
| Normal | < 10,000 followers | Default card styling |

Thresholds are configurable via `HOT_TWEET_THRESHOLD` and `WARM_TWEET_THRESHOLD` env vars.

### Tier Component Spec

- **Hot card**: 3px left border `#d4a574`, pill badge "Hot" (12px radius, uppercase, 0.75rem bold)
- **Warm card**: 3px left border `#58a6ff`, no badge
- **Normal card**: default 1px border
- **Mobile (<=480px)**: left border becomes top border
- **Animation**: card fade-in 200ms ease-out
- **WCAG AA**: Gold `#d4a574` on `#161b22` = 5.2:1 contrast ratio (passes AA)
- **WCAG AA**: Blue `#58a6ff` on `#161b22` = 5.4:1 contrast ratio (passes AA)

## Resolved Design Issues (from Phase 11 Review)

1. ~~No navigation~~ -- FIXED: Shared nav bar with active state on both pages
2. ~~No loading states~~ -- FIXED: AJAX with card animation + sending button state
3. ~~No skip confirmation~~ -- WAS ALREADY PRESENT: `confirm()` dialog existed in Round 1
4. ~~Stats grid orphan~~ -- FIXED: `auto-fit` with `minmax(140px,1fr)` + mobile breakpoint
5. ~~Stat values lack semantic color~~ -- FIXED: Each status has its own color class
6. ~~line-height unset~~ -- FIXED: `line-height:1.5` on body
7. ~~No letter-spacing on badges~~ -- FIXED: `letter-spacing:.04em` on sentiment badges
8. ~~Toast unused~~ -- FIXED: Toast used for AJAX approve/skip feedback + URL param fallback
9. ~~No system health on dashboard~~ -- FIXED: Health dot with pulse animation + last cycle time
