#!/usr/bin/env python3
"""Generate 150-day multi-page HTML master plan (Days 0-149)."""
from __future__ import annotations

import html
import json
import time
from pathlib import Path

from plan_data import PRODUCTS, build_day
from plan_status import apply_statuses, load_current_day, load_saved_statuses

ROOT = Path(__file__).parent
DATA = ROOT / "data"
ASSETS = "assets/style.css"
FONTS = (
    "https://fonts.googleapis.com/css2?"
    "family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@300;400;500;600&display=swap"
)

PRODUCT_COLORS = {
    "lensai": "#00e5ff",
    "traceforge": "#ff6b35",
    "routeiq": "#a78bfa",
    "driftwatch": "#ffd700",
    "fineforge": "#00ff88",
}


def esc(s) -> str:
    return html.escape(str(s)) if s is not None else ""


def wait_for_json(timeout_sec: int = 120, interval_sec: int = 5) -> tuple[Path, Path]:
    p0, p1 = DATA / "plan-days-0-74.json", DATA / "plan-days-75-149.json"
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if p0.exists() and p1.exists():
            break
        time.sleep(interval_sec)
    return p0, p1


def load_half(path: Path) -> list[dict]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "days" in raw:
        return raw["days"]
    return raw if isinstance(raw, list) else []


def merge_days() -> list[dict]:
    DATA.mkdir(parents=True, exist_ok=True)
    p0, p1 = DATA / "plan-days-0-74.json", DATA / "plan-days-75-149.json"
    d0, d1 = load_half(p0), load_half(p1)
    saved = load_saved_statuses()

    if d0 and d1:
        by_day = {x["day"]: x for x in d0 + d1}
        print(f"Merged JSON: {len(d0)} + {len(d1)} days")
        days = [by_day[i] for i in range(150)]
    elif d0 and not d1:
        print("Merged: JSON 0-74 + plan_data 75-149")
        days = d0 + [build_day(d) for d in range(75, 150)]
    elif d1 and not d0:
        print("Merged: plan_data 0-74 + JSON 75-149")
        days = [build_day(d) for d in range(0, 75)] + d1
    else:
        print("Generated all 150 days from plan_data")
        days = [build_day(d) for d in range(150)]

    current = load_current_day()
    days = apply_statuses(days, current, saved)
    print(f"Statuses from data/current-day.json (current_day={current}) + plan.json done overrides")
    return days


def nav(active: str, depth: int = 0) -> str:
    p = "../" * depth
    items = [
        ("index", "Master Plan", f"{p}index.html"),
        ("platform", "Platform", f"{p}platform.html"),
        ("checklist", "Daily Checklist", f"{p}checklist.html"),
    ]
    for slug, name, *_ in PRODUCTS:
        items.append((slug, name, f"{p}products/{slug}.html"))
    parts = ['<nav class="site-nav">', '<div class="nav-brand">Akshant · 150 Days</div>']
    for key, label, href in items:
        cls = "nav-item active" if key == active else "nav-item"
        parts.append(f'<a class="{cls}" href="{href}">{esc(label)}</a>')
    parts.append("</nav>")
    return "\n".join(parts)


def shell(title: str, active: str, body: str, depth: int = 0) -> str:
    prefix = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<link href="{FONTS}" rel="stylesheet">
<link rel="stylesheet" href="{prefix}{ASSETS}">
</head>
<body>
{nav(active, depth)}
{body}
<footer class="site-foot">Akshant Sharma · 150-Day Platform Plan · Days 0–149</footer>
<script>
document.querySelectorAll('.day-hdr').forEach(h => {{
  h.addEventListener('click', () => h.closest('.day-block').classList.toggle('open'));
}});
</script>
</body>
</html>"""


def status_badge(status: str) -> str:
    cls = {"done": "badge-done", "today": "badge-today"}.get(status, "badge-pending")
    label = {"done": "Done", "today": "Today", "pending": "Pending"}.get(status, status)
    return f'<span class="badge {cls}">{esc(label)}</span>'


def blog_extra(label: str, content) -> str:
    if not content:
        return ""
    if isinstance(content, dict):
        text = (
            f"<strong>{esc(content.get('title', ''))}</strong><br>"
            f"{esc(content.get('subtitle', ''))}<br>{esc(content.get('outline', ''))}"
        )
    else:
        text = esc(content)
    return f'<div class="detail-card extra"><div class="dc-label">{esc(label)}</div><div class="dc-body">{text}</div></div>'


def render_day_block(d: dict, show_product: bool = True) -> str:
    exp, ai = d.get("experience", {}), d.get("ai", {})
    st = d.get("status", "pending")
    slug = d.get("product", "")
    pname = d.get("product_name", "")
    color = PRODUCT_COLORS.get(slug, "#00e5ff")
    prod = (
        f' · <span class="product-pill" style="color:{color};border-color:{color}">{esc(pname)}</span>'
        if show_product
        else ""
    )
    extras = blog_extra("Weekly · Project blog", d.get("project_blog"))
    extras += blog_extra("Monthly · Product blog", d.get("product_blog"))
    title = d.get("title", d.get("repo", ""))
    block = f"""
