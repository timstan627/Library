'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
    Shield, ShieldCheck, User, Search, AlertCircle,
    Star, ThumbsUp, Trash2, CheckCircle, Info
} from 'lucide-react'
import { apiHelpers, api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { SkeletonTable } from '@/components/ui/Skeleton'

interface TrustedUser {
    id: string
    display_name?: string
    email: string
    role: string
    is_trusted: boolean
    promoted_at?: string
    promoted_by_name?: string
    upload_count: number
    approved_count: number
}

export default function UserPromotionPage() {
    const { user: currentUser, isAuthenticated, isLoading } = useAuth()
    const router = useRouter()

    const [users, setUsers] = useState<TrustedUser[]>([])
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')
    const [allUsers, setAllUsers] = useState<any[]>([])
    const [activeTab, setActiveTab] = useState<'trusted' | 'search'>('trusted')

    useEffect(() => {
        if (!isLoading && (!isAuthenticated || currentUser?.role !== 'admin')) {
            router.push('/')
        }
    }, [isLoading, isAuthenticated, currentUser, router])

    useEffect(() => {
        if (isAuthenticated && currentUser?.role === 'admin') {
            fetchTrusted()
        }
    }, [isAuthenticated, currentUser])

    const fetchTrusted = async () => {
        setLoading(true)
        try {
            const response = await apiHelpers.getTrustedUsers()
            setUsers(response.data)
        } catch (error) {
            console.error('Failed to fetch trusted users:', error)
        } finally {
            setLoading(false)
        }
    }

    const searchUsers = async (query: string) => {
        if (!query.trim()) return
        setLoading(true)
        try {
            const response = await api.get('/admin/users', { params: { q: query } })
            setAllUsers(response.data.results)
        } catch (error) {
            console.error('Failed to search users:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleToggleTrust = async (userId: string, currentStatus: boolean) => {
        const newStatus = !currentStatus
        if (!confirm(`Are you sure you want to ${newStatus ? 'promote to Trusted' : 'remove Trusted status'}?`)) return

        try {
            await apiHelpers.promoteUser(userId, { is_trusted: newStatus })
            if (activeTab === 'trusted') {
                fetchTrusted()
            } else {
                setAllUsers(allUsers.map(u => u.id === userId ? { ...u, is_trusted: newStatus } : u))
            }
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Promotion failed')
        }
    }

    if (isLoading || !isAuthenticated) {
        return <div className="p-8"><SkeletonTable rows={5} columns={4} /></div>
    }

    return (
        <div className="container-custom py-8">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-primary">Trusted Contributors</h1>
                    <p className="text-text-secondary">Manage users who can bypass moderation</p>
                </div>
                <div className="flex gap-2 p-1 bg-background-secondary rounded-lg border border-border-subtle">
                    <button
                        onClick={() => setActiveTab('trusted')}
                        className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'trusted' ? 'bg-accent-primary text-white shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
                    >
                        Trusted List
                    </button>
                    <button
                        onClick={() => setActiveTab('search')}
                        className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'search' ? 'bg-accent-primary text-white shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
                    >
                        Search All
                    </button>
                </div>
            </div>

            {activeTab === 'search' && (
                <div className="card mb-6 p-4">
                    <form onSubmit={(e) => { e.preventDefault(); searchUsers(searchQuery); }} className="relative flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                            <input
                                type="text"
                                placeholder="Enter email or display name..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="input pl-10"
                            />
                        </div>
                        <button type="submit" className="btn btn-primary px-6">Search</button>
                    </form>
                </div>
            )}

            <div className="card shadow-md overflow-hidden border border-border-subtle">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-background-secondary border-b border-border-subtle">
                            <tr>
                                <th className="px-6 py-4 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">User</th>
                                <th className="px-6 py-4 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Stats</th>
                                <th className="px-6 py-4 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Status</th>
                                <th className="px-6 py-4 text-right text-xs font-semibold text-text-muted uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border-subtle">
                            {loading ? (
                                [...Array(3)].map((_, i) => (
                                    <tr key={i}><td colSpan={4} className="px-6 py-4"><div className="h-6 bg-background-tertiary animate-pulse rounded" /></td></tr>
                                ))
                            ) : (activeTab === 'trusted' ? users : allUsers).length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="px-6 py-12 text-center text-text-secondary">
                                        {activeTab === 'trusted' ? 'No trusted contributors yet.' : 'Search for users to promote.'}
                                    </td>
                                </tr>
                            ) : (
                                (activeTab === 'trusted' ? users : allUsers).map((u: any) => (
                                    <tr key={u.id} className="hover:bg-background-tertiary transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 bg-accent-primary/10 rounded-full flex items-center justify-center">
                                                    <User className="w-5 h-5 text-accent-primary" />
                                                </div>
                                                <div className="flex flex-col">
                                                    <span className="font-bold text-text-primary text-sm">{u.display_name || 'No Name'}</span>
                                                    <span className="text-xs text-text-muted">{u.email}</span>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-col gap-1">
                                                <div className="flex items-center gap-2 text-xs">
                                                    <Star className="w-3 h-3 text-yellow-500" />
                                                    <span className="text-text-secondary">{u.upload_count || 0} Uploads</span>
                                                </div>
                                                <div className="flex items-center gap-2 text-xs">
                                                    <ThumbsUp className="w-3 h-3 text-green-500" />
                                                    <span className="text-text-secondary">{u.approved_count || 0} Approved</span>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            {u.is_trusted ? (
                                                <div className="flex items-center gap-1.5 px-2.5 py-1 bg-green-500/10 border border-green-500/20 rounded-full w-fit">
                                                    <ShieldCheck className="w-3.5 h-3.5 text-green-600" />
                                                    <span className="text-[10px] font-bold text-green-600 uppercase">Trusted</span>
                                                </div>
                                            ) : (
                                                <div className="flex items-center gap-1.5 px-2.5 py-1 bg-background-tertiary border border-border-subtle rounded-full w-fit">
                                                    <Shield className="w-3.5 h-3.5 text-text-muted" />
                                                    <span className="text-[10px] font-bold text-text-muted uppercase">Regular</span>
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            {u.role !== 'admin' && (
                                                <button
                                                    onClick={() => handleToggleTrust(u.id, u.is_trusted)}
                                                    className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all shadow-sm active:scale-95 ${u.is_trusted ? 'bg-red-500/10 text-red-600 border border-red-500/20 hover:bg-red-500 hover:text-white' : 'bg-green-500/10 text-green-600 border border-green-500/20 hover:bg-green-500 hover:text-white'}`}
                                                >
                                                    {u.is_trusted ? 'Revoke Trust' : 'Mark Trusted'}
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="mt-8 p-6 bg-blue-500/5 border border-blue-500/20 rounded-xl relative overflow-hidden">
                <div className="relative z-10 flex gap-4">
                    <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center shrink-0">
                        <Info className="w-6 h-6 text-blue-600" />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-text-primary mb-1">What is a Trusted Contributor?</h3>
                        <p className="text-sm text-text-secondary leading-relaxed max-w-2xl">
                            Trusted contributors are users who have established a history of providing high-quality study materials.
                            <strong> All their uploads will bypass the moderation queue and be published immediately.</strong>
                            This status is typically granted to students who maintain a high approval-to-upload ratio.
                        </p>
                    </div>
                </div>
                <div className="absolute -right-8 -bottom-8 opacity-5">
                    <Shield className="w-48 h-48" />
                </div>
            </div>
        </div>
    )
}
