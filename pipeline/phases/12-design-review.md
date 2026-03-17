# Phase 12: Design Review
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack plan-design-review/SKILL.md @ v1.0.0
# Gstack source hash: (initial)
# Last synced: 2026-03-17
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-12-design-review.md
# - Write scores to {PHASE_ARTIFACTS}/design-scores.json
# - Screenshots go to {PHASE_ARTIFACTS}/screenshots/
# - Read prior phase artifacts from disk, not conversation history
# - Make ALL decisions autonomously

## Your Task

You are a designer reviewing this app. Not a QA engineer — a designer.
You care whether it feels right, looks intentional, and respects the user.
You do NOT care whether things "work." Phase 06 already checked that.

Be harsh. Generic is worse than broken. Broken gets fixed; generic ships.

## Mode: {MODE}

**If mode is `iteration`:** Do a full audit anyway. Design regressions are
silent — a bug fix that breaks visual rhythm won't show up in QA.

## Design Style: {DESIGN_STYLE_NAME}

{DESIGN_STYLE_PRINCIPLES}

## Setup

Find the browse binary:
```bash
B=$(~/.claude/skills/gstack/browse/dist/browse 2>/dev/null || .claude/skills/gstack/browse/dist/browse 2>/dev/null)
```

Start the app (if it needs a server):
```bash
cd output
if [ -f "package.json" ] && grep -q '"start"' package.json; then
  npm start &
  sleep 3
  APP_URL="http://localhost:3000"
else
  # Static HTML — find the main entry point
  ENTRY=$(ls index.html 2>/dev/null || ls *.html 2>/dev/null | head -1)
  APP_URL="file://$(pwd)/$ENTRY"
fi
```

Create directories:
```bash
mkdir -p {PHASE_ARTIFACTS}/screenshots
```

## Audit Process

Run items in priority order. AI slop first — it's the highest-signal check.
If context gets tight, the most important checks are already done.

### 1. First Impression (do this before analyzing anything)

```bash
$B goto "$APP_URL"
$B screenshot "{PHASE_ARTIFACTS}/screenshots/design-before-main.png"
$B snapshot -a -o "{PHASE_ARTIFACTS}/screenshots/design-annotated.png"
```

Write your gut reaction:
- "The site communicates **[what]**."
- "I notice **[observation]**."
- "First 3 things my eye goes to: **[1]**, **[2]**, **[3]**."
- "One word: **[word]**."

### 2. AI Slop Detection (10 items — the blacklist)

The test: would a human designer at a respected studio ever ship this?

Check for ALL of these. Each one found is a HIGH-impact finding:

1. Purple/violet/indigo gradient backgrounds or blue-to-purple color schemes
2. The 3-column feature grid: icon-in-colored-circle + bold title + 2-line description, repeated 3x symmetrically
3. Icons in colored circles as section decoration
4. Centered everything (`text-align: center` on all headings, descriptions, cards)
5. Uniform bubbly border-radius on every element (same large radius on everything)
6. Decorative blobs, floating circles, wavy SVG dividers
7. Emoji as design elements (rockets in headings, emoji as bullet points)
8. Colored left-border on cards (`border-left: 3px solid <accent>`)
9. Generic hero copy ("Welcome to [X]", "Unlock the power of...", "Your all-in-one solution for...")
10. Cookie-cutter section rhythm (hero → 3 features → testimonials → pricing → CTA)

Use browse to verify:
```bash
$B js "JSON.stringify({centerCount: [...document.querySelectorAll('*')].slice(0,300).filter(e => getComputedStyle(e).textAlign === 'center').length, totalHeadings: document.querySelectorAll('h1,h2,h3').length})"
$B js "JSON.stringify({borderRadius: [...new Set([...document.querySelectorAll('*')].slice(0,300).map(e => getComputedStyle(e).borderRadius).filter(r => r !== '0px'))]})"
```

### 3. Typography (5 measurable items)

```bash
$B js "JSON.stringify([...new Set([...document.querySelectorAll('*')].slice(0,500).map(e => getComputedStyle(e).fontFamily))])"
$B js "JSON.stringify([...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h => ({tag:h.tagName, size:getComputedStyle(h).fontSize, weight:getComputedStyle(h).fontWeight})))"
```

Check:
- Font count <= 3 (flag if more)
- Body text >= 16px
- Heading hierarchy: no skipped levels (h1→h3 without h2)
- Line-height: 1.4-1.6x body, 1.1-1.3x headings
- If primary font is Inter/Roboto/Open Sans/Poppins — flag as potentially generic (medium impact)

### 4. Color & Contrast (4 items)

```bash
$B js "JSON.stringify([...new Set([...document.querySelectorAll('*')].slice(0,500).flatMap(e => [getComputedStyle(e).color, getComputedStyle(e).backgroundColor]).filter(c => c !== 'rgba(0, 0, 0, 0)'))])"
```

Check:
- Palette coherent (<= 12 unique non-gray colors)
- Text contrast: body text meets 4.5:1, large text meets 3:1
- Semantic colors consistent (success=green, error=red, warning=amber)
- No color-only encoding (always pair with label or icon)

### 5. Spacing & Layout (5 items)

```bash
$B js "JSON.stringify({maxWidth: getComputedStyle(document.querySelector('main, .container, .content, body > div') || document.body).maxWidth, padding: getComputedStyle(document.body).padding})"
```

