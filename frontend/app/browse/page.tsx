'use client'

import { useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { Search, Filter, X, Download, Star, Eye, FileText, AlertTriangle } from 'lucide-react'
import Link from 'next/link'
import { apiHelpers } from '@/lib/api'
import { SkeletonResourceGrid } from '@/components/ui/Skeleton'
import FetchError from '@/components/ui/FetchError'

interface Resource {
    id: string
    title: string
    slug: string
    description?: string
    course_code: string
    department?: string
    file_name: string
    file_size: number
    file_extension: string
    downloads: number
    views: number
    average_rating?: number
    rating_count: number
    created_at: string
    tags?: string[]
    uploader_name?: string
}

import { Suspense } from 'react'

function BrowseContent() {
    const searchParams = useSearchParams()
    const router = useRouter()

    const [resources, setResources] = useState<Resource[]>([])
    const [loading, setLoading] = useState(true)
    const [total, setTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [showFilters, setShowFilters] = useState(false)
    const [filterOptions, setFilterOptions] = useState<{ departments: string[], courses: string[] }>({ departments: [], courses: [] })
    const [filtersError, setFiltersError] = useState(false)

    // Search state
    const [query, setQuery] = useState(searchParams.get('q') || '')
    const [department, setDepartment] = useState(searchParams.get('department') || '')
    const [sortBy, setSortBy] = useState(searchParams.get('sort_by') || 'recent')

    // Sync state with URL params when they change (e.g. from Header search)
    useEffect(() => {
        const q = searchParams.get('q') || ''
        const dept = searchParams.get('department') || ''
        const sort = searchParams.get('sort_by') || 'recent'

        setQuery(q)
        setDepartment(dept)
        setSortBy(sort)
    }, [searchParams])

    useEffect(() => {
        fetchResources()
        fetchFilters()
    }, [page, sortBy, query, department]) // Add query and department to dependencies

    const fetchFilters = async () => {
        try {
            const res = await apiHelpers.getFilterOptions()
            setFilterOptions({
                departments: res.data.departments || [],
                courses: res.data.courses || []
            })
            setFiltersError(false)
        } catch (err) {
            console.error('Failed to fetch filter options', err)
            setFiltersError(true)
        }
    }

    const [searchError, setSearchError] = useState('')

    const fetchResources = async () => {
        setLoading(true)
        setSearchError('')
        try {
            const params = {
                q: query || undefined,
                department: department || undefined,
                sort_by: sortBy,
                page,
                size: 20,
            }
            const response = await apiHelpers.search(params)
            setResources(response.data.results)
            setTotal(response.data.total)
        } catch (error: any) {
            console.error('Failed to fetch resources:', error)
            setSearchError(error.response?.data?.detail || 'Failed to load resources. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        setPage(1)
        // Sync search params to URL for sharable links
        const params = new URLSearchParams()
        if (query) params.set('q', query)
        if (department) params.set('department', department)
        if (sortBy !== 'recent') params.set('sort_by', sortBy)
        const newUrl = params.toString() ? `/browse?${params.toString()}` : '/browse'
        router.push(newUrl, { scroll: false })
    }

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    const formatDate = (dateString: string) => {
        const date = new Date(dateString)
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
        })
    }

    return (
        <div className="container-custom py-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-text-primary mb-2">Browse Resources</h1>
                <p className="text-text-secondary">
                    Discover {total.toLocaleString()} study materials shared by students
                </p>
            </div>

            {/* Search Bar */}
            <form onSubmit={handleSearch} className="mb-8">
                <div className="flex items-stretch gap-3">
                    <div className="relative flex-1">
                        <Search aria-hidden="true" className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                        <input
                            type="text"
                            aria-label="Search resources"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Search by title, course code, or description..."
                            className="input pl-12 h-full"
                        />
                    </div>
                    <button type="submit" className="btn btn-primary">
                        Search
                    </button>
                    <button
                        type="button"
                        onClick={() => setShowFilters(!showFilters)}
                        className="btn btn-secondary"
                    >
                        <Filter className="w-4 h-4 mr-2" />
                        Filters
                    </button>
                </div>

                {/* Filters Panel */}
                {showFilters && (
                    <div className="card p-4 mt-4 animate-fade-in">
                        {filtersError && (
                            <FetchError
                                message="Filter options could not be loaded. Department filtering may be unavailable."
                                onRetry={fetchFilters}
                                className="mb-4"
                            />
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <div>
                                <label className="label">Department</label>
                                <select
                                    value={department}
                                    onChange={(e) => setDepartment(e.target.value)}
                                    className="input"
                                >
                                    <option value="">All Departments</option>
                                    {filterOptions.departments.map((dept) => (
                                        <option key={dept} value={dept}>{dept}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="label">Sort By</label>
                                <select
                                    value={sortBy}
                                    onChange={(e) => setSortBy(e.target.value)}
                                    className="input"
                                >
                                    <option value="recent">Most Recent</option>
                                    <option value="downloads">Most Downloaded</option>
                                    <option value="rating">Highest Rated</option>
                                    <option value="relevance">Relevance</option>
                                </select>
                            </div>
                            <div className="md:col-span-2 flex items-end">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setQuery('')
                                        setDepartment('')
                                        setSortBy('recent')
                                    }}
                                    className="btn btn-ghost"
                                >
                                    <X className="w-4 h-4 mr-2" />
                                    Clear Filters
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </form>

            {/* Search Error */}
            {searchError && (
                <div className="mb-6 p-4 bg-danger/10 border border-danger/20 rounded-lg text-danger-light text-sm animate-fade-in flex items-start gap-2" role="alert">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{searchError}</span>
                </div>
            )}

            {/* Results */}
            {loading ? (
                <SkeletonResourceGrid count={6} />
            ) : resources.length === 0 ? (
                <div className="text-center py-16">
                    <FileText className="w-16 h-16 text-text-muted mx-auto mb-4" />
                    <h2 className="text-xl font-medium text-text-primary mb-2">No resources found</h2>
                    <p className="text-text-secondary mb-6">
                        Try adjusting your search or filters
                    </p>
                    <Link href="/upload" className="btn btn-primary">
                        Upload First Resource
                    </Link>
                </div>
            ) : (
                <div className="stagger grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {resources.map((resource) => (
                        <Link
                            key={resource.id}
                            href={`/resources/${resource.slug}`}
                            className="card card-interactive p-4 block"
                        >
                            <div className="flex items-start gap-3">
                                <div className="w-10 h-10 bg-accent-primary/10 rounded-md flex items-center justify-center shrink-0">
                                    <FileText className="w-5 h-5 text-accent-primary" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h2 className="font-medium text-text-primary truncate">
                                        {resource.title}
                                    </h2>
                                    <div className="flex flex-wrap gap-x-2 text-sm text-text-secondary tabular-nums">
                                        {resource.uploader_name && <span className="font-medium text-text-primary">{resource.uploader_name}</span>}
                                        <span>{resource.course_code}</span>
                                        <span>{formatFileSize(resource.file_size)}</span>
                                    </div>
                                </div>
                            </div>

                            {resource.description && (
                                <p className="text-sm text-text-muted mt-3 line-clamp-2">
                                    {resource.description}
                                </p>
                            )}

                            <div className="flex items-center gap-4 mt-4 text-xs text-text-muted tabular-nums">
                                <span className="flex items-center gap-1">
                                    <Download className="w-3.5 h-3.5" />
                                    {resource.downloads}
                                </span>
                                <span className="flex items-center gap-1">
                                    <Eye className="w-3.5 h-3.5" />
                                    {resource.views}
                                </span>
                                {resource.average_rating && (
                                    <span className="flex items-center gap-1">
                                        <Star aria-hidden="true" className="w-3.5 h-3.5" />
                                        {resource.average_rating.toFixed(1)}
                                    </span>
                                )}
                            </div>

                            {resource.tags && resource.tags.length > 0 && (
                                <div className="flex flex-wrap gap-1.5 mt-3">
                                    {resource.tags.slice(0, 3).map((tag) => (
                                        <span key={tag} className="badge text-xs">
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </Link>
                    ))}
                </div>
            )}

            {/* Pagination */}
            {total > 20 && (
                <div className="flex justify-center gap-2 mt-8">
                    <button
                        onClick={() => setPage(Math.max(1, page - 1))}
                        disabled={page === 1}
                        className="btn btn-secondary disabled:opacity-50"
                    >
                        Previous
                    </button>
                    <span className="flex items-center px-4 text-text-secondary tabular-nums">
                        Page {page} of {Math.ceil(total / 20)}
                    </span>
                    <button
                        onClick={() => setPage(page + 1)}
                        disabled={page >= Math.ceil(total / 20)}
                        className="btn btn-secondary disabled:opacity-50"
                    >
                        Next
                    </button>
                </div>
            )}
        </div>
    )
}

export default function BrowsePage() {
    return (
        <Suspense fallback={<div className="container-custom py-20 text-center">Loading...</div>}>
            <BrowseContent />
        </Suspense>
    )
}
