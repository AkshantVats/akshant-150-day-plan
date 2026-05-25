# YC Application — Pre-Submit Checklist

Use this before clicking submit on [ycombinator.com/apply](https://www.ycombinator.com/apply). Items marked **BLOCKER** will weaken or disqualify the app if empty.

---

## Legal & entity

| Item | Status | Notes |
|------|--------|-------|
| **Legal company name** | ☐ TBD | Decide: LensAI Inc. vs platform brand |
| **Incorporation** (country, date, type) | ☐ TBD | DE C-Corp common for YC; India Pvt Ltd + flip **ask counsel** |
| **Cap table / equity split** | ☐ TBD | Enter in application; must sum to 100% |
| **Prior investment / SAFEs** | ☐ TBD | "None" if accurate |
| **IP assignment** | ☐ TBD | OSS MIT ok; confirm employer IP clearance from Agoda/Wayfair/etc. |

---

## Founders (BLOCKERS)

| Item | Status | Notes |
|------|--------|-------|
| **Founder legal names** | ☐ | Replace `[Founder name]` in all docs |
| **Full-time commitment** | ☐ BLOCKER | Exact date left job or plan to quit |
| **Co-founder** | ☐ | Solo: say so + hiring plan; or add co-founder bios |
| **Impressive achievement** (specific, numeric) | ☐ BLOCKER | Per founder; no generic adjectives |
| **How founders met / years known** | ☐ BLOCKER | |
| **Hack / non-computer system story** | ☐ | YC wildcard question |
| **Surprising founder fact** | ☐ | One concrete story |
| **LinkedIn / GitHub URLs** | ☐ | Verify links work |
| **Visa / SF batch attendance** | ☐ BLOCKER | Can you relocate July–Sept (or relevant batch)? |

---

## Product & traction

| Item | Status | Notes |
|------|--------|-------|
| **Company URL** | ☐ | Prod site or GitHub org landing |
| **Demo URL** | ☐ BLOCKER | 2-min screen recording: ingest → Grafana |
| **1-minute founder video** | ☐ BLOCKER | Unlisted YouTube; founders on camera; no ad polish |
| **GitHub stars / forks** | ☐ | Record at submit time |
| **Design partner count** | ☐ | Even 3 LOIs or paid pilots — huge lift |
| **Customer discovery notes** | ☐ | 10–20 interviews summarized in app |
| **Weekly growth metric** | ☐ | Stars, commits, or waitlist — something ↑ |

---

## Application copy

| Item | Status | Notes |
|------|--------|-------|
| Copy from `YC-APPLICATION.md` into form | ☐ | Trim to field char limits |
| **50-char description** | ☐ | `AI ops data plane: observe→route→retrain` |
| **One-sentence description** | ☐ | Plain English test (PG howtoapply) |
| **How far along** | ☐ | Re-read honesty: only LensAI shipped |
| **Competitors + insight** | ☐ | Must name real obstacles |
| **Revenue** | ☐ | $0 unless changed |
| **AI safety field** (if present) | ☐ | 150 chars — no PII in shared models |
| **Referral code** | ☐ | YC alumni email if you have one |
| **Other ideas field** | ☐ | Optional alternates |

---

## Pitch materials

| Item | Status | Notes |
|------|--------|-------|
| `PITCH-DECK.md` → PDF or Google Slides | ☐ | 10–12 slides; test on phone |
| `ONE-PAGER.md` → PDF | ☐ | Send to intros / alumni reviews |
| Red-pen pass (remove every extra word) | ☐ | Per PG howtoapply |
| Read answers aloud | ☐ | No tongue-twisters |

---

## Technical verification (before claiming in app)

| Item | Status | Notes |
|------|--------|-------|
| `./scripts/smoke-e2e.sh` passes | ☐ | |
| Grafana panels show data | ☐ | Screenshot for README / video |
| G-07 merged or describe as "PR #5" | ☐ | Update `YC-APPLICATION.md` if merged |
| `PROJECT-STATUS.md` gaps acknowledged | ☐ | partition key, anomaly detection |

---

## Post-submit

| Item | Status | Notes |
|------|--------|-------|
| Save application PDF / export | ☐ | Version history |
| Update app if major progress | ☐ | YC allows updates before interviews |
| Prepare 10-min interview Q&A | ☐ | Users, revenue, why you vs Langfuse |
| Demo laptop offline-capable | ☐ | compose up without WiFi fail |

---

## Files in this package

| File | Purpose |
|------|---------|
| `YC-APPLICATION.md` | Master answers for all form fields |
| `PITCH-DECK.md` | Slide-by-slide with speaker notes |
| `ONE-PAGER.md` | Partner / intro email attachment |
| `CHECKLIST.md` | This file |

---

## Suggested review order

1. Alumni or founder friend — **one-pager + 1-min video**  
2. Staff engineer — **technical honesty** (`PROJECT-STATUS` vs claims)  
3. Red-pen — **cut 30% words** from long answers  
4. Submit **before deadline 8pm PT** (not midnight — slow servers)

---

*After personalization, commit in plan repo: `docs: YC application package`*