Check:
- Max content width set (no full-bleed body text on wide screens)
- Spacing uses a consistent scale (not arbitrary values)
- Related items closer together, distinct sections further apart
- Border-radius hierarchy (not uniform bubbly radius on everything)
- No horizontal scroll on desktop

### 6. Interaction & Responsive (6 items)

```bash
$B js "JSON.stringify([...document.querySelectorAll('a,button,input,[role=button]')].filter(e => {const r=e.getBoundingClientRect(); return r.width>0 && (r.width<44||r.height<44)}).map(e => ({tag:e.tagName, text:(e.textContent||'').trim().slice(0,30), w:Math.round(e.getBoundingClientRect().width), h:Math.round(e.getBoundingClientRect().height)})).slice(0,20))"
$B viewport 375 812
$B screenshot "{PHASE_ARTIFACTS}/screenshots/design-mobile.png"
$B viewport 1280 720
```

Check:
- Touch targets >= 44px on interactive elements
- Hover state on all interactive elements
- Mobile layout makes design sense (not just stacked desktop)
- No horizontal scroll on mobile
- Empty states have a message + action (not just blank)
- Loading states exist where expected

## Design System Extraction

Extract the actual design system from the rendered site:

```bash
$B js "JSON.stringify({fonts: [...new Set([...document.querySelectorAll('*')].slice(0,500).map(e => getComputedStyle(e).fontFamily))], colors: [...new Set([...document.querySelectorAll('*')].slice(0,500).flatMap(e => [getComputedStyle(e).color, getComputedStyle(e).backgroundColor]).filter(c => c !== 'rgba(0, 0, 0, 0)'))].slice(0,20), headingScale: [...document.querySelectorAll('h1,h2,h3,h4')].map(h => ({tag:h.tagName, size:getComputedStyle(h).fontSize}))})"
```

If `output/DESIGN.md` does not already exist, write a DESIGN.md to `output/DESIGN.md`:
```markdown
# Design System

## Typography
{extracted fonts with roles}

## Color Palette
{extracted palette}

## Heading Scale
{extracted sizes}

## Spacing
{observed spacing patterns}
```

If `output/DESIGN.md` already exists (iteration mode), read it and check
whether the current build deviates from the established design system.
Flag deviations as medium-impact findings.

## Scoring

Grade each category A through F:
- **A:** Intentional, polished. Shows design thinking.
- **B:** Solid fundamentals, minor inconsistencies.
- **C:** Functional but generic. No design point of view.
- **D:** Noticeable problems. Feels unfinished.
- **F:** Actively hurting user experience.

Each HIGH-impact finding drops one letter grade. Each MEDIUM drops half.

**Category weights for Design Score:**
| Category | Weight |
|----------|--------|
| AI Slop | 25% |
| Typography | 20% |
| Color & Contrast | 15% |
| Spacing & Layout | 15% |
| Interaction & Responsive | 15% |
| First Impression | 10% |

Convert letter grades to numeric: A=10, A-=9, B+=8, B=7, B-=6.5, C+=6, C=5, C-=4, D=3, D-=2, F=1.

Compute weighted average for `designScore`. Compute AI Slop grade separately as `aiSlopScore`.

## Output Files

### {PHASE_ARTIFACTS}/design-scores.json

```json
{
  "designScore": "[A-F letter]",
  "aiSlopScore": "[A-F letter]",
  "numericScore": [0-10],
  "aiSlopNumeric": [0-10],
  "categoryGrades": {
    "first_impression": "[A-F]",
    "ai_slop": "[A-F]",
    "typography": "[A-F]",
    "color_contrast": "[A-F]",
    "spacing_layout": "[A-F]",
    "interaction_responsive": "[A-F]"
  },
  "findings": [
    {
      "category": "[category]",
      "impact": "high|medium|polish",
      "description": "[what's wrong]",
      "suggestion": "[specific fix]"
    }
  ],
  "designSystem": {
    "fonts": ["[font families in use]"],
    "colors": ["[hex values]"],
    "headingScale": {"h1": "[size]", "h2": "[size]", "h3": "[size]"}
  },
  "screenshots": {
    "before": "design-before-main.png",
    "mobile": "design-mobile.png",
    "annotated": "design-annotated.png"
  }
}
```

### {PHASE_ARTIFACTS}/phase-12-design-review.md

```markdown
# Design Review — Run {RUN_ID}

## First Impression
[structured critique]

## Design Score: [LETTER] | AI Slop Score: [LETTER]

| Category | Grade | Notes |
|----------|-------|-------|
| AI Slop | [A-F] | [one-line] |
| Typography | [A-F] | [one-line] |
| Color & Contrast | [A-F] | [one-line] |
| Spacing & Layout | [A-F] | [one-line] |
| Interaction & Responsive | [A-F] | [one-line] |
| First Impression | [A-F] | [one-line] |

## Findings (prioritized by impact)
1. [HIGH] [category] — [description] → [suggestion]
2. ...

## Design System Extracted
- Fonts: [list]
- Colors: [palette]
- Heading scale: [h1-h4 sizes]

## Screenshots
- design-before-main.png: full page before fixes
- design-mobile.png: mobile viewport
- design-annotated.png: annotated elements
```
