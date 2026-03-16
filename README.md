# gstack-auto

**An RL engine for software development.**

## Why This Exists

Most AI coding tools work like an intern: you tell them what to do, line by line, and they do it. That's useful. But it's not how great software gets built.

Great software gets built through iteration. You try something, you test it, you find bugs, you fix them, you try again. The best version emerges from the process — not from a single prompt.

gstack-auto is that process, automated.

You write a product spec in plain English. gstack-auto spawns N parallel implementations — each one plans, builds, reviews, QA tests, fixes bugs, and scores itself. At the end, you get a ranked email with the results. The best implementation wins.

Think of it like biological evolution for code. Multiple organisms, same environment, survival of the fittest. Except instead of millions of years, it takes about 30 minutes.

## What It Actually Does

```
  product-spec.md  →  N parallel builds  →  ranked results email
```

Each build goes through 12 phases:

1. **Plan** — CEO-level product thinking
2. **Plan** — Engineering architecture
3. **Build** — Write the code
4. **Review** — Code review
5. **Ship** — Package and prepare
6. **QA** — Automated testing with screenshots
7-11. **Bug fix loop** — Find bugs, fix them, verify (up to 3 cycles)
12. **Score** — Rate on 5 dimensions, write a retrospective

Every build runs in its own git worktree. Completely isolated. They can't see each other. At the end, gstack-auto reads all the scores, ranks the builds, and emails you the results.

## Getting Started

You'll need three things set up on your computer. If you've never done this before, don't worry — I'll walk you through each one.

### 1. Install Conductor

Conductor is the AI development environment that gstack-auto runs on. Go to [conductor.build](https://conductor.build), download the app, and install it.

Once installed, open Conductor. It will walk you through signing in and connecting to Claude.

### 2. Install gstack

gstack-auto is built on top of gstack (a skill system for Conductor). Open a Conductor workspace and run:

```
/install gh:garrytan/gstack
```

### 3. Set Up Email

gstack-auto emails you the results when it's done. You need a Gmail account with an App Password.

**Create a Gmail App Password:**
1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Make sure 2-Factor Authentication is ON
3. Search for "App Passwords" in the security page
4. Create a new app password — name it "gstack-auto"
5. Copy the 16-character password Google gives you

**Configure gstack-auto:**

In your terminal (you can open one inside Conductor), run:

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in your credentials:

```
PATTAYA_SMTP_USER=your-email@gmail.com
PATTAYA_SMTP_PASS=your-16-char-app-password
```

Also update `pipeline/config.yml` — change the `email.to` field to your email address.

**Test that email works:**

```bash
python3 scripts/send-email.py --probe
```

If you see "SMTP probe succeeded" — you're good.

### 4. Write Your Spec

Open `product-spec.md` and describe what you want built. Be specific. Here's what a good spec looks like:

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

The more specific you are, the better the output. Vague specs produce vague software.

### 5. Run It

In your Conductor workspace, tell Claude:

```
Run the gstack-auto pipeline with N=3
```

That's it. Go get coffee. Come back in 30 minutes. Check your email.

## What You'll Get

An email with:
- **Ranked results** — each build scored on Functionality, Code Quality, Test Coverage, UX Polish, and Spec Adherence
- **Score cards** with ASCII bar charts
- **"Why I Built It This Way"** — each build explains its architectural choices
- **Code highlights** — the most elegant piece from each build
- **Git branches** — so you can check out any build and keep working on it

The winning build lives in `output/run-{letter}/`. Open its `index.html` and see what you got.

## Configuration

Everything is in `pipeline/config.yml`:

```yaml
parallel_runs: 3          # How many builds to run simultaneously
max_fix_cycles: 3          # Max bug-fix attempts before forced scoring
email:
  to: "you@gmail.com"
  method: "smtp"           # or "file-only" to skip email
```

## Validation

Run the test suite to make sure everything is wired up correctly:

```bash
bash tests/validate-pipeline.sh
```

All checks should pass before you run the pipeline.

## Philosophy

The insight behind gstack-auto is simple: **the best way to get great software from AI is the same way you get great software from humans — iterate, compete, and select.**

One AI attempt might get lucky. Three attempts with scoring and selection will consistently produce better results than any single attempt, no matter how good the prompt.

This is reinforcement learning applied to the development process itself. Not at the token level — at the product level.

---

Built with [Conductor](https://conductor.build) and [gstack](https://github.com/garrytan/gstack).
