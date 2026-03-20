# UX review: reviewing picks, odds, and pool metrics

**Scope:** How people **find, read, and trust** the Day 2 NCAA ATS outputs (CSV, CLI, README, or a future report UI). This is not a review of a live product yet—it sets standards for whatever you ship.

---

## Executive summary

Readers need a **single obvious entry point**, **plain-language definitions** (spread side, confidence, edge), and **honest uncertainty** (book count, missing ratings). Without that, CSV-only outputs force unnecessary cognitive load and invite mis-clicked sides. **Top priorities:** (1) a “How to read this” block above any pick list, (2) never encode win/loss prediction with color alone, (3) empty and error states that say what to do next.

---

## Strengths (to preserve when you build)

- **One row per game** maps cleanly to “16 picks” mental model.
- **Numeric confidence** supports ordering without extra UI.
- **Separating** raw slate vs final picks reduces accidental use of the wrong file.

---

## Recommendations by area

### Information architecture and navigation

| Finding | Recommendation |
|--------|----------------|
| Multiple outputs (raw odds, picks, grades) with similar names | Use consistent prefixes: `slate_raw_`, `picks_`, `graded_` + date; README lists **one** “start here” file. |
| User lands on CSV in Excel | Add a **one-page** `REVIEW.md` or HTML report that mirrors columns with short tooltips (or link to definitions). |
| Jargon in column headers (`p_cover`, `de_vig`) | Ship a **data dictionary** table: column → plain English → example value. |

### Primary flows

| Finding | Recommendation |
|--------|----------------|
| Happy path: “What do I enter in my pool?” | **Above the fold:** ranked list with **pick (team name)**, **line**, **confidence**, **game time** (local TZ labeled). |
| User confuses home vs away spread | Each row shows **both teams** and explicitly: **Pick: [Team] ([role: home/away])** and the line as **“Team -3.5”** not only a bare number. |
| No games on date / API failure | **Empty state:** “No NCAAB spreads found for this date. Check API key, sport key, and timezone filter.” + link to Odds API status or retry command. |
| Partial ratings merge | **Inline flag** `ratings_ok: yes/no` per row; if no, show “market-only” badge and slightly muted confidence in UI. |

### Feedback and system status

| Finding | Recommendation |
|--------|----------------|
| Long fetch with no feedback | CLI prints **stages**: “Fetching odds…”, “Merging ratings…”, “Writing picks…” with counts (e.g. 16 games). |
| Success looks like silence | End with **one summary line**: “16 picks written to picks_2026-03-20.csv” + path. |
| Grading script errors | If result missing for a game, **list game IDs** missing and “W/L skipped for these rows.” |

### Accessibility

| Finding | Recommendation |
|--------|----------------|
| Color-only favorite/dog or confidence | Use **text labels**: “Higher confidence”, “Market-only”, not only green/red. |
| HTML report tables | Use `<th scope="col">`, caption or `aria-describedby` pointing to the “How to read” section. |
| Print or PDF for pool entry | Provide **print stylesheet** or “Print picks” that hides nav chrome; **16px+ body** text for readability. |

### Visual consistency and clarity

| Finding | Recommendation |
|--------|----------------|
| Confidence as long floats | **Format:** one decimal or whole percent, consistent width (e.g. `62%` not `0.623441`). |
| Wall of numbers | **Visual hierarchy:** rank #, then team pick, then line; push `edge_vs_market` to secondary column or tooltip. |
| Typography in terminal | Use **fixed-width alignment** for numeric columns; optional `rich`/`tabulate` for borders. |

### Mobile (if you add a web view later)

| Finding | Recommendation |
|--------|----------------|
| Wide tables on phone | **Card layout** per game on narrow viewports: pick + line + confidence stacked; horizontal scroll only as last resort. |
| Touch | If any actions (copy pick), **min 44px** tap targets. |

---

## Prioritized backlog

### High

1. **“How to read this”** — spread sign convention, what “confidence” means (model vs coin flip), and “not financial advice” one-liner.
2. **Explicit pick side** — team + home/away + stated line string.
3. **Empty / error states** — API, no lines, merge failures.

### Medium

4. **Data dictionary** for every CSV column.
5. **CLI progress** and final summary path.
6. **No color-only status** in any report.

### Lower

7. Print-friendly report page.
8. Responsive card layout if you ship HTML beyond the template.

---

## Subagent lenses (if you split work later)

- **Content & copy:** definitions, empty states, column renames.
- **IA:** single entry doc, file naming, section order.
- **A11y:** table semantics, labels, contrast for any chart.
- **Mobile:** card layout for pick list.

---

## Checklist before you call it “reviewable”

- [ ] New reader can answer “who do I take?” in **30 seconds** without opening README hunt.
- [ ] Spread direction mistakes are **structurally hard** (explicit team + line).
- [ ] Failures say **what happened** and **what to try**.
- [ ] Confidence is **interpretable** (relative rank + short definition).
