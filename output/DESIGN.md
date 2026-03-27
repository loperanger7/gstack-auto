# Design System — What to Wear

## Philosophy
Playful warmth meets Dieter Rams clarity. Every element earns its place,
but the personality comes through in conversational copy, weather-reactive
color palettes, and smooth micro-interactions.

## Color Palettes (weather-reactive)
Background gradient and accent shift based on conditions:

| Condition  | Background          | Accent  | Text    |
|-----------|---------------------|---------|---------|
| Clear     | #FFD700 → #FF8C00   | #FF6B35 | Dark    |
| Cloudy    | #87CEEB → #B0C4DE   | #5B8FB9 | Dark    |
| Fog       | #C8C8C8 → #A0A0A0   | #708090 | Dark    |
| Drizzle   | #9B8EC1 → #7B68AE   | #DDA0DD | Light   |
| Rain      | #6A5ACD → #483D8B   | #9370DB | Light   |
| Snow      | #E8E8FF → #B0C4DE   | #4169E1 | Dark    |
| Thunder   | #2F2F4F → #191932   | #FFD700 | Light   |

## Typography
- Font: System stack (-apple-system, BlinkMacSystemFont, Segoe UI)
- Temperature: 3.5rem bold tabular-nums
- Body: 1.1rem medium
- Labels: 0.75rem uppercase tracking
- Vibe copy: 1rem italic

## Spacing
8px grid: 4, 8, 16, 24, 32

## Layout
- Max-width: 420px centered
- Mobile-first single column
- Card-based sections with 16px border-radius
- Backdrop blur on cards for depth

## Accessibility
- prefers-reduced-motion respected
- All text meets WCAG AA on each palette (precomputed)
- Semantic HTML landmarks
- ARIA labels on interactive elements
- Min touch targets: 48px
