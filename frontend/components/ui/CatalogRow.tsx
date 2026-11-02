'use client'

import React, { useCallback, useEffect, useMemo, useRef } from 'react'
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
 * - Arrows: always rendered (never injected on hover → no CLS), hidden on
 *   touch screens (swipe covers them), scroll ~85% of the row per press,
 *   disabled — not removed — at both ends.
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
    const leftBtnRef = useRef<HTMLButtonElement | null>(null)
    const rightBtnRef = useRef<HTMLButtonElement | null>(null)
    const reducedMotion = useMemo(() => (
        typeof window !== 'undefined'
        && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ), [])

    const updateArrowState = useCallback(() => {
        const track = trackRef.current
        if (!track) return
        const maxScroll = track.scrollWidth - track.clientWidth
        if (leftBtnRef.current) {
            leftBtnRef.current.disabled = track.scrollLeft <= 2
        }
        if (rightBtnRef.current) {
            rightBtnRef.current.disabled = track.scrollLeft >= maxScroll - 2
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

                {/* Scroll controls: rendered from first paint, disabled at the ends.
                    Touch devices swipe natively, so arrows are desktop-only. */}
                <button
                    ref={leftBtnRef}
                    type="button"
                    onClick={() => scrollByPage(-1)}
                    aria-label={`Scroll ${ariaLabel ?? title} backward`}
                    disabled
                    className="absolute left-0 top-1/2 z-10 hidden h-11 w-11 -translate-y-1/2 place-items-center rounded-full border border-border-medium bg-background-secondary/95 text-text-primary disabled:pointer-events-none md:grid"
                >
                    <ChevronLeft className="h-5 w-5" aria-hidden="true" />
                </button>
                <button
                    ref={rightBtnRef}
                    type="button"
                    onClick={() => scrollByPage(1)}
                    aria-label={`Scroll ${ariaLabel ?? title} forward`}
                    disabled
                    className="absolute right-0 top-1/2 z-10 hidden h-11 w-11 -translate-y-1/2 place-items-center rounded-full border border-border-medium bg-background-secondary/95 text-text-primary disabled:pointer-events-none md:grid"
                >
                    <ChevronRight className="h-5 w-5" aria-hidden="true" />
                </button>
            </div>
        </section>
    )
}
