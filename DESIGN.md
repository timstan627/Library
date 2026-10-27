---
name: Student Library
description: A free, community-run study-material library — midnight-dark, one harbor-blue accent, built for findability and trust.
colors:
  surface-base: "oklch(0.155 0.012 245)"
  surface-raised: "oklch(0.200 0.014 245)"
  surface-sunken: "oklch(0.255 0.016 245)"
  edge-subtle: "oklch(0.315 0.020 245)"
  edge-field: "oklch(0.520 0.024 245)"
  edge-hover: "oklch(0.600 0.026 245)"
  ink-high: "oklch(0.920 0.010 245)"
  ink-body: "oklch(0.730 0.018 245)"
  ink-faint: "oklch(0.640 0.016 245)"
  harbor-blue: "oklch(0.545 0.180 250)"
  harbor-deep: "oklch(0.500 0.170 250)"
  harbor-sky: "oklch(0.780 0.115 250)"
  harbor-mist: "oklch(0.860 0.080 250)"
  paper-ink: "rgb(248 250 253)"
  ink-strong: "rgb(13 17 22)"
  success-fill: "oklch(0.535 0.145 155)"
  success-text: "oklch(0.700 0.130 155)"
  warning-fill: "oklch(0.700 0.140 085)"
  warning-text: "oklch(0.790 0.120 085)"
  danger-fill: "oklch(0.540 0.190 025)"
  danger-deep: "oklch(0.480 0.180 025)"
  danger-text: "oklch(0.705 0.160 025)"
  category-violet: "oklch(0.700 0.120 305)"
typography:
  display:
    fontFamily: "Bricolage Grotesque, Figtree, sans-serif"
    fontWeight: 700
  body:
    fontFamily: "Figtree, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Figtree, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "6": "24px"
  "8": "32px"
components:
  button-primary:
    backgroundColor: "{colors.harbor-blue}"
    textColor: "{colors.paper-ink}"
    rounded: "{rounded.lg}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.harbor-deep}"
  button-secondary:
    backgroundColor: "{colors.surface-sunken}"
    textColor: "{colors.ink-high}"
    rounded: "{rounded.lg}"
    padding: "8px 16px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-body}"
    rounded: "{rounded.lg}"
    padding: "8px 16px"
  button-danger:
    backgroundColor: "{colors.danger-fill}"
    textColor: "{colors.paper-ink}"
    rounded: "{rounded.lg}"
    padding: "8px 16px"
  input-field:
    backgroundColor: "{colors.surface-sunken}"
    textColor: "{colors.ink-high}"
    rounded: "{rounded.lg}"
    padding: "8px 12px"
  card:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink-high}"
    rounded: "{rounded.lg}"
  badge:
    backgroundColor: "{colors.surface-sunken}"
    textColor: "{colors.ink-body}"
    rounded: "{rounded.md}"
    padding: "2px 8px"
  badge-accent:
    backgroundColor: "oklch(0.545 0.180 250 / 0.10)"
    textColor: "{colors.harbor-sky}"
    rounded: "{rounded.md}"
    padding: "2px 8px"
  link:
    textColor: "{colors.harbor-sky}"
---

# Design System: Student Library

## Overview

**Creative North Star: "The Midnight Study Hall"**

A quiet, always-open library at night. The whole system is a dark, midnight-blue room — surfaces are near-black planes tinted toward a single azure hue (OKLCH hue 245, no pure grays anywhere) — and one harbor-blue light marks everything that matters: links, primary actions, focus, the way forward. Nothing glows, nothing shouts; the room is calm so the material on the shelves can be trusted.

The hall keeps its doors open and its shelf layout legible. Access is free and ungatekept (every public action is reachable in a click or two), and academic structure is the map: departments, courses, and semesters organize the shelves exactly the way students think. The interface's job is to disappear behind that structure — comfortable density, scanable tables, honest empty states.

Components are refined and restrained at rest but tactile in the hand: a single hover gesture (a small lift or a border brighten, never both plus a glow), a satisfying press (scale 0.98), instant focus. Efficient and unpretentious — the design would rather be a good study room than a showcase.

