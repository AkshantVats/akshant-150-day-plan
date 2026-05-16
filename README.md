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

## Files

| File | Purpose |
|------|---------|
| `data/plan.json` | Merged 150-day source |
| `CHECKLIST.md` | Daily multi-agent framework (source of truth) |
| `checklist.html` | Checklist UI with local progress save |
| `generate_plan.py` | HTML generator |