<article class="day-block status-{esc(st)}" id="day-{d['day']}" data-product="{esc(slug)}" data-status="{esc(st)}" data-repo="{esc(d.get('repo',''))}">
  <header class="day-hdr">
    <div class="day-num">{d['day']:03d}</div>
    <div class="day-title-wrap">
      <div class="day-title">{esc(title)}</div>
      <div class="day-meta">{esc(d.get('weekday',''))} · <code>{esc(d.get('repo',''))}</code>{prod} · {status_badge(st)}</div>
    </div>
    <span class="day-chevron">▼</span>
  </header>
  <div class="day-body">
    <div class="detail-grid">
      <div class="detail-card code">
        <div class="dc-label">Code / Repo work</div>
        <div class="dc-body">{esc(d.get('code',''))}</div>
      </div>
      <div class="detail-card exp">
        <div class="dc-label">Experience blog</div>
        <div class="dc-title">{esc(exp.get('title',''))}</div>
        <div class="dc-sub">{esc(exp.get('subtitle',''))}</div>
        <div class="dc-body"><em>Bridge → code:</em> {esc(exp.get('bridge',''))}</div>
      </div>
      <div class="detail-card ai">
        <div class="dc-label">AI learning · Day {esc(ai.get('day_index', d['day']))}</div>
        <div class="dc-title">{esc(ai.get('title',''))}</div>
        <div class="dc-sub">{esc(ai.get('subtitle',''))}</div>
        <div class="dc-body"><em>Hook → design:</em> {esc(ai.get('hook',''))}</div>
      </div>
      <div class="detail-card thread">
        <div class="dc-label">Daily thread</div>
        <div class="dc-body">{esc(d.get('thread',''))}</div>
      </div>
      {extras}
    </div>
  </div>
</article>"""
    return block


def hero_subtitle(days: list[dict], current_day: int) -> str:
    done = sum(1 for d in days if d.get("status") == "done")
    if current_day <= 0:
        return "Day 0 — set current_day in data/current-day.json"
    if done >= current_day:
        return f"Days 0–{current_day - 1} done · Day {current_day} is today"
    return f"{done} days done · Day {current_day} is today"


def generate_index(days: list[dict]) -> str:
    current_day = load_current_day()
    rows = []
    for d in days:
        exp, ai = d.get("experience", {}), d.get("ai", {})
        slug = d.get("product", "")
        color = PRODUCT_COLORS.get(slug, "#00e5ff")
        st = d.get("status", "pending")
        search = f"{d['day']} {d.get('product_name','')} {d.get('repo','')} {exp.get('title','')} {ai.get('title','')}"
        rows.append(
            f'<tr data-product="{esc(slug)}" data-status="{esc(st)}" data-repo="{esc(d.get("repo",""))}" '
            f'data-search="{esc(search)}">'
            f"<td><strong>{d['day']}</strong></td>"
            f"<td>{status_badge(st)}</td>"
            f'<td><span class="product-pill" style="color:{color};border-color:{color}">'
            f'{esc(d.get("product_name",""))}</span></td>'
            f'<td><a href="projects/{esc(d.get("repo",""))}.html">{esc(d.get("repo",""))}</a></td>'
            f'<td>{esc(d.get("weekday",""))}</td>'
            f'<td>{esc(exp.get("title","")[:55])}</td>'
            f'<td>{esc(ai.get("title","")[:55])}</td>'
            f'<td><a class="row-link" href="#day-{d["day"]}">Open</a></td></tr>'
        )

    product_opts = "".join(
        f'<option value="{esc(slug)}">{esc(name)}</option>' for slug, name, *_ in PRODUCTS
    )
    repos = sorted({d.get("repo", "") for d in days})
    repo_opts = "".join(f'<option value="{esc(r)}">{esc(r)}</option>' for r in repos)
    done = sum(1 for d in days if d.get("status") == "done")
    today_count = sum(1 for d in days if d.get("status") == "today")
    details = "\n".join(render_day_block(d) for d in days)
    sub = hero_subtitle(days, current_day)

    body = f"""