**Key Characteristics:**
- Dark-only system (`color-scheme: dark`); three surface elevations, all tinted hue 245
- One anchor accent (Harbor Blue); status hues appear only as state, violet only as category marks
- Flat at rest; depth appears only as feedback (lift, border brighten, press scale)
- Composited motion only (transform/opacity), exponential ease-out, staggered entrances at 45 ms
- Tabular figures on every data-heavy number; balanced line breaks on every heading
- Lucide icons at 16–24 px, stroke 2; never emoji as UI icons

## Colors

A midnight-neutral ramp with one hero hue. Every neutral — surfaces, edges, ink — is tinted toward azure (hue 245); saturation is deliberately faint (chroma ≤ 0.026) so the accent is the only voice in the room.

### Primary
- **Harbor Blue** (oklch(0.545 0.180 250)): the system's single accent. Primary buttons, links' hover targets, active focus rings, selected states, the wordmark tile. Its rarity is the point — on any screen it covers well under 10%.
- **Harbor Deep** (oklch(0.500 0.170 250)): Harbor Blue's pressed/hover step *down* — buttons darken on hover, never lighten toward the background.
- **Harbor Sky** (oklch(0.780 0.115 250)): the accent as *text* on dark — all links, accent badges, icon strokes needing ≥ 4.5:1. This is what "blue text" means in this system.
- **Harbor Mist** (oklch(0.860 0.080 250)): the hover step *up* for links and accent text; links brighten on hover, never dim.
- **Paper Ink** (rgb(248 250 253)): the near-white ink that sits *on* accent fills (primary/danger button labels).
- **Strong Ink** (rgb(13 17 22)): the near-black ink that sits on warning/success fills, where white would fail contrast.

### Secondary
Functional state hues, paired: a *fill* level (status-dot and badge backgrounds, always carrying Paper or Strong ink) and a *text* level (≥ 4.5:1 on dark surfaces, for inline words and icons).
- **Signal Green fill** (oklch(0.535 0.145 155)) / **Signal Green text** (oklch(0.700 0.130 155)): approved, healthy, trusted.
- **Caution Amber fill** (oklch(0.700 0.140 085)) / **Caution Amber text** (oklch(0.790 0.120 085)): pending, rate limits, warnings.
- **Alert Red fill** (oklch(0.540 0.190 025)), **Alert Red deep** (oklch(0.480 0.180 025)) as its hover, / **Alert Red text** (oklch(0.705 0.160 025)): destructive, rejected, errors.

### Tertiary
- **Category Violet** (oklch(0.700 0.120 305)): a text-level hue reserved for category/resource-type marks. Never used for actions or state — it identifies, it doesn't command.

### Neutral
All tinted hue 245; the three surfaces step 0.155 → 0.200 → 0.255 lightness.
- **Midnight Base** (oklch(0.155 0.012 245)): page background. The floor of the hall.
- **Raised Midnight** (oklch(0.200 0.014 245)): cards, header, footer — anything resting *on* the base.
- **Sunken Field** (oklch(0.255 0.016 245)): inputs, badges, icon tiles, wells — surfaces that invite interaction sit *in* the card.
- **Edge Subtle** (oklch(0.315 0.020 245)): decorative hairlines, card borders at rest, scrollbar thumb.
- **Edge Field** (oklch(0.520 0.024 245)): the interactive edge — input and secondary-button borders (≥ 3:1 field contrast).
- **Edge Hover** (oklch(0.600 0.026 245)): what Edge Field brightens to on hover.
- **Ink High** (oklch(0.920 0.010 245)): headings and primary body text.
- **Ink Body** (oklch(0.730 0.018 245)): secondary text, labels, inactive nav, badge text.
- **Ink Faint** (oklch(0.640 0.016 245)): placeholders, timestamps, the quietest metadata.

### Named Rules
**The One Hue Rule.** Harbor Blue is the only chromatic hero. Status hues speak only when state changes; violet only marks categories. If a new screen needs "more color," the answer is more structure, not more hues.

