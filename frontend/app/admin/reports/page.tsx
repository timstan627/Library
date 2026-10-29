'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
    Flag, CheckCircle, XCircle, FileText, User, AlertCircle, ChevronLeft, ChevronRight
} from 'lucide-react'
import { apiHelpers } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { SkeletonTable } from '@/components/ui/Skeleton'
import FetchError from '@/components/ui/FetchError'

interface ReportRow {
    id: string
    status: string
    reason: string
    details?: string
    resolution_note?: string
    created_at: string
    resolved_by_name?: string
    reporter_name?: string
    reporter_email?: string
    resource_id: string
    resource_title?: string
    resource_slug?: string
}

const TABS = [
    { key: 'pending', label: 'Pending' },
    { key: 'resolved', label: 'Resolved' },
    { key: 'dismissed', label: 'Dismissed' },
    { key: '', label: 'All' },
] as const

export default function AdminReportsPage() {
    const { user, isAuthenticated, isLoading } = useAuth()
    const router = useRouter()

    const [reports, setReports] = useState<ReportRow[]>([])
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const [statusFilter, setStatusFilter] = useState<'pending' | 'resolved' | 'dismissed' | ''>('pending')
    const [fetchError, setFetchError] = useState<string | null>(null)

    // Action modal state (mirrors the moderation rejection modal)
    const [actionModal, setActionModal] = useState<{ report: ReportRow; action: 'resolved' | 'dismissed' } | null>(null)
    const [note, setNote] = useState('')
    const [processing, setProcessing] = useState(false)
    const [actionError, setActionError] = useState('')

    useEffect(() => {
        if (!isLoading && (!isAuthenticated || user?.role !== 'admin')) {
            router.push('/')
        }
    }, [isLoading, isAuthenticated, user, router])

    useEffect(() => {
        if (isAuthenticated && user?.role === 'admin') {
            fetchReports()
        }
    }, [isAuthenticated, user, page, statusFilter])

    const fetchReports = async () => {
        setLoading(true)
        try {
            const response = await apiHelpers.getReportsAdmin(statusFilter || undefined, page)
            setReports(response.data.results)
            setTotal(response.data.total)
            setTotalPages(Math.max(1, Math.ceil(response.data.total / 20)))
            setFetchError(null)
        } catch (error) {
            console.error('Failed to fetch reports:', error)
            setFetchError('Failed to load reports. The queue may not actually be empty.')
        } finally {
            setLoading(false)
        }
    }

    const submitAction = async () => {
        if (!actionModal) return
        setProcessing(true)
        setActionError('')
        try {
            await apiHelpers.resolveReport(actionModal.report.id, {
                action: actionModal.action,
                resolution_note: note.trim() || undefined,
            })
            setActionModal(null)
            setNote('')
            fetchReports()
        } catch (err: any) {
            setActionError(err.response?.data?.detail || 'Failed to update the report')
        } finally {
            setProcessing(false)
        }
    }

    const statusBadge = (status: string) => {
        if (status === 'pending') {
            return (
                <span className="flex items-center gap-1.5 px-2.5 py-1 bg-warning/10 border border-warning/20 rounded-full w-fit">
                    <Flag className="w-3.5 h-3.5 text-warning-light" />
                    <span className="text-[11px] font-semibold text-warning-light">Pending</span>
                </span>
            )
        }
        if (status === 'resolved') {
            return (
                <span className="flex items-center gap-1.5 px-2.5 py-1 bg-success/10 border border-success/20 rounded-full w-fit">
                    <CheckCircle className="w-3.5 h-3.5 text-success-light" />
                    <span className="text-[11px] font-semibold text-success-light">Resolved</span>
                </span>
            )
        }
        return (
            <span className="flex items-center gap-1.5 px-2.5 py-1 bg-background-tertiary border border-border-subtle rounded-full w-fit">
                <XCircle className="w-3.5 h-3.5 text-text-muted" />
                <span className="text-[11px] font-semibold text-text-muted">Dismissed</span>
            </span>
        )
    }

    if (isLoading || !isAuthenticated) {
        return <div className="p-8"><SkeletonTable rows={5} columns={5} /></div>
    }

    return (
        <div className="container-custom py-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-primary">Content Reports</h1>
                    <p className="text-text-secondary">Review and resolve reports filed by users</p>
                </div>
                <div className="flex gap-2 p-1 bg-background-secondary rounded-lg border border-border-subtle w-fit">
                    {TABS.map(tab => (
                        <button
                            key={tab.key}
                            onClick={() => { setStatusFilter(tab.key); setPage(1) }}
                            aria-pressed={statusFilter === tab.key}
                            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-[background-color,color] ${statusFilter === tab.key ? 'bg-accent-primary text-accent-ink' : 'text-text-secondary hover:text-text-primary'}`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {fetchError && (
                <FetchError message={fetchError} onRetry={fetchReports} className="mb-4" />
            )}

            <div className="card shadow-md overflow-hidden border border-border-subtle">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        {(loading || reports.length > 0) && (
                        <thead className="bg-background-secondary border-b border-border-subtle">
                            <tr>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Resource</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Reporter</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Reason</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Filed</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Status</th>
                                <th className="px-6 py-4 text-right text-xs font-medium text-text-muted">Actions</th>
                            </tr>
                        </thead>
                        )}
                        <tbody className="divide-y divide-border-subtle">
                            {loading ? (
                                [...Array(3)].map((_, i) => (
                                    <tr key={i}><td colSpan={6} className="px-6 py-4"><div className="h-6 bg-background-tertiary animate-pulse rounded" /></td></tr>
                                ))
                            ) : reports.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center text-text-secondary">
                                        <div className="flex flex-col items-center">
                                            {fetchError ? (
                                                <>
                                                    <AlertCircle className="w-12 h-12 text-danger/50 mb-3" />
                                                    <p className="text-lg font-medium">Could not load reports</p>
                                                    <p className="text-sm">Check your connection, then retry above.</p>
                                                </>
                                            ) : statusFilter === 'pending' ? (
                                                <>
                                                    <CheckCircle className="w-12 h-12 text-green-500/50 mb-3" />
                                                    <p className="text-lg font-medium">No pending reports</p>
                                                    <p className="text-sm">Nothing needs attention right now.</p>
                                                </>
                                            ) : (
                                                <>
                                                    <Flag className="w-12 h-12 text-text-muted/40 mb-3" />
                                                    <p className="text-lg font-medium">{statusFilter ? `No ${statusFilter} reports` : 'No reports'}</p>
                                                    <p className="text-sm">Reports filed by users will appear here.</p>
                                                </>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                reports.map((rep) => (
                                    <tr key={rep.id} className="hover:bg-background-tertiary transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-3">
                                                <FileText className="w-5 h-5 text-accent-primary shrink-0" />
                                                <div className="min-w-0">
                                                    {rep.resource_slug ? (
                                                        <Link
                                                            href={`/resources/${rep.resource_slug}`}
                                                            target="_blank"
                                                            className="font-medium text-text-primary text-sm hover:text-accent-primary truncate block max-w-[220px]"
                                                            title={rep.resource_title}
                                                        >
                                                            {rep.resource_title || 'Deleted resource'}
                                                        </Link>
                                                    ) : (
                                                        <span className="font-medium text-text-primary text-sm">{rep.resource_title || 'Unknown resource'}</span>
                                                    )}
                                                    {rep.status !== 'pending' && rep.resolution_note && (
                                                        <span className="text-xs text-text-muted block truncate max-w-[220px]" title={rep.resolution_note}>
                                                            Note: {rep.resolution_note}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2 text-sm text-text-secondary">
                                                <User className="w-4 h-4 shrink-0" />
                                                <span className="truncate max-w-[140px]" title={rep.reporter_email}>
                                                    {rep.reporter_name || 'Anonymous'}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 max-w-[220px]">
                                            <p className="text-sm text-text-primary font-medium">{rep.reason}</p>
                                            {rep.details && (
                                                <p className="text-xs text-text-secondary truncate max-w-[220px]" title={rep.details}>
                                                    {rep.details}
                                                </p>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-xs text-text-secondary whitespace-nowrap">
                                            {new Date(rep.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4">{statusBadge(rep.status)}</td>
                                        <td className="px-6 py-4 text-right">
                                            {rep.status === 'pending' ? (
                                                <div className="flex justify-end gap-2">
                                                    <button
                                                        onClick={() => { setActionModal({ report: rep, action: 'resolved' }); setNote('') }}
                                                        className="btn btn-secondary px-3 py-1.5 text-xs"
                                                    >
                                                        Resolve
                                                    </button>
                                                    <button
                                                        onClick={() => { setActionModal({ report: rep, action: 'dismissed' }); setNote('') }}
                                                        className="btn btn-ghost px-3 py-1.5 text-xs text-text-secondary"
                                                    >
                                                        Dismiss
                                                    </button>
                                                </div>
                                            ) : (
                                                <span className="text-xs text-text-muted">
                                                    {rep.resolved_by_name ? `by ${rep.resolved_by_name}` : '—'}
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {totalPages > 1 && (
                    <div className="px-6 py-4 bg-background-secondary border-t border-border-subtle flex items-center justify-between">
                        <p className="text-sm text-text-secondary">Page {page} of {totalPages} · {total} total</p>
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

            {/* Resolve / Dismiss Modal */}
            {actionModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="card w-full max-w-md p-6 animate-scale-in shadow-2xl" role="dialog" aria-modal="true">
                        <div className={`flex items-center gap-3 mb-4 text-lg font-bold ${actionModal.action === 'resolved' ? 'text-success-light' : 'text-text-primary'}`}>
                            {actionModal.action === 'resolved'
                                ? <CheckCircle className="w-6 h-6" />
                                : <XCircle className="w-6 h-6" />}
                            <h2>{actionModal.action === 'resolved' ? 'Resolve report' : 'Dismiss report'}</h2>
                        </div>
                        <p className="text-text-secondary text-sm mb-4">
                            {actionModal.action === 'resolved'
                                ? `Mark the report on "${actionModal.report.resource_title}" as handled. An optional note is stored in the audit trail.`
                                : `Dismiss the report on "${actionModal.report.resource_title}" if no action is needed. An optional note is stored in the audit trail.`}
                        </p>
                        {actionError && (
                            <p role="alert" className="text-sm text-danger-light mb-4">{actionError}</p>
                        )}
                        <textarea
                            value={note}
                            onChange={(e) => setNote(e.target.value)}
                            placeholder="Optional note, e.g. 'Contacted uploader, file removed.'"
                            className="input min-h-[110px] mb-6 resize-none"
                            autoFocus
                        />
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => { setActionModal(null); setNote(''); setActionError('') }}
                                className="btn btn-ghost"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={submitAction}
                                disabled={processing}
                                className={`btn ${actionModal.action === 'resolved' ? 'btn-primary' : 'btn-secondary'} flex items-center gap-2`}
                            >
                                {actionModal.action === 'resolved' ? 'Resolve report' : 'Dismiss report'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
