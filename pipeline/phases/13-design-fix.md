# Phase 13: Design Fix
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack qa-design-review/SKILL.md @ v1.0.0
# Gstack source hash: (initial)
# Last synced: 2026-03-17
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-13-design-fix.md
# - Screenshots go to {PHASE_ARTIFACTS}/screenshots/
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously

## Your Task

Fix the design issues found in Phase 12. You are a designer who codes.
Read the findings, fix the highest-impact ones first, verify each fix
visually. One pass — no loops. Do your best work and move on.

Cap at 10 fixes maximum. Prioritize by impact: HIGH first, then MEDIUM.
Skip POLISH items unless you have context budget left.

## Design Style: {DESIGN_STYLE_NAME}

{DESIGN_STYLE_PRINCIPLES}

## Setup

Find the browse binary:
```bash
B=$(~/.claude/skills/gstack/browse/dist/browse 2>/dev/null || .claude/skills/gstack/browse/dist/browse 2>/dev/null)
```

Start the app (same pattern as Phase 12):
```bash
cd output
if [ -f "package.json" ] && grep -q '"start"' package.json; then
  npm start &
  sleep 3
  APP_URL="http://localhost:3000"
else
  ENTRY=$(ls index.html 2>/dev/null || ls *.html 2>/dev/null | head -1)
  APP_URL="file://$(pwd)/$ENTRY"
fi
```

## Fix Process

### 1. Read the Design Review

Read `{PHASE_ARTIFACTS}/phase-12-design-review.md` and
`{PHASE_ARTIFACTS}/design-scores.json`.

Sort findings by impact (HIGH → MEDIUM → POLISH).

If Phase 12 found no issues (design score A or A-), skip to the output
section and write "No design fixes needed — design score already high."

### 2. Font Upgrade (if applicable)

Check if the app uses default/system fonts (Arial, Helvetica, Times,
Georgia, Courier, system-ui without a custom font loaded). If yes:

This is the single highest-leverage design fix. Good typography alone
takes an app from "AI prototype" to "someone designed this."

Pick a font pairing appropriate to the product:

**For dashboards/data apps:**
- Headings: Inter or DM Sans (clean, modern)
- Body: Inter or DM Sans (same family is fine)

**For content/editorial:**
- Headings: DM Serif Display or Fraunces
- Body: DM Sans or Source Sans 3

**For playful/consumer:**
- Headings: Space Grotesk or Plus Jakarta Sans
- Body: Same family

Add a Google Fonts link to the HTML `<head>`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family={Font}:wght@400;500;700&display=swap" rel="stylesheet">
```

Update the CSS to use the new font.

### 3. Fix Each Issue

For each finding (up to 10), in priority order:

1. Read the finding and suggestion
2. Edit the source file(s) in `output/`
3. Reload and screenshot to verify:
   ```bash
   $B goto "$APP_URL"
   $B screenshot "{PHASE_ARTIFACTS}/screenshots/design-fix-{N}.png"
   ```

**Common fixes by category:**

**AI Slop fixes:**
- Replace 3-column icon grid with asymmetric layout or list
- Remove decorative blobs/circles
- Replace centered-everything with left-aligned content
- Replace uniform border-radius with a hierarchy (sm/md/lg)
- Rewrite generic hero copy to be specific to the product

**Typography fixes:**
- Set body font-size to 16px minimum
- Set line-height to 1.5 for body text
- Add `text-wrap: balance` to headings
- Ensure heading hierarchy (no h1 → h3 skips)

**Color fixes:**
- Reduce palette to <= 8 intentional colors
- Fix contrast ratios (darken text or lighten backgrounds)

**Spacing fixes:**
- Set max-width on content container (960-1200px)
- Use consistent spacing scale (multiples of 4px or 8px)

**Responsive fixes:**
- Fix touch targets to >= 44px
- Ensure no horizontal scroll on 375px viewport

### 4. After All Fixes — Capture "After" Screenshot

```bash
$B goto "$APP_URL"
$B screenshot "{PHASE_ARTIFACTS}/screenshots/design-after-main.png"
$B viewport 375 812
$B screenshot "{PHASE_ARTIFACTS}/screenshots/design-after-mobile.png"
$B viewport 1280 720
```

## Output Format

Write your fix log to `{PHASE_ARTIFACTS}/phase-13-design-fix.md`:

```markdown
# Design Fix Log — Run {RUN_ID}

## Fixes Applied
1. [HIGH] [category] — [what was wrong] → [what you did] — [file:line]
2. ...

## Fixes Skipped (over cap or low impact)
- [POLISH] [description] — skipped: [reason]

## Font Upgrade
- Before: [font family]
- After: [font family] (from Google Fonts)
- Rationale: [why this pairing]

## Screenshots
- design-after-main.png: full page after all fixes
- design-after-mobile.png: mobile viewport after fixes
- design-fix-1.png through design-fix-N.png: individual fix verification

## Summary
FIXES_APPLIED: [count]
DESIGN_SCORE_BEFORE: [letter from Phase 12]
```