**The Tinted Neutral Rule.** There are no pure grays. Every neutral in the system carries hue 245; a stock palette gray or a `#fff`/`#000` is off-system by definition (legacy bridged classes resolve to themed tokens — new code uses tokens directly).

**The Two-Edge Rule.** Edges have exactly three strengths: Subtle for decoration, Field for anything interactive, Hover for the hover state of Field. Never invent a fourth brightness.

## Typography

**Display Font:** Bricolage Grotesque (variable, with Figtree fallback)
**Body Font:** Figtree (variable, with system-ui fallback)
**Mono Font:** system mono stack (ui-monospace, SFMono-Regular, Consolas) — code and raw identifiers only

**Character:** An expressive, slightly warm grotesque display over a friendly geometric body — a library with personality on its signage and clarity on its shelves. The display face is reserved for headings so its character reads as structure, not decoration.

### Hierarchy
- **Display** (700, Tailwind `text-4xl`/`text-5xl`, `text-wrap: balance`): page titles and hero statements. Balanced line breaks are progressive — the browser may spend the extra layout pass.
- **Headline** (700, `text-2xl`/`text-3xl`): section headings.
- **Title** (600, `text-lg`/`text-xl`): card titles, modal titles, resource names.
- **Body** (400, 1rem, line-height 1.6, max 65ch for long-form via `.prose-measure`): paragraphs, descriptions, legal text.
- **Label** (500, 0.875rem, sentence case, Ink Body): form labels, table heads, buttons at `text-sm`. No uppercase, no letter-spacing games — hierarchy comes from weight and color.
- **Data** (tabular figures via `.tabular-nums`): every stat, count, file size, and table number column.

### Named Rules
**The Tabular Figure Rule.** Any number that will be scanned, compared, or counted (stats, sizes, table columns) gets `tabular-nums`. Prose numbers don't.

**The Balanced Headline Rule.** Every heading wraps with `text-wrap: balance`; every prose paragraph with `text-wrap: pretty`. The type sets itself up to look intentional at any width.

## Layout

One container for everything: `max-w-6xl` (1152 px), centered, with responsive gutters (16 px → 24 px → 32 px at the `sm`/`lg` steps). Inside, content is arranged in comfortable, generous grids — 24–32 px section gaps, 16–24 px card gaps — rather than dense dashboards. The spacing scale is the Tailwind 4 px base stepped through the `--space-*` tokens (4/8/12/16/24/32).

Responsive behavior follows Tailwind's default breakpoints (sm 640, md 768, lg 1024, xl 1280). The header keeps its inline nav down to `md`, then collapses to a hamburger; the search field keeps its visible input down to `sm`, then collapses to an icon link. Card grids go one column on phones, two at `md`, three at `lg` where the page supports it. Long-form prose (legal, help) is capped at 65ch regardless of container.

## Elevation & Depth

**Flat, lift on intent.** Surfaces are flat at rest — depth is conveyed by the tonal ladder (Base → Raised → Sunken) and hairline edges, never by resting shadows. Shadow appears nowhere at rest; elevation is a *response*: interactive cards lift 2 px and brighten their edge on hover, buttons press to scale 0.98, focus draws a 2 px outline instantly. Nothing fades in; feedback is immediate (120–180 ms) and settles with an exponential ease-out (280 ms for entrances).

### Shadow Vocabulary
None at rest — and that is the vocabulary. If a shadow seems needed, the surface is probably in the wrong tonal step. The only light-play in the system is the skeleton shimmer (a translating sheen, not a shadow) and the 40%-alpha accent ring that marks input focus.

### Named Rules
**The One-Signal Rule.** A hover state changes one thing about a component as a single gesture — a lift *with* its edge brighten, *or* a color shift — never a stack of color + shadow + motion. If two signals compete, the quieter one wins.

## Shapes

Soft-rounded and honest: controls, cards, inputs, and icon tiles all use the 8 px radius (`rounded-lg`); badges and small marks step down to 6 px (`rounded-md`); the scrollbar thumb uses 4 px. Nothing is pill-shaped, nothing is sharp. Borders are always 1 px hairlines from the three-step edge scale — they define planes rather than decorate them. The recurring silhouette is the **icon tile**: a small rounded-lg square of Sunken Field holding a 16–24 px lucide icon, used from the auth page's hero mark to collection covers and the header wordmark.

