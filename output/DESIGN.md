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

## Known Design Issues (Phase 11 Review)

1. **No navigation** — Dashboard has no link to stats page; stats has "Back to Dashboard" only
2. **No loading states** — Approve/skip are full page reloads with no feedback
3. **No skip confirmation** — Skip is permanent, single click, no undo
4. **Stats grid orphan** — 6 stat cards with auto-fit wraps to 5+1 layout
5. **Stat values lack semantic color** — All blue; should be green (replied), red (stale), etc.
6. **line-height unset** — All elements use browser default (~1.2), dense on long text
7. **No letter-spacing on badges** — Uppercase .75rem text runs tight
8. **Toast unused** — `style.css` defines `.toast` but templates never reference it
9. **No system health on dashboard** — No last-poll time, queue depth, or auto-refresh
