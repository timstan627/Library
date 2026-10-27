'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
    Activity, Clock, User, Target, Database,
    Search, Filter, ChevronRight, ChevronLeft,
    Shield, CheckCircle, XCircle, AlertTriangle
} from 'lucide-react'
import { apiHelpers } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { SkeletonTable } from '@/components/ui/Skeleton'

interface AuditEntry {
    id: string
    action: string
    actor_name: string
    target_type: string
    target_id: string
    details: any
    timestamp: string
}

export default function AuditLogsPage() {
    const { user, isAuthenticated, isLoading } = useAuth()
    const router = useRouter()

    const [logs, setLogs] = useState<AuditEntry[]>([])
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)

    useEffect(() => {
        if (!isLoading && (!isAuthenticated || user?.role !== 'admin')) {
            router.push('/')
        }
    }, [isLoading, isAuthenticated, user, router])

    useEffect(() => {
        if (isAuthenticated && user?.role === 'admin') {
            fetchLogs()
        }
    }, [isAuthenticated, user, page])

    const fetchLogs = async () => {
        setLoading(true)
        try {
            const response = await apiHelpers.getAuditLogs(page)
            setLogs(response.data.results)
            setTotalPages(Math.ceil(response.data.total / 50))
        } catch (error) {
            console.error('Failed to fetch audit logs:', error)
        } finally {
            setLoading(false)
        }
    }

    const getActionIcon = (action: string) => {
        if (action.includes('approve')) return <CheckCircle className="w-4 h-4 text-green-500" />
        if (action.includes('reject')) return <XCircle className="w-4 h-4 text-red-500" />
        if (action.includes('promote')) return <Shield className="w-4 h-4 text-blue-500" />
        if (action.includes('delete')) return <AlertTriangle className="w-4 h-4 text-orange-500" />
        return <Activity className="w-4 h-4 text-text-muted" />
    }

    const formatAction = (action: string) => {
        return action.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
    }

    if (isLoading || !isAuthenticated) {
        return <div className="p-8"><SkeletonTable rows={10} columns={5} /></div>
    }

    return (
        <div className="container-custom py-8">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-text-primary">Audit Trail</h1>
                <p className="text-text-secondary">Historical record of all administrative actions</p>
            </div>

            <div className="card shadow-md overflow-hidden border border-border-subtle">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-background-secondary border-b border-border-subtle">
                            <tr>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Timestamp</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Action</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Admin</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Target</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Details</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border-subtle text-xs">
                            {loading ? (
                                [...Array(10)].map((_, i) => (
                                    <tr key={i}><td colSpan={5} className="px-6 py-4"><div className="h-4 bg-background-tertiary animate-pulse rounded" /></td></tr>
                                ))
                            ) : logs.length === 0 ? (
                                <tr><td colSpan={5} className="px-6 py-12 text-center text-text-secondary">No audit logs found.</td></tr>
                            ) : (
                                logs.map((log) => (
                                    <tr key={log.id} className="hover:bg-background-tertiary transition-colors">
                                        <td className="px-6 py-3 whitespace-nowrap text-text-muted">
                                            {new Date(log.timestamp).toLocaleString(undefined, {
                                                year: 'numeric',
                                                month: 'short',
                                                day: 'numeric',
                                                hour: '2-digit',
                                                minute: '2-digit',
                                                second: '2-digit'
                                            })}
                                        </td>
                                        <td className="px-6 py-3">
                                            <div className="flex items-center gap-2">
                                                {getActionIcon(log.action)}
                                                <span className="font-bold text-text-primary font-sans text-xs">
                                                    {formatAction(log.action)}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-3">
                                            <div className="flex items-center gap-1.5 font-sans">
                                                <User className="w-3.5 h-3.5 text-blue-500" />
                                                <span className="text-text-primary">{log.actor_name}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-3">
                                            <div className="flex items-center gap-1.5">
                                                <Target className="w-3.5 h-3.5 text-text-muted" />
                                                <span className="text-text-muted capitalize">[{log.target_type}]</span>
                                                <span className="text-text-secondary truncate max-w-[100px]">{log.target_id}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-3">
                                            <div className="max-w-md overflow-hidden text-ellipsis whitespace-nowrap text-text-muted hover:whitespace-normal hover:overflow-visible hover:bg-background-secondary p-1 rounded">
                                                {JSON.stringify(log.details)}
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {totalPages > 1 && (
                    <div className="px-6 py-4 bg-background-secondary border-t border-border-subtle flex items-center justify-between">
                        <p className="text-sm text-text-secondary">Page {page} of {totalPages}</p>
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
        </div>
    )
}