<div class="hero">
  <span class="tag" style="color:var(--teal);border-color:rgba(0,229,255,.3);background:rgba(0,229,255,.06)">150-Day Master Plan</span>
  <h1>Platform build · <em>Days 0–149</em></h1>
  <p class="sub">Two daily blogs (Experience + AI Learning) linked by a Daily Thread. Five products, ~26 repos, one platform. {esc(sub)}</p>
  <div class="stats">
    <div class="stat"><span class="stat-v" style="color:var(--green)">{done}</span><span class="stat-l">Done</span></div>
    <div class="stat"><span class="stat-v" style="color:var(--teal)">{today_count}</span><span class="stat-l">Today</span></div>
    <div class="stat"><span class="stat-v">150</span><span class="stat-l">Days</span></div>
    <div class="stat"><span class="stat-v">5</span><span class="stat-l">Products</span></div>
  </div>
</div>
<div class="sec">
  <div class="sec-head"><h2>Master table</h2><div class="sec-line"></div></div>
  <div class="filters">
    <label>Product</label><select id="f-product"><option value="">All</option>{product_opts}</select>
    <label>Status</label><select id="f-status"><option value="">All</option>
      <option value="done">Done</option><option value="today">Today</option><option value="pending">Pending</option></select>
    <label>Repo</label><select id="f-repo"><option value="">All</option>{repo_opts}</select>
    <label>Search</label><input id="f-search" type="search" placeholder="Day, repo, headline…">
  </div>
  <div class="plan-table-wrap">
    <table class="plan-table" id="plan-table">
      <thead><tr><th>Day</th><th>Status</th><th>Product</th><th>Repo</th><th>Dow</th>
      <th>Experience</th><th>AI Learning</th><th></th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
  </div>
</div>
<div class="sec"><div class="sec-head"><h2>Day detail</h2><div class="sec-line"></div></div>
<div class="days-wrap">{details}</div>
<script>
(function() {{
  const rows = [...document.querySelectorAll('#plan-table tbody tr')];
  const blocks = [...document.querySelectorAll('.day-block')];
  function apply() {{
    const p = document.getElementById('f-product').value;
    const s = document.getElementById('f-status').value;
    const r = document.getElementById('f-repo').value;
    const q = document.getElementById('f-search').value.toLowerCase();
    rows.forEach(row => {{
      const ok = (!p||row.dataset.product===p)&&(!s||row.dataset.status===s)
        &&(!r||row.dataset.repo===r)&&(!q||row.dataset.search.toLowerCase().includes(q));
      row.classList.toggle('hidden', !ok);
    }});
    blocks.forEach(b => {{
      const ok = (!p||b.dataset.product===p)&&(!s||b.dataset.status===s)
        &&(!r||b.dataset.repo===r)&&(!q||b.textContent.toLowerCase().includes(q));
      b.style.display = ok ? '' : 'none';
    }});
  }}
  ['f-product','f-status','f-repo','f-search'].forEach(id =>
    document.getElementById(id).addEventListener('input', apply));
  if (location.hash) {{
    const el = document.querySelector(location.hash);
    if (el) {{ el.classList.add('open'); setTimeout(()=>el.scrollIntoView({{behavior:'smooth'}}), 100); }}
  }}
}})();
</script>"""
    return shell("Akshant · 150-Day Master Plan", "index", body, 0)


def generate_platform() -> str:
    cards = []
    taglines = {
        "lensai": "AI Inference Observability",
        "traceforge": "AI Agent Execution Tracer",
        "routeiq": "Intelligent LLM Router",
        "driftwatch": "ML Drift + Quality Monitor",
        "fineforge": "Fine-Tuning Pipeline",
    }
    for slug, name, lo, hi in PRODUCTS:
        c = PRODUCT_COLORS[slug]
        cards.append(
            f'<div class="card"><div class="card-header">'
            f'<div class="card-title" style="color:{c}">{esc(name)}</div>'
            f'<div class="card-sub">Days {lo}–{hi} · {esc(taglines[slug])}</div></div>'
            f'<div class="card-body"><a href="products/{slug}.html">View {esc(name)} plan →</a></div></div>'
        )
    body = f"""
