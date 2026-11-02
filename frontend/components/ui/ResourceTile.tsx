'use client'

import Link from 'next/link'
import { Star, Eye, Download } from 'lucide-react'

/**
 * Compact vertical tile for catalog shelf rows.
 *
 * Render rules from the catalog research (docs/research/2026-11-02-netflix-catalog-homepage.md):
 * - Rating average is shown only when `rating_count >= 3` (a lone 5-star
 *   average is misleading at this site's scale).
 * - Every tile carries an explicit kind chip (course code / file format), the
 *   "explicit differences" rule for near-duplicate material.
 * - Whole tile is one link; saved-collection items carry no stats and fall
 *   back to file size + format only.
 */

const EXT_STYLES: Record<string, string> = {
    pdf: 'bg-danger/10 text-danger-light border-danger/30',
    doc: 'bg-accent-primary/10 text-accent-light border-accent-primary/30',
    docx: 'bg-accent-primary/10 text-accent-light border-accent-primary/30',
    txt: 'bg-accent-primary/10 text-accent-light border-accent-primary/30',
    md: 'bg-warning/10 text-warning-light border-warning/30',
    ppt: 'bg-violet/10 text-violet-light border-violet/30',
    pptx: 'bg-violet/10 text-violet-light border-violet/30',
    xls: 'bg-success/10 text-success-light border-success/30',
    xlsx: 'bg-success/10 text-success-light border-success/30',
    csv: 'bg-success/10 text-success-light border-success/30',
    zip: 'bg-warning/10 text-warning-light border-warning/30',
    rar: 'bg-warning/10 text-warning-light border-warning/30',
}

const DEFAULT_EXT_STYLE = 'bg-background-tertiary text-text-secondary border-border-medium'

export interface ResourceTileData {
    title: string
    slug: string
    course_code?: string
    file_extension?: string
    file_size?: number
    views?: number
    downloads?: number
    rating_count?: number
    average_rating?: number | null
    uploader_name?: string
    added_at?: string
}

function formatSize(bytes?: number): string {
    if (!bytes || bytes <= 0) return ''
    if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function extLabel(ext?: string): string {
    return (ext || 'file').toUpperCase()
}

export function ResourceTile({ resource, compact }: {
    resource: ResourceTileData
    /** Saved-collection items: no public stats available — smaller, statless tile. */
    compact?: boolean
}) {
    const ext = resource.file_extension?.toLowerCase()
    const extStyle = EXT_STYLES[ext ?? ''] ?? DEFAULT_EXT_STYLE
    const showRating = !compact
        && typeof resource.rating_count === 'number'
        && resource.rating_count >= 3
        && typeof resource.average_rating === 'number'

    return (
        <Link
            href={`/resources/${resource.slug}`}
            aria-label={`${resource.title}${resource.course_code ? ` (${resource.course_code})` : ''}`}
            className="card card-interactive flex h-full min-h-[8.5rem] flex-col p-3.5"
        >
            <div className="flex items-center justify-between gap-2">
                <span
                    className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-semibold tracking-wide ${extStyle}`}
                >
                    {extLabel(resource.file_extension)}
                </span>
                {showRating && (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-warning-light">
                        <Star className="h-3.5 w-3.5 fill-warning text-warning" aria-hidden="true" />
                        <span className="tabular-nums">{resource.average_rating!.toFixed(1)}</span>
                    </span>
                )}
            </div>

            <h3 className="mt-2 line-clamp-2 text-sm font-medium leading-snug text-text-primary">
                {resource.title}
            </h3>

            <div className="mt-auto pt-2">
                {resource.course_code && (
                    <span className="badge text-[11px] leading-none">{resource.course_code}</span>
                )}
                {!compact && (
                    <div className="mt-2 flex items-center gap-3 text-[11px] text-text-muted">
                        <span className="tabular-nums inline-flex items-center gap-1">
                            <Eye className="h-3 w-3" aria-hidden="true" />
                            {resource.views ?? 0}
                        </span>
                        <span className="tabular-nums inline-flex items-center gap-1">
                            <Download className="h-3 w-3" aria-hidden="true" />
                            {resource.downloads ?? 0}
                        </span>
                        {formatSize(resource.file_size) && (
                            <span className="hidden sm:inline">{formatSize(resource.file_size)}</span>
                        )}
                    </div>
                )}
                {compact && formatSize(resource.file_size) && (
                    <p className="mt-2 text-[11px] text-text-muted">{formatSize(resource.file_size)}</p>
                )}
            </div>
        </Link>
    )
}

export function ResourceTileSkeleton() {
    return (
        <div className="card h-full min-h-[8.5rem] p-3.5 skeleton" aria-hidden="true">
            <div className="h-4 w-10 rounded bg-background-tertiary" />
            <div className="mt-2 h-3.5 w-3/4 rounded bg-background-tertiary" />
            <div className="mt-1.5 h-3.5 w-1/2 rounded bg-background-tertiary" />
            <div className="mt-auto h-3 w-1/3 rounded bg-background-tertiary" />
        </div>
    )
}
