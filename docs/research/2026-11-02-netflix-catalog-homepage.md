# Netflix-Style Catalog Homepage — Research Report

*Generated: 2026-11-02 | Sources: 26+12+27 across three parallel research tracks | Confidence: High (primary sources fetched in full)*

Compiled from three parallel research tracks done on this date, covering (A) Netflix page
anatomy + horizontal carousel mechanics, (B) user psychology for campus study-material
browsing, and (C) small-scale ranking math. Full source lists live at the bottom.

## Executive Summary

- Netflix's homepage is a 2-D layout: a server-rendered "billboard" hero plus a stack of
  **horizontally scrollable, individually named rows**. Rows exist to let a member decide
  about 20 items at once ("dive in or skip the whole row") instead of scanning one giant
  grid — their own words: rows prevent the experience of "a large, unorganized collection."
- The strongest finding relevant to this product: the homepage should lead with **retrieval**
  (search + personal state), not discovery. Spotify's discovery-heavy Home redesign dropped
  weekly active users ~17% and 95% of users never scrolled past two discovery cards; the fix
  reserved the first ~10 slots for familiar content. Scribd's bandit-optimized homepage
  found the personal **"Library" row was their highest-performing row of 42 row types**, and
  when a personal row is empty it degrades to the next content row rather than rendering empty.
