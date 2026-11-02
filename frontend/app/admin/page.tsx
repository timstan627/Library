'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { TrendingUp, Info, ChevronRight } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, apiHelpers } from '@/lib/api'
import { SkeletonGrid } from '@/components/ui/Skeleton'
import { ModeratorAuthGate } from '@/components/AuthGate'
import FetchError from '@/components/ui/FetchError'

interface DashboardStats {
    total_users: number
    total_resources: number
    total_downloads: number
    total_storage_mb: number
    pending_reports: number
    pending_moderation: number
    new_users_7d: number
    new_resources_7d: number
}

function AdminDashboardContent() {
    const { user, isAuthenticated } = useAuth()

    const [stats, setStats] = useState<DashboardStats | null>(null)
    const [loading, setLoading] = useState(true)
    const [fetchError, setFetchError] = useState(false)

    useEffect(() => {
        if (isAuthenticated && user && (user.role === 'admin' || user.role === 'moderator')) {
            fetchStats()
        }
    }, [isAuthenticated, user])

    const fetchStats = async () => {
        try {
            // In a real app, we'd have a single dashboard stats endpoint
            // For now we combine a few
            const [dashRes, modStats] = await Promise.all([
                api.get('/admin/dashboard'),
                apiHelpers.getModerationStats()
            ])

            setStats({
                ...dashRes.data,
                pending_moderation: modStats.data.pending,
                total_storage_mb: dashRes.data.total_storage_bytes / (1024 * 1024)
            })
            setFetchError(false)
        } catch (error) {
            console.error('Failed to fetch admin statistics:', error)
            setFetchError(true)
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return (
            <div className="container-custom py-8">
                <div className="h-10 bg-background-tertiary rounded w-1/4 mb-8" />
                <SkeletonGrid count={4} />
                <div className="mt-12 h-64 bg-background-tertiary rounded" />
            </div>
        )
    }

    if (!user) {
        return null
    }

    // Only work that actually waits on a human gets a signal. The sidebar
    // is the wayfinding system; the dashboard does not re-list every section.
    const needsAttention = [
        { label: 'Moderation queue', href: '/admin/moderation', count: stats?.pending_moderation ?? 0 },
        { label: 'Open reports', href: '/admin/reports', count: stats?.pending_reports ?? 0 },
    ].filter(item => item.count > 0)

    return (
        <div className="container-custom py-8">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-primary">Dashboard</h1>
                    <p className="text-text-secondary">System-wide overview for the library</p>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-text-muted">Logged in as</span>
                    <span className="badge badge-primary">{user.role}</span>
                </div>
            </div>

            {fetchError && (
                <FetchError
                    message="Dashboard statistics could not be loaded. Counters may show placeholders."
                    onRetry={fetchStats}
                    className="mb-6"
                />
            )}

            {/* Needs attention — the only place a colored signal appears */}
            <div className="card p-4 mb-8">
                {needsAttention.length === 0 ? (
                    <p className="text-sm text-text-secondary px-2 py-1">
                        Nothing needs attention right now.
                    </p>
                ) : (
                    <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-6">
                        <span className="text-xs font-medium text-text-muted uppercase tracking-wide px-1">
                            Needs attention
                        </span>
                        {needsAttention.map(item => (
                            <Link
                                key={item.href}
                                href={item.href}
                                className="flex items-center gap-2.5 rounded-lg px-2 py-1.5 transition-colors hover:bg-background-tertiary"
                            >
                                <span className="w-2 h-2 rounded-full bg-warning-light shrink-0" aria-hidden="true" />
                                <span className="text-sm font-semibold text-text-primary tabular-nums">{item.count}</span>
                                <span className="text-sm text-text-secondary">{item.label}</span>
                                <ChevronRight className="w-4 h-4 text-text-muted" />
                            </Link>
                        ))}
                    </div>
                )}
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
                <div className="card p-6">
                    <p className="text-text-secondary text-xs font-medium mb-1">Total Users</p>
                    <p className="text-3xl font-bold font-display text-text-primary tabular-nums">{stats?.total_users.toLocaleString()}</p>
                    <p className="text-success-light text-xs mt-2 flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" />
                        +{stats?.new_users_7d} this week
                    </p>
                </div>
                <div className="card p-6">
                    <p className="text-text-secondary text-xs font-medium mb-1">Total Resources</p>
                    <p className="text-3xl font-bold font-display text-text-primary tabular-nums">{stats?.total_resources.toLocaleString()}</p>
                    <p className="text-success-light text-xs mt-2 flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" />
                        +{stats?.new_resources_7d} this week
                    </p>
                </div>
                <div className="card p-6">
                    <p className="text-text-secondary text-xs font-medium mb-1">Downloads</p>
                    <p className="text-3xl font-bold font-display text-text-primary tabular-nums">{stats?.total_downloads.toLocaleString()}</p>
                    <p className="text-text-muted text-xs mt-2">Aggregated across all files</p>
                </div>
                <div className="card p-6">
                    <p className="text-text-secondary text-xs font-medium mb-1">Storage Usage</p>
                    <p className="text-3xl font-bold font-display text-text-primary tabular-nums">
                        {(stats?.total_storage_mb || 0).toFixed(2)} MB
                    </p>
                    <p className="text-text-muted text-xs mt-2">Telegram storage footprint</p>
                </div>
            </div>

            {/* Service bindings — stated as facts; runtime health is not instrumented yet */}
            <div className="card p-6">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-accent-primary/10 rounded-lg flex items-center justify-center shrink-0">
                        <Info className="w-5 h-5 text-accent-primary" />
                    </div>
                    <div>
                        <h3 className="font-bold text-text-primary">Service bindings</h3>
                        <p className="text-xs text-text-muted">Runtime metrics are not instrumented yet.</p>
                    </div>
                </div>
                <ul className="text-sm text-text-secondary space-y-1.5">
                    <li><span className="font-semibold text-text-primary">File storage</span> — bound to a Telegram channel; no storage bill.</li>
                    <li><span className="font-semibold text-text-primary">Rate limiting, lockout, stats</span> — in-memory in one process; restart resets counters.</li>
                    <li><span className="font-semibold text-text-primary">Database</span> — SQLite, single file.</li>
                </ul>
            </div>
        </div>
    )
}

// CRITICAL-002: Wrap with ModeratorAuthGate to block render until auth resolved
export default function AdminDashboardPage() {
    return (
        <ModeratorAuthGate>
            <AdminDashboardContent />
        </ModeratorAuthGate>
    )
}