## Components

### Buttons
- **Shape:** 8 px radius, 8 × 16 px padding, 500 weight, `white-space: nowrap`, always a flex row (icon + label stay on one line).
- **Primary:** Harbor Blue fill, Paper Ink label, transparent border. Hover deepens to Harbor Deep; active presses to scale 0.98.
- **Secondary:** Sunken Field fill, Ink High label, Edge Field border. Hover brightens only the border (Edge Hover) — the fill is already the resting depth.
- **Ghost:** transparent fill, Ink Body label. Hover reveals Sunken Field and steps text to Ink High.
- **Danger:** Alert Red fill, Paper Ink label; hover deepens to Alert Red deep. Reserved for destructive intent only.
- **Disabled:** 50% opacity, no transform, `not-allowed` cursor.
- **Focus:** 2 px Harbor Blue outline, 2 px offset — instant, never faded in.

### Cards / Containers
- **Corner Style:** 8 px radius.
- **Background:** Raised Midnight; hairline Edge Subtle border.
- **Shadow Strategy:** none at rest (see Elevation).
- **Interactive:** hover lifts 2 px and brightens the edge to Edge Field (180 ms, expo-out) — one gesture, no shadow play.
- **Internal Padding:** 16–24 px.

### Inputs / Fields
- **Style:** Sunken Field background (visibly recessed), Edge Field border (≥ 3:1), 8 px radius, Ink High text, Ink Faint placeholder, Harbor Blue caret.
- **Focus:** border turns Harbor Blue with a 2 px ring at 40% alpha; outline none (the ring is the visible focus).
- **Error:** Alert Red text-level messaging beside the field; the border reads Edge Field until submission feedback.

### Badges
- **Style:** Sunken Field fill, Ink Body text, 6 px radius, 2 × 8 px padding, hairline Edge Subtle border.
- **Accent variant:** Harbor Blue at 10% alpha fill, Harbor Sky text, Harbor Blue at 30% alpha border — the accent as a whisper.

### Navigation
Header: wordmark tile (Harbor Blue, Paper Ink "S") + wordmark, inline text links (Ink Body, stepping to Ink High when active), search field, and actions. Footer: link columns over Raised Midnight with a colophon row. Mobile: hamburger below `md`, search collapses to an icon below `sm`.

### Skeleton (signature)
Loading surfaces are Sunken Field with a single translating sheen (6% white, 1.6 s loop, composited `translateX`). List and grid entrances stagger at 45 ms per item, fading up 8 px. Under `prefers-reduced-motion`, all of it collapses to instant opacity-only appearance.

## Do's and Don'ts

### Do:
- **Do** use the semantic token classes (`bg-background-secondary`, `text-text-secondary`, `border-border-subtle`) for all new UI; resolve every color through the theme.
- **Do** check every new neutral carries the tint — if it reads as pure gray on midnight, it's off-system.
- **Do** give interactive elements exactly one hover gesture, 120–180 ms, exponential ease-out.
- **Do** set `tabular-nums` on every scanned number and `text-wrap: balance` on every heading.
- **Do** use lucide icons at 16–24 px (stroke 2) wrapped in accessible names; put icons on icon tiles (Sunken Field, 8 px radius).
- **Do** honor `prefers-reduced-motion`: opacity-only feedback, no spatial movement, no infinite loops.

### Don't:
- **Don't** introduce stock palette steps (`blue-500`, `gray-400`) in new code — the legacy bridge exists so old markup renders on-theme, not as an invitation.
- **Don't** stack hover signals (glow + lift + color) or add resting shadows to flat surfaces.
- **Don't** use uppercase/letter-spaced label caps, glued arrows in copy ("Upload your first file →"), or middle-dot separators — hierarchy is weight and color, not typographic noise.
- **Don't** animate layout properties (width, height, top/left); movement is composited transform only.
- **Don't** remove or fade-in focus rings; focus is instant and always visible.
- **Don't** use emoji as UI icons or invent a second accent hue.
