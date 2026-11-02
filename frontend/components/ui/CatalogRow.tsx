'use client'

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { ChevronLeft, ChevronRight, ChevronRight as SeeAllIcon } from 'lucide-react'
import { ResourceTileSkeleton } from './ResourceTile'

/**
 * Netflix-style catalog shelf: one named, vertically stacked row whose items
 * scroll horizontally with native scroll + CSS scroll-snap.
 *
 * Mechanics follow docs/research/2026-11-02-netflix-catalog-homepage.md:
 * - `overflow-x: auto` + `snap-x snap-mandatory` + per-item `snap-start`
 *   (uniform card widths make mandatory snapping safe).
 * - The next card always peeks into view — the strongest scrollability cue.
 * - Arrows exist only when the row actually overflows (fitting rows render
 *   none — no dead overlays over card text), sit above the rail only while
 *   scrolling, fade to invisible at the exact scroll ends (opacity, never
 *   display toggles — no layout shift), stay real disabled buttons in the
 *   DOM, and scroll ~85% of the row per press.
 * - The track is a focusable scrollable region with a labelled heading;
 *   on-screen readers get the plain-list semantic.
 * - No horizontal scrolljacking: `overscroll-x-contain` keeps the scroll
 *   inside the shelf.
 * - Rows hide themselves when they hold fewer than `minItems` items (3 for
 *   discovery rows — a small library must still show its shelves; rows
 *   claiming "Top"-style authority pass a higher threshold from the caller);
 *   an empty personal row must never render (Scribd's bandit fallback rule).
 */

interface CatalogRowProps {
    title: string
    /** Optional trailing link for the full list (e.g. /browse?…). */
    seeAllHref?: string
    ariaLabel?: string
    /** Row renders nothing when fewer than this many items exist. */
    minItems?: number
    /** While true, shimmer tiles render inside the shelf (no CLS: the row exists from first paint). */
    loading?: boolean
    skeletonCount?: number
    children?: React.ReactNode
}

interface ScrollState {
    /** Track content wider than the viewport (arrows only make sense then). */
    overflow: boolean
    canLeft: boolean
    canRight: boolean
}

const IDLE_SCROLL: ScrollState = { overflow: false, canLeft: false, canRight: false }