- Row labels must state their **evidence** ("Most read this week in CSE", "Top rated by
  25 students"); vague rotating labels are the one documented negative case (Spotify UX audit).
- Ranking math: for a tiny stack, "Most Read" = cumulative deduped `views` (Reddit "Top"
  semantics) with a recent tiebreak; "Top Rated" = IMDb-family **Bayesian average**
  `WR = (sum + m·C)/(count + m)` with a small pseudocount m and a per-item floor
  (items with very few ratings cannot top the list).

## 1. Page anatomy (Netflix Tech Blog, primary sources)

- Billboard + rows have been the structure since 2015; members **scan vertically more than
  horizontally**, so the top row × first few cards is the most-viewed real estate on the page
  (netflixtechblog.com "Learning a Personalized Homepage").
- Netflix server-renders the billboard and first ~3 rows; deeper rows lazy-load on scroll to
  save DOM nodes and bandwidth ("Delivering Meaning with Previews on Web").
- Row template (pre-personalization era): **Continue Watching → Top Picks → Popular → genre
  rows**, with a personal-state row ("My List") interleaved among discovery rows.
- "Top 10" rows break the grid intentionally (huge outlined rank numerals) and carry badges
  wherever the title appears elsewhere on the page.

## 2. Horizontal scroll mechanics (NN/g, web.dev, MDN, Chrome, WAI-ARIA)

- Rows = native scroll built on `overflow-x: auto` + `scroll-snap-type: x mandatory` with
  `scroll-snap-align: start` on cards; momentum/trackpad/keyboard scrolling for free.
- **The next card's edge must peek** into view — the single strongest horizontal-scroll
  discovery cue, stronger than arrows or dots (NN/g mobile carousel research). NN/g found
  users stop after 3–4 swipes; rows should be short (6–12 cards) with "See all →" links.
- Arrows: large, always-visible (not hover-only — Netflix's hover-only arrows are cited by
  name as an antipattern on NN/g "Beware Horizontal Scrolling"), disabled-not-removed at the
  ends, real `<button>`s with accessible names, and **scroll by ~85–90% of the row width** so
  context is kept (Chrome DevRel: `::scroll-button()` pages ~85%).
- Hidden scrollbars are acceptable **only** when arrows/peek still signal scrollability.
- Accessibility: row is a focusable scrollable region (`tabindex="0"`, `role="region"`,
  `aria-label`), visible focus styles, keyboard arrows scroll; for item lists a plain labeled
  list of links is the recommended SR semantic (do not deploy slideshow ARIA per row).
- Contain the axis: `overscroll-behavior-x: contain` so a horizontal flick never scrolls the
  whole page. Honor `prefers-reduced-motion` (no smooth-scroll animation, no auto-rotate).
- Hover effects: animate composited `transform` only; never animate `width`; avoid big blur
  shadows on cards (paint bombs) and blanket `will-change` (layer explosions).

## 3. User thought process (education-specific studies)

- Study-material intent is **exam-rush dominated**: ~35–65% of students only engage with
  study tools in exam week or the day(s) before (OSF 2022 flashcard study); sharing happens
  around deliverables (Kuwait Univ. ASIS&T study). Retrieval speed is the product.
- But "browse with nothing specific in mind" is a real minority mode — a StudySmarter case
  study documents five intent levels and built *both* no-typing browse and layered search;
  measured lift in "users ending up studying."
- Advanced filtering is rare early on: only ~1 in 4 students uses filters at study start
  (Higher Education 2018). The homepage must do the filtering for them.
- **Trust is the bottleneck**: confidence in notes shared through informal group chats is
  ~42% vs 88% for admin/platform-verified material (2025 design-science study). Peer ratings,
  rating volume, and "who uploaded" matter; research also shows students systematically
  overrate peer content, so rating *volume* should accompany averages.
- Choice overload (Iyengar & Lepper + 63-condition meta-analysis): the effect is real but
  moderated; it bites when sets are hard to compare and the user is rushed/exam-stressed —
  i.e., exactly this audience 10 minutes before an exam. The remedy is **categorization and
  explicit differences**, not fewer items: named rows + chips (course code, semester, rating
  count, format) on each tile.

## 4. Competitor patterns actually in production

- **Studocu** (fetched live): hero = intent-framed copy + one search bar; then a labeled
  discipline grid, peer-proof band, and stats. Course pages tab materials as Lecture notes /
  Practice / Summaries / Assignments and sort "Highest Rated"; each doc shows academic year.
- **Docsity**: hero explicitly exam-intent ("Preparing for an exam? …"), discovery row, and
  daily-throughput stats as social proof.
- **Coursera** (fetched live): main content rail is literally a carousel titled
  **"New and popular"** with three labeled cards (Most popular / Hot new releases / Trending
  AI courses), followed by an "Explore categories" grid and trending-search chips.
- **Scribd**: 10 homepage row slots over 42 row types, position-optimized by bandits; the
  personal "Library" row WON; empty personal rows degrade to the next best content row
  (Scribd engineering blog).
- **Netflix**: "New & Popular" tab bundles New / Coming Soon / daily Top 10 / "Worth the
  Wait"; removing these rows in 2025 caused the loudest user backlash — capability-carrying
  labels matter.

## 5. Design decisions for this app (traceable)

Decision table — each traceable to a finding above:

| Our element | Decision | Trace |
|---|---|---|
| Hero | Keep search bar as the anchor (exam-rush intent) + time-aware greeting + department/branch chips + compact featured spotlight card | §3 retrieval-first; Studocu/Docsity heroes; billboard anchor |
| Row 1 (logged in) | **"From your library"** — saved collections rendered as tiles; hidden when empty (never an empty personal row) | Scribd bandit winner + empty-row fallback |
| Row order | Saved → Recently added → Most read → Top rated → per-branch → by-category | Netflix template order (personal state first, then freshness, popularity, rating) |
| "Most read" semantics | Cumulative, visitor-deduped `views` + recency tiebreak; **not** decayed (decay would make the "Trending" label, which we don't claim) | Reddit Top; Spotify popular-tracks; YouTube |
| "Top rated" semantics | IMDb Bayesian average `WR = (sum + 5·C)/(count + 5)`; per-item floor `rating_count ≥ 3`; row hidden unless ≥5 items qualify | IMDb + Evan Miller; degenerate "1×5★ = top" state prevented |
| Row length | 6–12 items max per row; "See all →" to `/browse` | NN/g 3–4-swipe finding |
| Labels | State evidence: "Most read", "Top rated", "Popular in {branch}", "Past exam papers" | Netflix title-as-evidence; Spotify vague-label failure |
| Tiles | Format-coloured badge, 2-clamped title, course-code chip, rating **only ≥3 ratings** shown, reads count | explicit-differences rule; rating-volume rule |
| Motion | No autoplay, no auto-rotate; smooth arrows only without `prefers-reduced-motion` | NN/g auto-forward + reduced-motion rules |

## Key source index (chronological by track)

**Track A — Netflix anatomy & carousel mechanics:** Netflix TechBlog "Learning a
Personalized Homepage" (netflixtechblog.com/learning-a-personalized-homepage-aa8ec670359a);
"Delivering Meaning with Previews on Web" (…/delivering-meaning-with-previews-on-web-3cedc0341b9a);
NN/g "Carousel Usability: Designing an Effective UI" (nngroup.com/articles/designing-effective-carousels/);
NN/g "Carousels on Mobile Devices" (…/mobile-carousels/); NN/g "Beware Horizontal Scrolling"
(…/horizontal-scrolling/); NN/g "Scrolljacking 101"; web.dev carousel best practices
(web.dev/articles/carousel-best-practices); web.dev CSS scroll-snap; MDN "Creating CSS
carousels" (2026 — ::scroll-button/::scroll-marker); Chrome "Carousels with CSS" +
"Make accessible carousels" (developer.chrome.com/blog); W3C WAI-ARIA APG Carousel;
WebAIM carousels; css-tricks.com Netflix hover animation breakdown; Vulture 2025 redesign
coverage ("why netflix had to redesign its homepage").
**Track B — psychology & competitors:** OSF 2022 flashcard SRL preprint (doi 10.31234/osf.io/ve7hr);
ASIS&T Kuwait Univ. sharing study (doi 10.1002/pra2.881); Higher Ed filtering study
(doi 10.1007/s10734-018-0296-4); Iyengar & Lepper 2000 full text; Scheibehenne 2010
meta-analysis; NN/g noncompensatory decisions + explicit differences + choice overload;
kaiwanschura.com/studysmarter (five intent levels); nishal.design Spotify Hybrid Home
postmortem (-17% WAU finding); tech.scribd.com "Bandits for the win"; live-fetched
studocu.com, coursera.org, docsity.com; NoteHub 2025 trust study
(doi 10.15680/ijircce.2025.1311063); IEEE TL&T peer-rating overrate study
(doi 10.1109/tlt.2022.3229022); studocu course-page sort/year habits blog.
**Track C — ranking math:** Evan Miller "How Not To Sort By Average Rating" +
"Ranking Items With Star Ratings" + "Bayesian Average Ratings"
(evanmiller.org); HN news.arc analysis (righto.com/2009/06/how-does-newsy-ranking-work,
note actual slug how-does-newsyc-ranking-work); HN gravity/Medium write-up;
reddit-archive hot-formula source; IMDB ratings FAQ (WR formula, m); SO 5-star-sorting
canonical answer; SQLite queryplanner/optoverview (ORDER BY/LIMIT behavior at ≤10k rows);
YouTube Trending Charts help (signals list); Spotify charts/popular definitions.

## What we shipped from it (this date)

1. `backend/app/api/v1/search.py` — additive `sort_by=views` (Most read) and
   `sort_by=top_rated` (Bayesian/IMDb-weighted, floor-via `min_ratings` param) +
   `min_ratings` filter; existing sorts untouched (contract stays additive).
2. `frontend/app/page.tsx` — billboard hero (greeting/search/chips/spotlight) + named
   catalog rows: From your library → Recently added → Most read → Top rated → per-branch
   ("Popular in X") → past exams, each a horizontally snap-scrolling shelf.
3. `frontend/components/ui/CatalogRow.tsx` — scroll-snap shelf, edge peek, always-visible
   disabled-at-ends arrows (desktop), focusable region + arrow keys, reduced-motion.
4. Row hide rules: empty personal row never renders; content rows hidden under 5 items.