<div class="hero">
  <span class="tag" style="color:var(--purple);border-color:rgba(167,139,250,.35);background:rgba(167,139,250,.06)">Platform</span>
  <h1>Five products · <em>one loop</em></h1>
  <p class="sub">LensAI observes inference → TraceForge traces agents → RouteIQ routes requests → DriftWatch detects drift → FineForge fine-tunes. Day 149 wires platform-launch into a single demo narrative.</p>
</div>
<div class="sec"><div class="sec-head"><h2>Products</h2><div class="sec-line"></div></div>
<div class="grid-3">{"".join(cards)}</div></div>
<div class="sec"><div class="info-box">
<strong>Closed loop (Day 149):</strong> Telemetry from LensAI feeds DriftWatch evals; drift triggers FineForge retrain; RouteIQ registers new model weights; TraceForge validates agent behavior on shadow traffic.
</div></div>"""
    return shell("Platform Vision", "platform", body, 0)


def generate_product(slug: str, name: str, lo: int, hi: int, days: list[dict]) -> str:
    subset = [d for d in days if lo <= d["day"] <= hi]
    c = PRODUCT_COLORS[slug]
    body = f"""
<div class="hero">
  <span class="tag" style="color:{c};border-color:{c}55;background:{c}12">{esc(name)}</span>
  <h1>{esc(name)}</h1>
  <p class="sub">Days {lo}–{hi} · <a href="../index.html">Master calendar</a></p>
</div>
<div class="days-wrap">{"".join(render_day_block(d, False) for d in subset)}</div>"""
    return shell(f"{name} · Product Plan", slug, body, 1)


def generate_project(repo: str, days: list[dict]) -> str:
    subset = [d for d in days if d.get("repo") == repo]
    slug = subset[0].get("product", "lensai") if subset else "lensai"
    c = PRODUCT_COLORS.get(slug, "#00e5ff")
    cards = "".join(
        f'<div class="card" style="margin-bottom:10px"><div class="card-header">'
        f'<div class="card-title">Day {d["day"]} · {esc(d.get("weekday",""))}</div>'
        f'<div class="card-sub">{status_badge(d.get("status","pending"))}</div></div>'
        f'<div class="card-body">{esc(d.get("code",""))}</div></div>'
        for d in subset
    )
    body = f"""
<div class="hero">
  <span class="tag" style="color:{c};border-color:{c}55">{esc(repo)}</span>
  <h1><code>{esc(repo)}</code></h1>
  <p class="sub">{len(subset)} build days · <a href="../index.html">Master plan</a></p>
</div>
<div class="sec">{cards}</div>"""
    return shell(f"Project · {repo}", "index", body, 1)


def main() -> None:
    days = merge_days()
    current_day = load_current_day()
    (ROOT / "data").mkdir(exist_ok=True)
    plan_path = ROOT / "data" / "plan.json"
    plan_path.write_text(
        json.dumps({"current_day": current_day, "days": days}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    generated: list[Path] = [plan_path, ROOT / "assets" / "style.css"]

    (ROOT / "index.html").write_text(generate_index(days), encoding="utf-8")
    generated.append(ROOT / "index.html")

    (ROOT / "platform.html").write_text(generate_platform(), encoding="utf-8")
    generated.append(ROOT / "platform.html")

    (ROOT / "products").mkdir(exist_ok=True)
    for slug, name, lo, hi in PRODUCTS:
        path = ROOT / "products" / f"{slug}.html"
        path.write_text(generate_product(slug, name, lo, hi, days), encoding="utf-8")
        generated.append(path)

    (ROOT / "projects").mkdir(exist_ok=True)
    for repo in sorted({d.get("repo") for d in days if d.get("repo")}):
        path = ROOT / "projects" / f"{repo}.html"
        path.write_text(generate_project(repo, days), encoding="utf-8")
        generated.append(path)

    print("\nGenerated files:")
    for p in generated:
        print(f"  {p}")
    html_count = len(generated) - 2
    print(f"\nHTML pages: {html_count}")
    print(f"\nChecklist (not regenerated): {ROOT / 'checklist.html'}")
    print(f"Open: open '{ROOT / 'index.html'}'")


if __name__ == "__main__":
    main()
