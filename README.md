# Akshant · 150-Day Plan (local only)

Private master calendar for the platform build. **Do not push this folder to GitHub** — it contains day-by-day plans, `data/plan.json`, and workflow artifacts.

**Public copy numbering:** Blogs use **X of N** (Experience calendar) and **N of N** (AI Learning series index). **N** is intentionally open-ended — not a fixed "150" in published posts. This site may still track ~150 internal calendar days in `plan.json` / generated HTML.

## Open locally

```bash
open index.html
# or
open checklist.html
```

## Daily workflow

1. **[checklist.html](checklist.html)** — interactive daily multi-agent checklist (browser).
2. **[CHECKLIST.md](CHECKLIST.md)** — same content, copy/paste into agent prompts.

**Rule:** Plan mode (3 parallel markdown plans) → user approval → implementation. Code and blogs live in [infra-ai-streaming](https://github.com/akshantvats/infra-ai-streaming) and [Profile](https://github.com/akshantvats/Profile).

## Regenerate plan pages

```bash
python3 generate_plan.py
```

Regenerates `index.html`, product/project pages, and `data/plan.json`. Does **not** overwrite `checklist.html` or `CHECKLIST.md`. Nav includes **Daily Checklist** when using the updated `generate_plan.py`.

## Set today's calendar day

Edit **`data/current-day.json`** (single source of truth):

```json
{ "current_day": 6 }
```

Then run `python3 generate_plan.py`. The master table, hero stats, and day detail blocks will show days `< current_day` as **Done**, day `current_day` as **Today**, and later days as **Pending**. Marking a day `done` in `plan.json` before bumping `current_day` is preserved across regenerations.

## Files

| File | Purpose |
|------|---------|
| `data/current-day.json` | Which calendar day is **Today** on the site |
| `data/plan.json` | Merged 150-day source (`current_day` + `days`) |
| `CHECKLIST.md` | Daily multi-agent framework (source of truth) |
| `checklist.html` | Checklist UI with local progress save |
| `generate_plan.py` | HTML generator |
