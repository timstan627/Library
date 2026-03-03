'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import {
    Download, Star, Eye, FileText, Calendar, User, Tag, Share2, Flag,
    ArrowLeft, Lock, CheckCircle, Clock, X, Edit3, Save, Loader2, Trash2
} from 'lucide-react'
import { apiHelpers, api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { SkeletonResourceDetail } from '@/components/ui/Skeleton'
import { ProgressBar } from '@/components/ui/ProgressBar'

interface Resource {
    id: string
    title: string
    slug: string
    description?: string
    course_code: string
    department?: string
    semester?: string
    branch?: string
    file_name: string
    file_size: number
    file_extension: string
    mime_type: string
    downloads: number
    views: number
    average_rating?: number
    rating_count: number
    visibility: string
    is_password_protected: boolean
    moderation_status: string
    uploader_id?: string
    uploader_name?: string
    created_at: string
    updated_at: string
    tags?: string[]
}

interface Rating {
    id: string
    user_id: string
    value: number
    review?: string
    created_at: string
    user_name?: string
}

export default function ResourceDetailPage() {
    const params = useParams()
    const router = useRouter()
    const pathname = usePathname()
    const { user, isAuthenticated } = useAuth()
    const slug = params.slug as string

    const [resource, setResource] = useState<Resource | null>(null)
    const [ratings, setRatings] = useState<Rating[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [actionError, setActionError] = useState('')
    const [downloading, setDownloading] = useState(false)
    const [downloadProgress, setDownloadProgress] = useState(0)
    const [password, setPassword] = useState('')
    const [showPasswordPrompt, setShowPasswordPrompt] = useState(false)

    // Preview state
    const [previewing, setPreviewing] = useState(false)
    const [previewUrl, setPreviewUrl] = useState<string | null>(null)
    const [showPreviewModal, setShowPreviewModal] = useState(false)

    // Rating form
    const [userRating, setUserRating] = useState(0)
    const [userReview, setUserReview] = useState('')
    const [submittingRating, setSubmittingRating] = useState(false)
    const fetchedRef = useRef(false)

    // Edit state
    const [showEditModal, setShowEditModal] = useState(false)
    const [editSaving, setEditSaving] = useState(false)
    const [editError, setEditError] = useState('')
    const [editForm, setEditForm] = useState({
        title: '',
        description: '',
        course_code: '',
        department: '',
        semester: '',
        tags: '',
        visibility: 'public',
    })

    // Determine if user can edit (owner or admin/moderator)
    const canEdit = isAuthenticated && resource && user && (
        resource.uploader_id === user.id ||
        user.role === 'admin' ||
        user.role === 'moderator'
    )

    useEffect(() => {
        if (fetchedRef.current) return
        fetchedRef.current = true
        fetchResource()
    }, [slug])

    const fetchResource = async () => {
        try {
            const response = await apiHelpers.getResourceBySlug(slug)
            setResource(response.data)

            // Fetch ratings
            const ratingsResponse = await apiHelpers.getResourceRatings(response.data.id)
            setRatings(ratingsResponse.data.results)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Resource not found')
        } finally {
            setLoading(false)
        }
    }

    const handlePreview = async () => {
        if (!resource) return

        if (resource.is_password_protected && !password) {
            setShowPasswordPrompt(true)
            return
        }

        // If we already have a preview URL, just show it
        if (previewUrl) {
            setShowPreviewModal(true)
            return
        }

        setPreviewing(true)
        try {
            const response = await api.get(`/resources/${resource.id}/preview`, {
                params: { password: password || undefined },
                responseType: 'blob',
            })

            const mimeType = resource.mime_type || response.headers['content-type']
            const type = mimeType.split('/')[0]

            // Create object URL
            const url = window.URL.createObjectURL(new Blob([response.data], { type: mimeType }))
            setPreviewUrl(url)
            setShowPreviewModal(true)

            // Update view count locally
            setResource(prev => prev ? { ...prev, views: prev.views + 1 } : null)
        } catch (err: any) {
            console.error('Preview failed:', err)
            setActionError('Preview failed: ' + (err.response?.data?.detail || 'Unknown error'))
            setTimeout(() => setActionError(''), 5000)
        } finally {
            setPreviewing(false)
        }
    }

    const handleDownload = async () => {
        if (!resource) return

        if (resource.is_password_protected && !password) {
            setShowPasswordPrompt(true)
            return
        }

        setDownloading(true)
        setDownloadProgress(0)
        try {
            const response = await api.get(`/resources/${resource.id}/download`, {
                params: { password: password || undefined },
                responseType: 'blob',
                onDownloadProgress: (progressEvent) => {
                    const total = progressEvent.total || resource.file_size
                    const current = progressEvent.loaded
                    const pct = Math.floor((current / total) * 100)
                    setDownloadProgress(pct)
                }
            })

            // Create download link
            const url = window.URL.createObjectURL(new Blob([response.data]))
            const link = document.createElement('a')
            link.href = url
            link.setAttribute('download', resource.file_name)
            document.body.appendChild(link)
            link.click()
            link.remove()
            window.URL.revokeObjectURL(url)

            setDownloadProgress(100)

            // Update download count
            setResource(prev => prev ? { ...prev, downloads: prev.downloads + 1 } : null)
        } catch (err: any) {
            console.error('Download failed:', err)
            const errorMessage = err.response?.data?.detail || err.message || 'Download failed'
            setActionError(`Download failed: ${errorMessage}`)
            setTimeout(() => setActionError(''), 5000)
        } finally {
            setDownloading(false)
            setShowPasswordPrompt(false)
        }
    }

    const handleStarClick = (star: number) => {
        setUserRating(star)
    }

    const confirmStarRating = async () => {
        if (!resource || userRating === 0) return

        setSubmittingRating(true)
        try {
            await apiHelpers.createRating(resource.id, {
                value: userRating,
            })

            // Update stats
            const ratingsResponse = await apiHelpers.getResourceRatings(resource.id)
            setResource(prev => prev ? {
                ...prev,
                average_rating: ratingsResponse.data.average_rating,
                rating_count: ratingsResponse.data.rating_count,
            } : null)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to rate')
        } finally {
            setSubmittingRating(false)
        }
    }

    const handleCommentSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!resource || !userReview.trim()) return

        setSubmittingRating(true)
        try {
            await apiHelpers.createRating(resource.id, {
                value: 0, // Comment only
                review: userReview,
            })

            // Refresh ratings list
            const ratingsResponse = await apiHelpers.getResourceRatings(resource.id)
            setRatings(ratingsResponse.data.results)

            setUserReview('')
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to post comment')
        } finally {
            setSubmittingRating(false)
        }
    }

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        })
    }

    const [copied, setCopied] = useState(false)
    const [deleting, setDeleting] = useState(false)
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

    const handleShare = async () => {
        try {
            await navigator.clipboard.writeText(window.location.href)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch {
            // Fallback for older browsers
            const input = document.createElement('input')
            input.value = window.location.href
            document.body.appendChild(input)
            input.select()
            document.execCommand('copy')
            document.body.removeChild(input)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        }
    }

    const openEditModal = () => {
        if (!resource) return
        setEditForm({
            title: resource.title || '',
            description: resource.description || '',
            course_code: resource.course_code || '',
            department: resource.department || '',
            semester: resource.semester || '',
            tags: resource.tags?.join(', ') || '',
            visibility: resource.visibility || 'public',
        })
        setEditError('')
        setShowEditModal(true)
    }

    const handleEditSave = async () => {
        if (!resource) return
        setEditSaving(true)
        setEditError('')

        try {
            const updateData: any = {}
            if (editForm.title.trim() && editForm.title !== resource.title)
                updateData.title = editForm.title.trim()
            if (editForm.description !== (resource.description || ''))
                updateData.description = editForm.description.trim() || null
            if (editForm.course_code.trim() && editForm.course_code !== resource.course_code)
                updateData.course_code = editForm.course_code.trim()
            if (editForm.department !== (resource.department || ''))
                updateData.department = editForm.department.trim() || null
            if (editForm.semester !== (resource.semester || ''))
                updateData.semester = editForm.semester.trim() || null
            if (editForm.visibility !== resource.visibility)
                updateData.visibility = editForm.visibility

            // Handle tags
            const newTags = editForm.tags
                .split(',')
                .map(t => t.trim().toLowerCase())
                .filter(t => t.length > 0)
            const oldTags = resource.tags || []
            if (JSON.stringify(newTags.sort()) !== JSON.stringify([...oldTags].sort())) {
                updateData.tags = newTags
            }

            if (Object.keys(updateData).length === 0) {
                setShowEditModal(false)
                return
            }

            await apiHelpers.updateResource(resource.id, updateData)

            // Refresh resource data
            const response = await apiHelpers.getResourceBySlug(slug)
            setResource(response.data)

            setShowEditModal(false)
        } catch (err: any) {
            setEditError(err.response?.data?.detail || 'Failed to update resource')
        } finally {
            setEditSaving(false)
        }
    }

    const handleDelete = async () => {
        if (!resource) return
        setDeleting(true)
        try {
            await apiHelpers.deleteResource(resource.id)
            router.push('/browse')
        } catch (err: any) {
            setActionError(err.response?.data?.detail || 'Failed to delete resource')
            setDeleting(false)
            setShowDeleteConfirm(false)
        }
    }

    if (loading) {
        return (
            <div className="container-custom py-8">
                <SkeletonResourceDetail />
            </div>
        )
    }

    if (error || !resource) {
        return (
            <div className="container-custom py-20 text-center">
                <FileText className="w-16 h-16 text-text-muted mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-text-primary mb-2">Resource Not Found</h2>
                <p className="text-text-secondary mb-6">{error || 'This resource does not exist.'}</p>
                <Link href="/browse" className="btn btn-primary">
                    Browse Resources
                </Link>
            </div>
        )
    }

    return (
        <div className="container-custom py-8">
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-text-secondary mb-6">
                <Link href="/" className="hover:text-text-primary">Home</Link>
                <span>/</span>
                <Link href="/browse" className="hover:text-text-primary">Browse</Link>
                <span>/</span>
                <span className="text-text-primary">{resource.course_code}</span>
            </div>

            <div className="grid lg:grid-cols-3 gap-8">
                {/* Left Column - Main Content + Reviews */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Header */}
                    <div className="card p-6">
                        <div className="flex items-start gap-4">
                            <div className="w-14 h-14 bg-accent-primary/10 rounded-lg flex items-center justify-center shrink-0">
                                <FileText className="w-7 h-7 text-accent-primary" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-start justify-between gap-3">
                                    <h1 className="text-2xl font-bold text-text-primary mb-2">
                                        {resource.title}
                                    </h1>
                                    {canEdit && (
                                        <div className="flex items-center gap-2 shrink-0">
                                            <button
                                                onClick={openEditModal}
                                                className="btn btn-sm bg-accent-primary/10 text-accent-primary hover:bg-accent-primary/20 transition-colors"
                                                title="Edit resource"
                                            >
                                                <Edit3 className="w-4 h-4 mr-1.5" />
                                                Edit
                                            </button>
                                            <button
                                                onClick={() => setShowDeleteConfirm(true)}
                                                className="btn btn-sm bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                                                title="Delete resource"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    )}
                                </div>
                                <div className="flex flex-wrap items-center gap-3 text-sm text-text-secondary">
                                    <span className="badge badge-primary">{resource.course_code}</span>
                                    {resource.department && <span>{resource.department}</span>}
                                    {resource.semester && <span>• {resource.semester}</span>}
                                </div>
                            </div>
                        </div>

                        {/* Stats */}
                        <div className="flex flex-wrap items-center gap-6 mt-6 pt-6 border-t border-border-subtle">
                            <div className="flex items-center gap-2 text-text-secondary">
                                <Download className="w-4 h-4" />
                                <span>{resource.downloads} downloads</span>
                            </div>
                            <div className="flex items-center gap-2 text-text-secondary">
                                <Eye className="w-4 h-4" />
                                <span>{resource.views} views</span>
                            </div>
                            {resource.average_rating && (
                                <div className="flex items-center gap-2 text-text-secondary">
                                    <Star className="w-4 h-4 fill-yellow-500 text-yellow-500" />
                                    <span>{resource.average_rating.toFixed(1)} ({resource.rating_count} reviews)</span>
                                </div>
                            )}
                            <div className="flex items-center gap-2 text-text-secondary">
                                <Calendar className="w-4 h-4" />
                                <span>{formatDate(resource.created_at)}</span>
                            </div>
                        </div>
                    </div>

                    {/* Description */}
                    {resource.description && (
                        <div className="card p-6">
                            <h2 className="text-lg font-semibold text-text-primary mb-3">Description</h2>
                            <p className="text-text-secondary whitespace-pre-wrap">{resource.description}</p>
                        </div>
                    )}

                    {/* Tags */}
                    {resource.tags && resource.tags.length > 0 && (
                        <div className="card p-6">
                            <h2 className="text-lg font-semibold text-text-primary mb-3">Tags</h2>
                            <div className="flex flex-wrap gap-2">
                                {resource.tags.map((tag) => (
                                    <Link
                                        key={tag}
                                        href={`/browse?tags=${tag}`}
                                        className="badge hover:bg-background-tertiary"
                                    >
                                        <Tag className="w-3 h-3 mr-1" />
                                        {tag}
                                    </Link>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Ratings & Reviews */}
                    <div className="card p-6">
                        <h2 className="text-lg font-semibold text-text-primary mb-4">
                            Ratings & Reviews ({resource.rating_count})
                        </h2>

                        {/* Rating Form */}
                        {isAuthenticated ? (
                            <div className="mb-8 space-y-6">
                                {/* Star Rating Section */}
                                <div className="bg-background-tertiary p-4 rounded-lg">
                                    <h3 className="font-semibold text-text-primary mb-2">Rate this Resource</h3>
                                    <div className="flex items-center gap-2">
                                        <div className="flex gap-1">
                                            {[1, 2, 3, 4, 5].map((star) => (
                                                <button
                                                    key={star}
                                                    type="button"
                                                    onClick={() => handleStarClick(star)}
                                                    className="p-1 hover:scale-110 transition-transform"
                                                >
                                                    <Star
                                                        className={`w-8 h-8 ${star <= userRating
                                                            ? 'fill-yellow-500 text-yellow-500'
                                                            : 'text-text-muted hover:text-yellow-400'
                                                            }`}
                                                    />
                                                </button>
                                            ))}
                                        </div>
                                        <span className="text-sm text-text-secondary ml-2">
                                            {userRating > 0 ? `Selected: ${userRating} stars` : 'Click to rate'}
                                        </span>
                                        {userRating > 0 && (
                                            <button
                                                onClick={confirmStarRating}
                                                disabled={submittingRating}
                                                className="btn btn-sm btn-primary ml-auto"
                                            >
                                                {submittingRating ? 'Saving...' : 'Confirm Rating'}
                                            </button>
                                        )}
                                    </div>
                                </div>

                                {/* Comment Section */}
                                <form onSubmit={handleCommentSubmit} className="pb-6 border-b border-border-subtle">
                                    <div className="mb-4">
                                        <label className="label">Add a Review / Comment</label>
                                        <textarea
                                            value={userReview}
                                            onChange={(e) => setUserReview(e.target.value)}
                                            placeholder="Share your thoughts, ask questions, or provide feedback..."
                                            rows={3}
                                            className="input resize-none"
                                        />
                                    </div>
                                    <button
                                        type="submit"
                                        disabled={!userReview.trim() || submittingRating}
                                        className="btn btn-primary disabled:opacity-50"
                                    >
                                        {submittingRating ? 'Posting...' : 'Post Comment'}
                                    </button>
                                </form>
                            </div>
                        ) : (
                            <div className="mb-6 pb-6 border-b border-border-subtle text-center">
                                <p className="text-text-secondary">
                                    <Link
                                        href={`/auth/login?returnUrl=${encodeURIComponent(pathname)}`}
                                        className="text-accent-light hover:text-accent-primary"
                                    >
                                        Login
                                    </Link>{' '}
                                    to leave a review
                                </p>
                            </div>
                        )}

                        {/* Reviews List */}
                        {ratings.length > 0 ? (
                            <div className="space-y-4">
                                {ratings.map((rating) => (
                                    <div key={rating.id} className="pb-4 border-b border-border-subtle last:border-0">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <div className="w-8 h-8 bg-background-tertiary rounded-full flex items-center justify-center">
                                                    <User className="w-4 h-4 text-text-muted" />
                                                </div>
                                                <span className="text-text-primary font-medium">
                                                    {rating.user_name || 'Anonymous'}
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-1">
                                                {[...Array(5)].map((_, i) => (
                                                    <Star
                                                        key={i}
                                                        className={`w-4 h-4 ${i < rating.value
                                                            ? 'fill-yellow-500 text-yellow-500'
                                                            : 'text-text-muted'
                                                            }`}
                                                    />
                                                ))}
                                            </div>
                                        </div>
                                        {rating.review && (
                                            <p className="text-text-secondary text-sm">{rating.review}</p>
                                        )}
                                        <p className="text-text-muted text-xs mt-2">
                                            {formatDate(rating.created_at)}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-text-muted text-center py-4">No reviews yet</p>
                        )}
                    </div>
                </div>

                {/* Right Sidebar - Download + File Info (sticky at top) */}
                <div className="space-y-6 lg:sticky lg:top-24 lg:self-start">
                    {/* Action Error Banner */}
                    {actionError && (
                        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm animate-fade-in flex items-start gap-2">
                            <span className="shrink-0 mt-0.5">⚠️</span>
                            <span>{actionError}</span>
                        </div>
                    )}

                    {/* Download Card */}
                    <div className="card p-6">
                        <div className="text-center mb-4">
                            <p className="text-2xl font-bold text-text-primary font-mono">
                                {formatFileSize(resource.file_size)}
                            </p>
                            <p className="text-text-secondary text-sm">
                                {resource.file_extension.toUpperCase()} file
                            </p>
                        </div>

                        {resource.is_password_protected && (
                            <div className="flex items-center gap-2 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-md mb-4">
                                <Lock className="w-4 h-4 text-yellow-500" />
                                <span className="text-yellow-500 text-sm">Password protected</span>
                            </div>
                        )}

                        {showPasswordPrompt && (
                            <div className="mb-4">
                                <label className="label">Enter Password</label>
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    className="input mb-2"
                                />
                            </div>
                        )}

                        <button
                            onClick={handleDownload}
                            disabled={downloading}
                            className="btn btn-primary w-full py-3 disabled:opacity-50 transition-all active:scale-[0.98] flex items-center justify-center"
                        >
                            {downloading ? (
                                <div className="flex items-center justify-center gap-2">
                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    {downloadProgress > 0 ? `Downloading ${downloadProgress}%` : 'Starting...'}
                                </div>
                            ) : (
                                <>
                                    <Download className="w-4 h-4 mr-2" />
                                    Download
                                </>
                            )}
                        </button>

                        {downloading && (
                            <div className="mt-4 animate-fade-in">
                                <ProgressBar value={downloadProgress} size="sm" showPercentage={false} />
                            </div>
                        )}

                        {/* Preview Button */}
                        {resource.mime_type && (resource.mime_type.startsWith('image/') || resource.mime_type === 'application/pdf') && (
                            <button
                                onClick={handlePreview}
                                disabled={previewing}
                                className="btn btn-outline w-full mt-4 hover:bg-background-tertiary transition-colors flex items-center justify-center"
                            >
                                {previewing ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
                                        Loading...
                                    </>
                                ) : (
                                    <>
                                        <Eye className="w-4 h-4 mr-2" />
                                        Preview File
                                    </>
                                )}
                            </button>
                        )}

                        {/* Secondary Actions */}
                        <div className="flex gap-2 mt-4 pt-4 border-t border-border-subtle">
                            <button
                                onClick={handleShare}
                                className={`btn btn-secondary flex-1 text-sm border-transparent transition-all ${copied ? 'bg-green-500/20 text-green-400' : 'bg-background-tertiary hover:bg-background-secondary'}`}
                            >
                                {copied ? (
                                    <>
                                        <CheckCircle className="w-4 h-4 mr-2" />
                                        Copied!
                                    </>
                                ) : (
                                    <>
                                        <Share2 className="w-4 h-4 mr-2" />
                                        Share
                                    </>
                                )}
                            </button>
                            <Link
                                href={`/report/${resource.id}`}
                                className="btn btn-ghost flex-1 text-sm text-text-muted hover:text-red-500 hover:bg-red-500/10"
                            >
                                <Flag className="w-4 h-4 mr-2" />
                                Report
                            </Link>
                        </div>
                    </div>

                    {/* File Info */}
                    <div className="card p-6">
                        <h3 className="text-sm font-semibold text-text-primary mb-4">File Information</h3>
                        <div className="space-y-3 text-sm">
                            <div className="flex justify-between">
                                <span className="text-text-secondary">Filename</span>
                                <span className="text-text-primary font-mono text-xs truncate max-w-[150px]">
                                    {resource.file_name}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-text-secondary">Type</span>
                                <span className="text-text-primary">{resource.mime_type}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-text-secondary">Size</span>
                                <span className="text-text-primary">{formatFileSize(resource.file_size)}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-text-secondary">Uploaded</span>
                                <span className="text-text-primary">{formatDate(resource.created_at)}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-text-secondary">Visibility</span>
                                <span className="text-text-primary capitalize">{resource.visibility}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Preview Modal */}
            {showPreviewModal && previewUrl && resource && (
                <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4 animate-fade-in">
                    <div className="bg-white dark:bg-gray-900 w-full h-full max-w-6xl rounded-lg flex flex-col overflow-hidden shadow-2xl">
                        {/* Modal Header */}
                        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950">
                            <h3 className="font-semibold text-lg truncate flex-1 pr-4">{resource.title}</h3>
                            <div className="flex items-center gap-2">
                                <a
                                    href={previewUrl}
                                    download={resource.file_name}
                                    className="btn btn-sm btn-ghost"
                                    title="Download"
                                >
                                    <Download className="w-4 h-4" />
                                </a>
                                <button
                                    onClick={() => setShowPreviewModal(false)}
                                    className="btn btn-sm btn-ghost hover:bg-red-500/10 hover:text-red-500"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                        </div>

                        {/* Modal Content */}
                        <div className="flex-1 bg-gray-100 dark:bg-gray-950 overflow-auto flex items-center justify-center p-4">
                            {resource.mime_type === 'application/pdf' ? (
                                <iframe
                                    src={previewUrl}
                                    className="w-full h-full min-h-[500px] border-0 rounded bg-white"
                                    title="PDF Preview"
                                />
                            ) : (
                                <img
                                    src={previewUrl}
                                    alt="Preview"
                                    className="max-w-full max-h-full object-contain rounded shadow-lg"
                                />
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Edit Modal */}
            {showEditModal && resource && (
                <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 animate-fade-in">
                    <div className="bg-background-secondary w-full max-w-lg rounded-xl shadow-2xl border border-border-subtle overflow-hidden">
                        {/* Modal Header */}
                        <div className="flex items-center justify-between p-5 border-b border-border-subtle">
                            <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
                                <Edit3 className="w-5 h-5 text-accent-primary" />
                                Edit Resource
                            </h3>
                            <button
                                onClick={() => setShowEditModal(false)}
                                className="p-2 hover:bg-background-tertiary rounded-lg transition-colors"
                            >
                                <X className="w-5 h-5 text-text-muted" />
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div className="p-5 space-y-4 max-h-[60vh] overflow-y-auto">
                            {editError && (
                                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                                    {editError}
                                </div>
                            )}

                            <div>
                                <label className="label">Title *</label>
                                <input
                                    type="text"
                                    value={editForm.title}
                                    onChange={(e) => setEditForm(f => ({ ...f, title: e.target.value }))}
                                    className="input"
                                    placeholder="Resource title"
                                />
                            </div>

                            <div>
                                <label className="label">Description</label>
                                <textarea
                                    value={editForm.description}
                                    onChange={(e) => setEditForm(f => ({ ...f, description: e.target.value }))}
                                    className="input min-h-[100px] resize-y"
                                    placeholder="Describe this resource..."
                                    rows={3}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="label">Course Code *</label>
                                    <input
                                        type="text"
                                        value={editForm.course_code}
                                        onChange={(e) => setEditForm(f => ({ ...f, course_code: e.target.value }))}
                                        className="input"
                                        placeholder="e.g., CS101"
                                    />
                                </div>
                                <div>
                                    <label className="label">Department</label>
                                    <input
                                        type="text"
                                        value={editForm.department}
                                        onChange={(e) => setEditForm(f => ({ ...f, department: e.target.value }))}
                                        className="input"
                                        placeholder="e.g., Computer Science"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="label">Semester</label>
                                    <input
                                        type="text"
                                        value={editForm.semester}
                                        onChange={(e) => setEditForm(f => ({ ...f, semester: e.target.value }))}
                                        className="input"
                                        placeholder="e.g., Fall 2026"
                                    />
                                </div>
                                <div>
                                    <label className="label">Visibility</label>
                                    <select
                                        value={editForm.visibility}
                                        onChange={(e) => setEditForm(f => ({ ...f, visibility: e.target.value }))}
                                        className="input"
                                    >
                                        <option value="public">Public</option>
                                        <option value="unlisted">Unlisted</option>
                                        <option value="private">Private</option>
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label className="label">Tags</label>
                                <input
                                    type="text"
                                    value={editForm.tags}
                                    onChange={(e) => setEditForm(f => ({ ...f, tags: e.target.value }))}
                                    className="input"
                                    placeholder="Comma-separated: notes, data-structures, exam"
                                />
                                <p className="text-text-muted text-xs mt-1">Separate tags with commas (max 10)</p>
                            </div>
                        </div>

                        {/* Modal Footer */}
                        <div className="flex items-center justify-end gap-3 p-5 border-t border-border-subtle">
                            <button
                                onClick={() => setShowEditModal(false)}
                                className="btn btn-secondary"
                                disabled={editSaving}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleEditSave}
                                disabled={editSaving || !editForm.title.trim() || !editForm.course_code.trim()}
                                className="btn btn-primary flex items-center gap-2"
                            >
                                {editSaving ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Saving...
                                    </>
                                ) : (
                                    <>
                                        <Save className="w-4 h-4" />
                                        Save Changes
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {showDeleteConfirm && (
                <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 animate-fade-in">
                    <div className="bg-background-secondary w-full max-w-sm rounded-xl shadow-2xl border border-border-subtle p-6 text-center">
                        <div className="w-12 h-12 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Trash2 className="w-6 h-6 text-red-500" />
                        </div>
                        <h3 className="text-lg font-bold text-text-primary mb-2">Delete Resource?</h3>
                        <p className="text-text-secondary text-sm mb-6">
                            This will permanently remove <strong>&quot;{resource?.title}&quot;</strong>. This action cannot be undone.
                        </p>
                        <div className="flex gap-3">
                            <button
                                onClick={() => setShowDeleteConfirm(false)}
                                className="btn btn-secondary flex-1"
                                disabled={deleting}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleDelete}
                                disabled={deleting}
                                className="btn bg-red-500 hover:bg-red-600 text-white flex-1 flex items-center justify-center gap-2"
                            >
                                {deleting ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Deleting...
                                    </>
                                ) : (
                                    <>
                                        <Trash2 className="w-4 h-4" />
                                        Delete
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
