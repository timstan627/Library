'use client'

import { ReactNode } from 'react'
import { FileText, Upload, Search, Plus } from 'lucide-react'
import Link from 'next/link'

interface EmptyStateProps {
    icon?: ReactNode
    title: string
    description: string
    action?: {
        label: string
        href?: string
        onClick?: () => void
    }
}

/**
 * Empty state component for when there's no content to display.
 * Explains why it's empty and suggests next action.
 */
export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
    return (
        <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
            <div className="w-16 h-16 bg-background-tertiary rounded-full flex items-center justify-center mb-6">
                {icon || <FileText className="w-8 h-8 text-text-muted" />}
            </div>

            <h3 className="text-xl font-semibold text-text-primary mb-2">
                {title}
            </h3>

            <p className="text-text-secondary max-w-sm mb-6">
                {description}
            </p>

            {action && (
                action.href ? (
                    <Link href={action.href} className="btn btn-primary">
                        {action.label}
                    </Link>
                ) : (
                    <button onClick={action.onClick} className="btn btn-primary">
                        {action.label}
                    </button>
                )
            )}
        </div>
    )
}

/**
 * Common empty state presets
 */
export const EmptyStates = {
    NoResources: () => (
        <EmptyState
            icon={<FileText className="w-8 h-8 text-text-muted" />}
            title="No resources yet"
            description="Be the first to share study materials with your peers."
            action={{ label: 'Upload Resource', href: '/upload' }}
        />
    ),

    NoSearchResults: () => (
        <EmptyState
            icon={<Search className="w-8 h-8 text-text-muted" />}
            title="No results found"
            description="Try adjusting your search or filters to find what you're looking for."
        />
    ),

    NoUploads: () => (
        <EmptyState
            icon={<Upload className="w-8 h-8 text-text-muted" />}
            title="No uploads yet"
            description="Start sharing your notes and study materials."
            action={{ label: 'Upload Now', href: '/upload' }}
        />
    ),
}

/**
 * Page loading skeleton
 */
export function PageLoadingSkeleton() {
    return (
        <div className="animate-pulse">
            {/* Header skeleton */}
            <div className="h-8 bg-background-tertiary rounded w-1/3 mb-4" />
            <div className="h-4 bg-background-tertiary rounded w-2/3 mb-8" />

            {/* Content skeleton */}
            <div className="grid md:grid-cols-3 gap-4">
                {[...Array(6)].map((_, i) => (
                    <div key={i} className="bg-background-secondary rounded-lg p-4">
                        <div className="h-4 bg-background-tertiary rounded w-3/4 mb-3" />
                        <div className="h-3 bg-background-tertiary rounded w-1/2 mb-2" />
                        <div className="h-3 bg-background-tertiary rounded w-2/3" />
                    </div>
                ))}
            </div>
        </div>
    )
}

/**
 * Table loading skeleton
 */
export function TableLoadingSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
    return (
        <div className="animate-pulse">
            {/* Header */}
            <div className="flex gap-4 p-4 border-b border-border-subtle">
                {[...Array(columns)].map((_, i) => (
                    <div key={i} className="h-4 bg-background-tertiary rounded flex-1" />
                ))}
            </div>

            {/* Rows */}
            {[...Array(rows)].map((_, rowIndex) => (
                <div key={rowIndex} className="flex gap-4 p-4 border-b border-border-subtle">
                    {[...Array(columns)].map((_, colIndex) => (
                        <div
                            key={colIndex}
                            className="h-4 bg-background-tertiary rounded flex-1"
                            style={{ width: `${Math.random() * 40 + 60}%` }}
                        />
                    ))}
                </div>
            ))}
        </div>
    )
}

/**
 * Card grid loading skeleton
 */
export function CardGridSkeleton({ count = 6 }: { count?: number }) {
    return (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
            {[...Array(count)].map((_, i) => (
                <div key={i} className="bg-background-secondary rounded-lg p-4 border border-border-subtle">
                    <div className="flex items-start gap-3">
                        <div className="w-10 h-10 bg-background-tertiary rounded-lg shrink-0" />
                        <div className="flex-1">
                            <div className="h-4 bg-background-tertiary rounded w-3/4 mb-2" />
                            <div className="h-3 bg-background-tertiary rounded w-1/2" />
                        </div>
                    </div>
                    <div className="mt-4 space-y-2">
                        <div className="h-3 bg-background-tertiary rounded" />
                        <div className="h-3 bg-background-tertiary rounded w-4/5" />
                    </div>
                </div>
            ))}
        </div>
    )
}