export function CatalogRow({
    title,
    seeAllHref,
    ariaLabel,
    minItems = 3,
    loading = false,
    skeletonCount = 6,
    children,
}: CatalogRowProps) {
    const titleId = useMemo(
        () => `catalog-row-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
        [title],
    )
    const trackRef = useRef<HTMLUListElement | null>(null)
    const [scrollState, setScrollState] = useState<ScrollState>(IDLE_SCROLL)
    const lastRef = useRef<ScrollState>(IDLE_SCROLL)
    const reducedMotion = useMemo(() => (
        typeof window !== 'undefined'
        && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ), [])

    const updateArrowState = useCallback(() => {
        const track = trackRef.current
        if (!track) return
        const next: ScrollState = {
            overflow: track.scrollWidth > track.clientWidth + 1,
            canLeft: track.scrollLeft > 2,
            canRight: track.scrollLeft < track.scrollWidth - track.clientWidth - 2,
        }
        const prev = lastRef.current
        if (prev.overflow !== next.overflow || prev.canLeft !== next.canLeft || prev.canRight !== next.canRight) {
            lastRef.current = next
            setScrollState(next)
        }
    }, [])

    useEffect(() => {
        updateArrowState()
        window.addEventListener('resize', updateArrowState)
        return () => window.removeEventListener('resize', updateArrowState)
    }, [updateArrowState, children, loading])

    if (!loading && React.Children.count(children) < minItems) {
        return null
    }

    const scrollByPage = (direction: 1 | -1) => {
        const track = trackRef.current
        if (!track) return
        track.scrollBy({
            left: direction * track.clientWidth * 0.85,
            behavior: reducedMotion ? 'auto' : 'smooth',
        })
        // Safety net: smooth scrolling + mandatory CSS snapping can finish
        // after the last scroll event on some engines (mobile WebViews throttle
        // momentum scroll events), leaving arrow state stale at the scroll
        // ends. Re-derive twice — once as the scroll settles, once later — so
        // the end-state fade never lags one press behind.
        window.setTimeout(updateArrowState, reducedMotion ? 150 : 450)
        window.setTimeout(updateArrowState, 800)
    }

    const items = loading
        ? Array.from({ length: skeletonCount }, (_, i) => (
            <li key={`sk-${i}`} className="w-[44vw] shrink-0 snap-start sm:w-56">
                <ResourceTileSkeleton />
            </li>
        ))
        : React.Children.map(children, (child, i) => (
            <li key={i} className="w-[44vw] shrink-0 snap-start sm:w-56">
                {child}
            </li>
        ))

    // Arrows render only while the rail can scroll, and only on pointer
    // devices (md:grid — touch users swipe). At the exact scroll ends they
    // fade out (opacity transition, no display change → zero layout shift):
    // a grey disabled circle parked over the first card reads as a bug.
    // Fitting rows (wide screens, short shelves) render no arrows at all.

    return (
        <section aria-label={ariaLabel ?? title}>
            <div className="mb-2 flex items-baseline justify-between">
                <h2 id={titleId} className="text-lg font-semibold font-display text-text-primary">
                    {title}
                </h2>
                {seeAllHref && !loading && (
                    <Link
                        href={seeAllHref}
                        className="text-sm text-text-secondary hover:text-text-primary"
                    >
                        See all
                        <SeeAllIcon className="ml-1 inline h-4 w-4 -translate-y-px" aria-hidden="true" />
                    </Link>
                )}
            </div>

            <div className="relative">
                <ul
                    ref={trackRef}
                    onScroll={updateArrowState}
                    onKeyDown={(e) => {
                        if (e.key === 'ArrowRight') { e.preventDefault(); scrollByPage(1) }
                        if (e.key === 'ArrowLeft') { e.preventDefault(); scrollByPage(-1) }
                    }}
                    aria-labelledby={titleId}
                    tabIndex={0}
                    className="no-scrollbar -mx-4 flex gap-3 overflow-x-auto px-4 py-1 overscroll-x-contain snap-x snap-mandatory scroll-pl-4 sm:mx-[-1.5rem] sm:px-6 sm:scroll-pl-6"
                >
                    {items}
                </ul>

                {scrollState.overflow && !loading && (
                    <>
                        <button
                            type="button"
                            onClick={() => scrollByPage(-1)}
                            aria-label={`Scroll ${ariaLabel ?? title} backward`}
                            disabled={!scrollState.canLeft}
                            className={`absolute left-0 top-1/2 z-10 hidden h-11 w-11 -translate-y-1/2 place-items-center rounded-full border border-border-medium bg-background-secondary/95 text-text-primary transition-opacity duration-200 disabled:pointer-events-none md:grid ${
                                scrollState.canLeft ? 'opacity-100' : 'opacity-0'
                            }`}
                        >
                            <ChevronLeft className="h-5 w-5" aria-hidden="true" />
                        </button>
                        <button
                            type="button"
                            onClick={() => scrollByPage(1)}
                            aria-label={`Scroll ${ariaLabel ?? title} forward`}
                            disabled={!scrollState.canRight}
                            className={`absolute right-0 top-1/2 z-10 hidden h-11 w-11 -translate-y-1/2 place-items-center rounded-full border border-border-medium bg-background-secondary/95 text-text-primary transition-opacity duration-200 disabled:pointer-events-none md:grid ${
                                scrollState.canRight ? 'opacity-100' : 'opacity-0'
                            }`}
                        >
                            <ChevronRight className="h-5 w-5" aria-hidden="true" />
                        </button>
                    </>
                )}
            </div>
        </section>
    )
}
