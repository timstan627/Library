'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
    LayoutDashboard, Users, FileText, Flag, BarChart3, Settings,
    TrendingUp, Download, Eye, HardDrive, AlertTriangle, CheckCircle,
    XCircle, Search, Shield, BookOpen, Layers, Activity, ChevronRight
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, apiHelpers } from '@/lib/api'
import { SkeletonGrid } from '@/components/ui/Skeleton'
import { ModeratorAuthGate } from '@/components/AuthGate'

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
        } catch (error) {
            console.error('Failed to fetch admin statistics:', error)
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

    const adminSections = [
        {
            title: 'Resources',
            desc: 'Manage all uploads',
            icon: FileText,
            href: '/admin/resources',
            color: 'text-accent-primary',
            bg: 'bg-accent-primary/10'
        },
        {
            title: 'Moderation',
            desc: 'Review pending uploads',
            icon: Shield,
            count: stats?.pending_moderation || 0,
            href: '/admin/moderation',
            color: 'text-yellow-500',
            bg: 'bg-yellow-500/10'
        },
        {
            title: 'Departments',
            desc: 'Manage faculty units',
            icon: Layers,
            href: '/admin/departments',
            color: 'text-blue-500',
            bg: 'bg-blue-500/10'
        },
        {
            title: 'Courses',
            desc: 'Manage study programs',
            icon: BookOpen,
            href: '/admin/courses',
            color: 'text-purple-500',
            bg: 'bg-purple-500/10'
        },
        {
            title: 'Trusted Users',
            desc: 'Manage contributors',
            icon: Users,
            href: '/admin/users',
            color: 'text-green-500',
            bg: 'bg-green-500/10'
        },
        {
            title: 'Audit Logs',
            desc: 'Track admin actions',
            icon: Activity,
            href: '/admin/audit',
            color: 'text-orange-500',
            bg: 'bg-orange-500/10'
        }
    ]

    return (
        <div className="container-custom py-8">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-primary">Admin Control Center</h1>
                    <p className="text-text-secondary">System-wide monitoring and management</p>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-text-muted">Logged in as</span>
                    <span className="badge badge-primary">{user.role}</span>
                </div>
            </div>

            {/* Quick Stats Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
                <div className="card p-6 border-l-4 border-blue-500">
                    <p className="text-text-secondary text-xs font-medium mb-1">Total Users</p>
                    <p className="text-3xl font-bold font-display text-text-primary tabular-nums">{stats?.total_users.toLocaleString()}</p>
                    <p className="text-green-500 text-xs mt-2 flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" />
                        +{stats?.new_users_7d} this week
                    </p>
                </div>
                <div className="card p-6 border-l-4 border-purple-500">
                    <p className="text-text-secondary text-xs font-medium mb-1">Total Resources</p>
                    <p className="text-3xl font-bold font-display text-text-primary tabular-nums">{stats?.total_resources.toLocaleString()}</p>
                    <p className="text-green-500 text-xs mt-2 flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" />
                        +{stats?.new_resources_7d} this week
                    </p>
                </div>
                <div className="card p-6 border-l-4 border-green-500">
                    <p className="text-text-secondary text-xs font-medium mb-1">Downloads</p>
                    <p className="text-3xl font-bold font-display text-text-primary tabular-nums">{stats?.total_downloads.toLocaleString()}</p>
                    <p className="text-text-muted text-xs mt-2">Aggregated across all files</p>
                </div>
                <div className="card p-6 border-l-4 border-orange-500">
                    <p className="text-text-secondary text-xs font-medium mb-1">Storage Usage</p>
                    <p className="text-3xl font-bold font-display text-text-primary tabular-nums">
                        {(stats?.total_storage_mb || 0).toFixed(2)} MB
                    </p>
                    <p className="text-text-muted text-xs mt-2">Cloud storage footprint</p>
                </div>
            </div>

            {/* Management Hub */}
            <h2 className="text-xl font-bold text-text-primary mb-6 flex items-center gap-2">
                <Settings className="w-5 h-5 text-accent-primary" />
                Management Hub
            </h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {adminSections.map((section) => (
                    <Link
                        key={section.title}
                        href={section.href}
                        className="group card card-interactive p-6 relative overflow-hidden"
                    >
                        <div className="flex items-start justify-between relative z-10">
                            <div className={`p-3 rounded-xl ${section.bg} ${section.color} mb-4`}>
                                <section.icon className="w-6 h-6" />
                            </div>
                            {section.count !== undefined && section.count > 0 && (
                                <span className="bg-danger text-accent-ink text-xs font-semibold px-2 py-0.5 rounded-full tabular-nums">
                                    {section.count}
                                </span>
                            )}
                        </div>
                        <h3 className="text-lg font-bold text-text-primary">
                            {section.title}
                        </h3>
                        <p className="text-sm text-text-secondary mt-1">
                            {section.desc}
                        </p>
                        <div className="mt-4 flex items-center gap-1.5 text-xs font-semibold text-accent-primary">
                            Manage Section
                            <ChevronRight className="w-4 h-4 transition-transform duration-200 ease-expo group-hover:translate-x-1" />
                        </div>

                        {/* Decorative background icon */}
                        <section.icon className="absolute -right-4 -bottom-4 w-24 h-24 opacity-[0.03]" />
                    </Link>
                ))}
            </div>

            {/* Platform Status */}
            <div className="mt-12 p-8 bg-background-secondary rounded-2xl border border-border-subtle relative overflow-hidden">
                <div className="flex flex-col md:flex-row items-center justify-between gap-8 relative z-10">
                    <div className="flex items-center gap-6">
                        <div className="w-16 h-16 bg-success/20 rounded-full flex items-center justify-center">
                            <Activity className="w-8 h-8 text-success-light" />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-text-primary">System Health: Operational</h3>
                            <p className="text-text-secondary">All services are running normally. No active issues detected.</p>
                        </div>
                    </div>
                    <div className="flex flex-wrap gap-4">
                        <div className="flex items-center gap-2 bg-background p-3 rounded-lg border border-border-subtle">
                            <div className="w-2 h-2 rounded-full bg-success-light" />
                            <span className="text-xs font-medium text-text-secondary">Telegram API</span>
                        </div>
                        <div className="flex items-center gap-2 bg-background p-3 rounded-lg border border-border-subtle">
                            <div className="w-2 h-2 rounded-full bg-success-light" />
                            <span className="text-xs font-medium text-text-secondary">In-Memory Cache</span>
                        </div>
                        <div className="flex items-center gap-2 bg-background p-3 rounded-lg border border-border-subtle">
                            <div className="w-2 h-2 rounded-full bg-success-light" />
                            <span className="text-xs font-medium text-text-secondary">SQLite DB</span>
                        </div>
                    </div>
                </div>
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
