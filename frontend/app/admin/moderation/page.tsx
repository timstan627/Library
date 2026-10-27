'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
    CheckCircle, XCircle, Eye, AlertCircle,
    ChevronRight, ChevronLeft, FileText, User
} from 'lucide-react'
import { apiHelpers } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { SkeletonTable } from '@/components/ui/Skeleton'
import FetchError from '@/components/ui/FetchError'
import Link from 'next/link'

interface PendingResource {
    id: string
    title: string
    slug: string
    course_code: string
    department_name?: string
    uploader_name?: string
    file_size: number
    created_at: string
}

interface HistoryItem {
    resource_id: string
    title: string
    status: string
    uploader_name?: string | null
    uploaded_at?: string | null
    moderated_at?: string | null
    rejection_reason?: string | null
}

const MODERATOR_TABS = [
    { key: 'pending' as const, label: 'Pending' },
    { key: 'history' as const, label: 'History' },
]

export default function ModerationPage() {
    const { user, isAuthenticated, isLoading } = useAuth()
    const router = useRouter()

    const [view, setView] = useState<'pending' | 'history'>('pending')
    const [resources, setResources] = useState<PendingResource[]>([])
    const [history, setHistory] = useState<HistoryItem[]>([])
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [stats, setStats] = useState({ pending: 0, approved: 0, rejected: 0 })
    const [fetchError, setFetchError] = useState<string | null>(null)

    // Moderation action state
    const [processingId, setProcessingId] = useState<string | null>(null)
    const [rejectionReason, setRejectionReason] = useState('')
    const [showRejectionModal, setShowRejectionModal] = useState<string | null>(null)

    useEffect(() => {
        if (!isLoading && (!isAuthenticated || (user?.role !== 'admin' && user?.role !== 'moderator'))) {
            router.push('/')
        }
    }, [isLoading, isAuthenticated, user, router])

    useEffect(() => {
        if (isAuthenticated && (user?.role === 'admin' || user?.role === 'moderator')) {
            if (view === 'pending') {
                fetchPending()
            } else {
                fetchHistory()
            }
            fetchStats()
        }
    }, [isAuthenticated, user, page, view])

    const fetchPending = async () => {
        setLoading(true)
        try {
            const response = await apiHelpers.getPendingModeration(page)
            setResources(response.data.results)
            setTotalPages(Math.ceil(response.data.total / 20))
            setFetchError(null)
        } catch (error) {
            console.error('Failed to fetch pending resources:', error)
            setFetchError('Failed to load the moderation queue. It may not actually be empty.')
        } finally {
            setLoading(false)
        }
    }

    const fetchHistory = async () => {
        setLoading(true)
        try {
            // Returns a bare list; page_size 200 (backend max) covers realistic history sizes.
            const response = await apiHelpers.getModerationHistory(1, 200)
            setHistory(response.data)
            setTotalPages(1)
            setFetchError(null)
        } catch (error) {
            console.error('Failed to fetch moderation history:', error)
            setFetchError('Failed to load moderation history.')
        } finally {
            setLoading(false)
        }
    }

    const fetchStats = async () => {
        try {
            const response = await apiHelpers.getModerationStats()
            setStats(response.data)
            setFetchError(null)
        } catch (error) {
            console.error('Failed to fetch stats:', error)
        }
    }

    const switchView = (next: 'pending' | 'history') => {
        if (next === view) return
        setView(next)
        setPage(1)
        setTotalPages(1)
        setFetchError(null)
    }

    const handleModerate = async (id: string, action: 'approve' | 'reject', reason?: string) => {
        setProcessingId(id)
        try {
            await apiHelpers.moderateResource(id, { action, rejection_reason: reason })
            setResources(resources.filter(r => r.id !== id))
            fetchStats()
            setShowRejectionModal(null)
            setRejectionReason('')
        } catch (error) {
            console.error(`Failed to ${action} resource:`, error)
            alert(`Failed to ${action} resource. Please try again.`)
        } finally {
            setProcessingId(null)
        }
    }

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    if (isLoading || !isAuthenticated) {
        return <div className="p-8"><SkeletonTable rows={5} columns={5} /></div>
    }

    return (
        <div className="container-custom py-8">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-3xl font-bold text-text-primary">Moderation Queue</h1>
                    <p className="text-text-secondary">Review and approve student uploads</p>
                </div>
                <div className="flex gap-4">
                    <div className="bg-background-tertiary px-4 py-2 rounded-lg border border-border-subtle">
                        <p className="text-xs text-text-muted font-medium">Pending</p>
                        <p className="text-xl font-bold text-warning-light tabular-nums">{stats.pending}</p>
                    </div>
                    <div className="bg-background-tertiary px-4 py-2 rounded-lg border border-border-subtle">
                        <p className="text-xs text-text-muted font-medium">Approved</p>
                        <p className="text-xl font-bold text-success-light tabular-nums">{stats.approved}</p>
                    </div>
                    <div className="bg-background-tertiary px-4 py-2 rounded-lg border border-border-subtle">
                        <p className="text-xs text-text-muted font-medium">Rejected</p>
                        <p className="text-xl font-bold text-danger-light tabular-nums">{stats.rejected}</p>
                    </div>
                </div>
            </div>

            {/* View tabs */}
            <div className="flex gap-2 p-1 bg-background-secondary rounded-lg border border-border-subtle w-fit mb-6">
                {MODERATOR_TABS.map((tab) => (
                    <button
                        key={tab.key}
                        type="button"
                        onClick={() => switchView(tab.key)}
                        aria-pressed={view === tab.key}
                        className={`px-4 py-1.5 rounded-md text-sm font-medium transition-[background-color,color] ${view === tab.key ? 'bg-accent-primary text-accent-ink' : 'text-text-secondary hover:text-text-primary'}`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {fetchError && (
                <FetchError
                    message={fetchError}
                    onRetry={() => { view === 'pending' ? fetchPending() : fetchHistory(); fetchStats() }}
                    className="mb-4"
                />
            )}

            {view === 'pending' ? (
                <div className="card shadow-md overflow-hidden border border-border-subtle">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-background-secondary border-b border-border-subtle">
                                <tr>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Resource</th>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Uploader</th>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Course</th>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Size</th>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Date</th>
                                    <th className="px-6 py-4 text-right text-xs font-medium text-text-muted">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border-subtle">
                                {loading ? (
                                    [...Array(5)].map((_, i) => (
                                        <tr key={i}>
                                            <td colSpan={6} className="px-6 py-4"><div className="h-6 bg-background-tertiary animate-pulse rounded" /></td>
                                        </tr>
                                    ))
                                ) : !resources || resources.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="px-6 py-12 text-center text-text-secondary">
                                            <div className="flex flex-col items-center">
                                                {fetchError ? (
                                                    <>
                                                        <AlertCircle className="w-12 h-12 text-danger/50 mb-3" />
                                                        <p className="text-lg font-medium">Could not load the queue</p>
                                                        <p className="text-sm">Check your connection, then retry above.</p>
                                                    </>
                                                ) : (
                                                    <>
                                                        <CheckCircle className="w-12 h-12 text-green-500/50 mb-3" />
                                                        <p className="text-lg font-medium">Clear Queue!</p>
                                                        <p className="text-sm">No pending resources to moderate.</p>
                                                    </>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ) : (
                                    resources.map((res) => (
                                        <tr key={res.id} className="hover:bg-background-tertiary transition-colors">
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-3">
                                                    <FileText className="w-5 h-5 text-accent-primary" />
                                                    <span className="font-medium text-text-primary text-sm truncate max-w-[200px]" title={res.title}>
                                                        {res.title}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2 text-sm text-text-secondary">
                                                    <User className="w-4 h-4" />
                                                    <span>{res.uploader_name || 'Anonymous'}</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className="badge badge-secondary text-xs">{res.course_code}</span>
                                            </td>
                                            <td className="px-6 py-4 text-xs text-text-secondary tabular-nums">
                                                {formatFileSize(res.file_size)}
                                            </td>
                                            <td className="px-6 py-4 text-xs text-text-secondary">
                                                {new Date(res.created_at).toLocaleDateString()}
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <div className="flex justify-end gap-2">
                                                    <Link
                                                        href={`/resources/${res.slug}`}
                                                        target="_blank"
                                                        className="p-2 text-text-muted hover:text-accent-primary transition-colors"
                                                        title="Preview"
                                                    >
                                                        <Eye className="w-5 h-5" />
                                                    </Link>
                                                    <button
                                                        onClick={() => handleModerate(res.id, 'approve')}
                                                        disabled={processingId === res.id}
                                                        className="p-2 text-success-light hover:bg-success/10 rounded-md transition-[background-color,transform] active:scale-90"
                                                        title="Approve"
                                                    >
                                                        <CheckCircle className={`w-5 h-5 ${processingId === res.id && 'animate-spin'}`} />
                                                    </button>
                                                    <button
                                                        onClick={() => setShowRejectionModal(res.id)}
                                                        disabled={processingId === res.id}
                                                        className="p-2 text-danger-light hover:bg-danger/10 rounded-md transition-[background-color,transform] active:scale-90"
                                                        title="Reject"
                                                    >
                                                        <XCircle className="w-5 h-5" />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="px-6 py-4 bg-background-secondary border-t border-border-subtle flex items-center justify-between">
                            <p className="text-sm text-text-secondary">
                                Page {page} of {totalPages}
                            </p>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setPage(p => Math.max(1, p - 1))}
                                    disabled={page === 1}
                                    className="btn btn-secondary p-2 disabled:opacity-50"
                                >
                                    <ChevronLeft className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                    disabled={page === totalPages}
                                    className="btn btn-secondary p-2 disabled:opacity-50"
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            ) : (
                <div className="card shadow-md overflow-hidden border border-border-subtle">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-background-secondary border-b border-border-subtle">
                                <tr>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Resource</th>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Status</th>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Uploader</th>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Uploaded</th>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Moderated</th>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Rejection Reason</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border-subtle">
                                {loading ? (
                                    [...Array(5)].map((_, i) => (
                                        <tr key={i}>
                                            <td colSpan={6} className="px-6 py-4"><div className="h-6 bg-background-tertiary animate-pulse rounded" /></td>
                                        </tr>
                                    ))
                                ) : history.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="px-6 py-12 text-center text-text-secondary">
                                            <div className="flex flex-col items-center">
                                                <FileText className="w-12 h-12 text-text-muted/40 mb-3" />
                                                <p className="text-lg font-medium">No moderation history yet</p>
                                                <p className="text-sm">Approved and rejected resources will appear here.</p>
                                            </div>
                                        </td>
                                    </tr>
                                ) : (
                                    history.map((item) => (
                                        <tr key={item.resource_id} className="hover:bg-background-tertiary transition-colors">
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-3">
                                                    <FileText className="w-5 h-5 text-accent-primary" />
                                                    <span className="font-medium text-text-primary text-sm truncate max-w-[240px]" title={item.title}>
                                                        {item.title}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`badge text-xs ${item.status === 'approved' ? 'badge-success' : 'badge-danger'}`}>
                                                    {item.status === 'approved' ? 'Approved' : 'Rejected'}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2 text-sm text-text-secondary">
                                                    <User className="w-4 h-4" />
                                                    <span>{item.uploader_name || 'Anonymous'}</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-xs text-text-secondary">
                                                {item.uploaded_at ? new Date(item.uploaded_at).toLocaleDateString() : '—'}
                                            </td>
                                            <td className="px-6 py-4 text-xs text-text-secondary">
                                                {item.moderated_at ? new Date(item.moderated_at).toLocaleDateString() : '—'}
                                            </td>
                                            <td className="px-6 py-4 text-xs text-text-secondary max-w-[240px] truncate" title={item.rejection_reason || undefined}>
                                                {item.rejection_reason || '—'}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Rejection Modal */}
            {showRejectionModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="card w-full max-w-md p-6 animate-scale-in shadow-2xl">
                        <div className="flex items-center gap-3 mb-4 text-red-600 text-lg font-bold">
                            <AlertCircle className="w-6 h-6" />
                            <h2>Reject Resource</h2>
                        </div>
                        <p className="text-text-secondary text-sm mb-4">
                            Please provide a reason for rejecting this resource. The uploader will see this reason.
                        </p>
                        <textarea
                            value={rejectionReason}
                            onChange={(e) => setRejectionReason(e.target.value)}
                            placeholder="e.g., Poor quality scan, incorrect course code, or inappropriate content."
                            className="input min-h-[120px] mb-6 resize-none"
                            autoFocus
                        />
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => {
                                    setShowRejectionModal(null)
                                    setRejectionReason('')
                                }}
                                className="btn btn-ghost"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => handleModerate(showRejectionModal, 'reject', rejectionReason)}
                                disabled={!rejectionReason.trim() || processingId === showRejectionModal}
                                className="btn btn-primary bg-red-600 hover:bg-red-700 text-white"
                            >
                                {processingId === showRejectionModal ? 'Processing...' : 'Confirm Rejection'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
