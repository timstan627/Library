import Link from 'next/link'
import { Download, Eye, Star, FileText } from 'lucide-react'

interface ResourceCardProps {
    id: string
    title: string
    slug: string
    description?: string
    course_code: string
    file_size: number
    file_extension: string
    downloads: number
    views: number
    average_rating?: number
    rating_count: number
    tags?: string[]
    uploader_name?: string
}

function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function ResourceCard({
    title,
    slug,
    description,
    course_code,
    file_size,
    file_extension,
    downloads,
    views,
    average_rating,
    rating_count,
    tags,
    uploader_name,
}: ResourceCardProps) {
    return (
        <Link
            href={`/resources/${slug}`}
            className="card p-4 hover:border-border-medium transition-colors animate-fade-in block"
        >
            <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-accent-primary/10 rounded-md flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5 text-accent-primary" />
                </div>
                <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-text-primary truncate">{title}</h3>
                    <div className="flex flex-wrap gap-x-3 text-sm text-text-secondary">
                        {uploader_name && <span className="font-medium text-text-primary">{uploader_name}</span>}
                        <span>{course_code}</span>
                        <span>{formatFileSize(file_size)}</span>
                        <span>{file_extension.toUpperCase()}</span>
                    </div>
                </div>
            </div>

            {description && (
                <p className="text-sm text-text-muted mt-3 line-clamp-2">{description}</p>
            )}

            <div className="flex items-center gap-4 mt-4 text-xs text-text-muted">
                <span className="flex items-center gap-1">
                    <Download className="w-3.5 h-3.5" />
                    {downloads}
                </span>
                <span className="flex items-center gap-1">
                    <Eye className="w-3.5 h-3.5" />
                    {views}
                </span>
                {average_rating && (
                    <span className="flex items-center gap-1">
                        <Star className="w-3.5 h-3.5 fill-warning text-warning" />
                        {average_rating.toFixed(1)}
                    </span>
                )}
            </div>

            {tags && tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3">
                    {tags.slice(0, 3).map((tag) => (
                        <span key={tag} className="badge text-xs">
                            {tag}
                        </span>
                    ))}
                    {tags.length > 3 && (
                        <span className="text-text-muted text-xs">+{tags.length - 3}</span>
                    )}
                </div>
            )}
        </Link>
    )
}


export function ResourceCardSkeleton() {
    return (
        <div className="card p-4 animate-pulse">
            <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-background-tertiary rounded-md" />
                <div className="flex-1">
                    <div className="h-5 bg-background-tertiary rounded w-3/4 mb-2" />
                    <div className="h-4 bg-background-tertiary rounded w-1/2" />
                </div>
            </div>
            <div className="h-4 bg-background-tertiary rounded w-full mt-3" />
            <div className="flex gap-4 mt-4">
                <div className="h-4 bg-background-tertiary rounded w-12" />
                <div className="h-4 bg-background-tertiary rounded w-12" />
            </div>
        </div>
    )
}
