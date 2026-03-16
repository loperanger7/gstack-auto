# UFC Odds · Risk Intel Dashboard

A single-page web app for UFC fans who wager on marquee fights. Shows win/loss betting odds from multiple sources with a focus on **minimizing risk of loss** and **understanding upset potential**. Information only — no bet placement.

## Customer Story
I watch UFC. I like to consider wagering on marquee fights. I want to have the lowest risk of losing my money on a fighter. Understanding upset potential is very important to me.

## Data Sources

1. **Polymarket** — prediction market odds for UFC fights
2. **DraftKings** — traditional sportsbook moneyline odds
3. **FanDuel** — traditional sportsbook moneyline odds

Use The Odds API (https://the-odds-api.com) for DraftKings and FanDuel data. The free tier gives 500 requests/month. API key entry should be a simple input field at the top of the page that persists in localStorage.

For Polymarket, use their public CLOB API: `https://clob.polymarket.com` — search for UFC-related markets. No API key needed.

## What the User Sees

### Safest Bets Summary (top of page)
- A summary panel listing the fights with the lowest upset risk, ranked by favorite's consensus probability
- Filter out toss-ups and upset-alert fights — only show fights where there's a clear, agreed-upon favorite
- Also show an "Upset Watch" section calling out fights where the underdog has a realistic path to winning

### Fight Cards
- Show upcoming UFC events grouped by card (e.g., "UFC 315 — March 22, 2026")
- Each fight shows both fighters' names and odds from each source

### Risk Classification
Tag each fight with a risk badge based on the favorite's consensus probability:
- **Lock** (≥75%) — heavy favorite, low upset risk, sources agree
- **Lean** (60–74%) — clear favorite but not dominant
- **Toss-Up** (45–59%) — coin flip, high uncertainty
- **Upset Alert** — the 95% CI crosses 50%, or sources disagree significantly while the margin is thin. The underdog has a real shot.

### Upset Potential Meter
For each fight, show an upset potential score (0–100) as a horizontal bar:
- Factors: closeness to 50/50, CI width (wider = more uncertain), source disagreement
- Fights scoring ≥50 show a warning naming the underdog: "⚠ [Fighter] can win this"
- Color: green (low), yellow (moderate), red (high)

### Source Disagreement Indicator
Show how much the books agree or disagree on each fight:
- Compute the max spread in implied probability across sources for the favorite
- "Strong consensus" (<3% spread), "Some disagreement" (3–8%), "Books disagree significantly — line is unsettled" (>8%)
- Wider disagreement = more upset potential, because the market hasn't settled

### Odds Display
- Show American odds (e.g., -150 / +130) from each source
- Convert odds to implied probability and display as a percentage
- Color code: favorite vs underdog in distinct colors

### Confidence Interval
- For each fight, compute a consensus implied probability by averaging across all available sources
- Show a 95% confidence interval derived from the spread between sources:
  - Mean = average implied probability across sources
  - Standard deviation = std dev of implied probabilities
  - 95% CI = mean ± 1.96 × std dev
- Display as a horizontal bar/gauge showing the probability range for each fighter
- If only one source has data, show the single probability with a note "single source — no CI available"

### Edge Cases
- If The Odds API key is missing, show a message and only show Polymarket data
- If Polymarket has no UFC markets, show a note
- If no data from any source, show: "No upcoming UFC odds found. Check back closer to fight night."

## Design Direction
- GitHub-dark theme (#0d1117 background)
- Emerald green (#10b981) as the single accent color
- Typography-driven: large probability percentages, monospace for numbers
- Minimal dataviz: probability gauges with CI glow overlays
- Hover to reveal source-level detail per fight
- Mobile-responsive

## Tech Stack
- Single HTML file with embedded CSS and JS (no build tools)
- Fetch API for HTTP requests
- sessionStorage cache with 15-min TTL
- No frameworks, no dependencies

## What This Does NOT Do
- No bet placement or linking to betting sites
- No historical odds tracking
- No prop bets (over/under, method of victory, round betting)
- No user accounts or authentication
