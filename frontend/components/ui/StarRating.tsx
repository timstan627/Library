'use client'

import { Star } from 'lucide-react'

interface StarRatingProps {
    value: number
    onChange?: (value: number) => void
    readonly?: boolean
    size?: 'sm' | 'md' | 'lg'
}

export function StarRating({
    value,
    onChange,
    readonly = false,
    size = 'md',
}: StarRatingProps) {
    const sizes = {
        sm: 'w-4 h-4',
        md: 'w-5 h-5',
        lg: 'w-6 h-6',
    }

    return (
        <div className="flex items-center gap-0.5">
            {[1, 2, 3, 4, 5].map((star) => (
                <button
                    key={star}
                    type="button"
                    onClick={() => !readonly && onChange?.(star)}
                    disabled={readonly}
                    className={`${readonly ? 'cursor-default' : 'cursor-pointer'} p-0.5 transition-transform hover:scale-110 disabled:hover:scale-100`}
                >
                    <Star
                        className={`${sizes[size]} ${star <= value
                                ? 'fill-yellow-500 text-yellow-500'
                                : 'text-text-muted'
                            }`}
                    />
                </button>
            ))}
        </div>
    )
}


interface RatingDisplayProps {
    average: number | null
    count: number
    showCount?: boolean
}

export function RatingDisplay({ average, count, showCount = true }: RatingDisplayProps) {
    if (!average && count === 0) {
        return <span className="text-text-muted text-sm">No ratings</span>
    }

    return (
        <div className="flex items-center gap-2">
            <StarRating value={Math.round(average || 0)} readonly size="sm" />
            <span className="text-text-secondary text-sm">
                {average?.toFixed(1) || 'N/A'}
                {showCount && ` (${count})`}
            </span>
        </div>
    )
}
