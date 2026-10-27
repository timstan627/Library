'use client'

import { AlertTriangle, RefreshCw } from 'lucide-react'

/**
 * Inline error banner for failed data fetches.
 *
 * Use this instead of letting a failed request fall through to an empty
 * state — "no results" tells the user the data is gone when really the
 * request just failed. Optionally pass a retry callback.
 */
export default function FetchError({
    message = 'Failed to load data. Please check your connection and try again.',
    onRetry,
    className = '',
}: {
    message?: string
    onRetry?: () => void
    className?: string
}) {
    return (
        <div
            role="alert"
            className={`flex items-center justify-between gap-4 rounded-xl border border-danger/20 bg-danger/10 px-4 py-3 ${className}`}
        >
            <div className="flex items-center gap-2.5 min-w-0">
                <AlertTriangle className="w-4 h-4 shrink-0 text-danger" />
                <p className="text-sm text-text-primary truncate">{message}</p>
            </div>
            {onRetry && (
                <button
                    onClick={onRetry}
                    className="flex items-center gap-1.5 shrink-0 text-xs font-semibold text-danger hover:underline"
                >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Retry
                </button>
            )}
        </div>
    )
}
