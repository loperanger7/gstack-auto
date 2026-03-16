# gstack-auto

Reinforcement learning applied to the development process itself. Not at the token level — at the product level.

You write a spec. gstack-auto spawns parallel implementations, each one planning, building, reviewing, testing, and fixing bugs autonomously. The best one wins. Then it does it again, starting from the winner's code. Each round gets better.

```
  product-spec.md
        |
        v
  +-- ROUND LOOP (1..R) --------------------------------+
  |                                                      |
  |   +-- N PARALLEL RUNS ----------------------------+  |
  |   |  Each run: plan > build > review > QA > fix   |  |
  |   |  Run A biases toward code quality             |  |
  |   |  Run B biases toward UX polish                |  |
  |   |  Run C biases toward robustness               |  |
  |   +-----------------------------------------------+  |
  |          |                                           |
  |          v                                           |
  |   SELECT WINNER (by score, bugs, fix cycles)         |
  |   Commit to git. Feed into next round.               |
  |                                                      |
  +------------------------------------------------------+
        |
        v
  RESULTS: dashboard + email + git history
```

## How Rounds Work

Round 1 builds your app from scratch. Three parallel attempts, scored independently. The best one wins.

Round 2 takes the winner's code and improves it. Three more parallel attempts, each starting from that codebase. The best improvement wins.

Round 3 does it again. Scores go up. Bugs go down. Each round's winner is committed to git with a full score card — you can see the progression.

```
Round 1: Best 7.2/10 (run-b)  ==============        72%
Round 2: Best 8.4/10 (run-a)  ================       84%  (+1.2)
Round 3: Best 9.1/10 (run-c)  ==================     91%  (+0.7)
```

## The 12 Phases

Each build goes through:

1. **Plan** — CEO-level product thinking
2. **Plan** — Engineering architecture
3. **Build** — Write the code
4. **Review** — Code review
5. **Ship** — Package and prepare
6. **QA** — Automated testing with screenshots
7-11. **Bug fix loop** — Find, fix, verify (up to 3 cycles)
12. **Score** — Rate on 5 dimensions, write a retrospective

Every build runs in its own git worktree. Completely isolated. They can't see each other.

## Getting Started

### 1. Prerequisites

Install [Conductor](https://conductor.build) (the AI development environment) and [gstack](https://github.com/garrytan/gstack) (the skill system). In Claude Code:

> Install gstack: run `git clone https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup` then add a "gstack" section to CLAUDE.md that says to use the /browse skill from gstack for all web browsing, never use mcp\_\_claude-in-chrome\_\_\* tools, and lists the available skills: /plan-ceo-review, /plan-eng-review, /review, /ship, /browse, /qa, /setup-browser-cookies, /retro. Then ask the user if they also want to add gstack to the current project so teammates get it.

### 2. Configure

Edit `product-spec.md` with what you want built. Be specific:

```markdown
# Product Spec

## What It Does
A personal bookshelf app where I can track books I've read
and want to read, with a simple rating system.

## Core Interaction
User opens the page and sees two lists: "Want to Read" and "Read."
They can add books by title, move them between lists, and rate
books they've read from 1-5 stars.

## Constraints
- Pure HTML/CSS/JS, no frameworks
- Data stored in localStorage
- Must work on mobile
```

Vague specs produce vague software.

**Email (optional):** Copy `.env.example` to `.env`, add your [Gmail App Password](https://myaccount.google.com/security), and update `email.to` in `pipeline/config.yml`. Run `python3 scripts/send-email.py --probe` to verify. Or set `email.method: "file-only"` and skip it — results are always saved to disk.

### 3. Run

```
Run the gstack-auto pipeline with N=3
```

Go get coffee. Come back in 30 minutes.

## What You Get

**Dashboard** at `localhost:8000` — ranked score cards with winner crown, live app preview iframes, round-by-round progression with score deltas, and unified diff comparison between runs.

**Email** (if configured) — ASCII score bar charts, architectural narratives, code highlights, and git branch names for each run.

**Git history** — each round's winner committed with score card and feature summary. `git log` tells the story of how the code evolved.

The winning build lives in `output/`. Open its `index.html` and see what you got.

## Configuration

`pipeline/config.yml`:

```yaml
parallel_runs: 3          # How many builds to run simultaneously
rounds: 1                 # Sequential rounds (each improves on the last)
auto_accept_winner: true   # Auto-select best score (false = pick via dashboard)
max_fix_cycles: 3          # Max bug-fix attempts before forced scoring
style: "marlinspike"       # Engineering style (see pipeline/styles/)
email:
  to: "you@gmail.com"
  method: "smtp"           # or "file-only" to skip email
```

Available styles: `carmack`, `antirez`, `abramov`, `metz`, `holowaychuk`, `majors`, `marlinspike`. Each encodes concrete coding principles that guide implementation, review, and scoring. Or leave it blank for the default.

## Validation

```bash
bash tests/validate-pipeline.sh
```

All 136 checks should pass before you run the pipeline.

---

Built with [Conductor](https://conductor.build) and [gstack](https://github.com/garrytan/gstack).

Special thanks to [Garry Tan](https://github.com/garrytan) for building [gstack](https://github.com/garrytan/gstack) — the skill system that makes this entire pipeline possible.
