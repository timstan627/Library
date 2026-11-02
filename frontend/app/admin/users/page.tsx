'use client'

import { useState, useEffect } from 'react'
import {
    ToggleLeft, ToggleRight, Shield, ShieldCheck, User, Search, Star, ThumbsUp, Info, Loader2
} from 'lucide-react'
import { apiHelpers, api } from '@/lib/api'
import { AdminAuthGate } from '@/components/AuthGate'
import { SkeletonTable } from '@/components/ui/Skeleton'
import { AdminModal } from '@/components/ui/AdminModal'
import FetchError from '@/components/ui/FetchError'

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

const ROLE_LABELS: Record<string, string> = {
    admin: 'Admin',
    moderator: 'Moderator',
    user: 'Regular',
}

function TrustedListContent() {
    const [users, setUsers] = useState<TrustedUser[]>([])
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')
    const [allUsers, setAllUsers] = useState<any[]>([])
    const [activeTab, setActiveTab] = useState<'trusted' | 'search'>('trusted')
    const [fetchError, setFetchError] = useState<string | null>(null)

    // "Change access" modal: one place to toggle Trusted Contributor and the
    // per-user moderation exemption, with the consequences stated in words.
    const [accessModal, setAccessModal] = useState<{ isOpen: boolean; user: any | null }>({
        isOpen: false,
        user: null,
    })
    const [draft, setDraft] = useState<{ trusted: boolean; exempt: boolean } | null>(null)
    const [applying, setApplying] = useState(false)
    const [modalError, setModalError] = useState('')

    useEffect(() => {
        fetchTrusted()
    }, [])

    const fetchTrusted = async () => {
        setLoading(true)
        try {
            const response = await apiHelpers.getTrustedUsers()
            // Envelope {results: [UserPromotionResponse]}; the id key is user_id.
            const rows: any[] = Array.isArray(response.data) ? response.data : response.data.results ?? []
            setUsers(rows.map((u: any) => ({ ...u, id: u.id ?? u.user_id })))
            setFetchError(null)
        } catch (error) {
            console.error('Failed to fetch trusted users:', error)
            setFetchError('Failed to load the trusted list. It may not actually be empty.')
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
            setFetchError(null)
        } catch (error) {
            console.error('Failed to search users:', error)
            setFetchError('User search failed. Try again.')
        } finally {
            setLoading(false)
        }
    }

    const patchRow = (userId: string, changes: Partial<TrustedUser & { moderation_exempt: boolean }>) => {
        setUsers(prev => prev.map(u => (u.id === userId ? { ...u, ...changes } : u)))
        setAllUsers(prev => prev.map(u => (u.id === userId ? { ...u, ...changes } : u)))
    }

    const openAccessModal = (user: any) => {
        setAccessModal({ isOpen: true, user })
        setDraft({ trusted: !!user.is_trusted, exempt: !!user.moderation_exempt })
        setModalError('')
    }

    const closeAccessModal = () => {
        setAccessModal({ isOpen: false, user: null })
        setDraft(null)
        setModalError('')
    }

    const applyAccessChanges = async () => {
        const target = accessModal.user
        if (!target || !draft) return

        const ops: { label: string; run: () => Promise<void>; done: boolean }[] = []
        if (draft.trusted !== !!target.is_trusted) {
            const nextTrusted = draft.trusted
            ops.push({
                label: 'Trusted Contributor status',
                done: false,
                run: async () => {
                    await apiHelpers.promoteUser(target.id, { is_trusted: nextTrusted })
                },
            })
        }
        if (draft.exempt !== !!target.moderation_exempt) {
            const nextExempt = draft.exempt
            ops.push({
                label: 'moderation exemption',
                done: false,
                run: async () => {
                    await apiHelpers.setUserModerationExempt(target.id, nextExempt)
                },
            })
        }

        if (ops.length === 0) {
            closeAccessModal()
            return
        }

        setApplying(true)
        setModalError('')
        try {
            const failures: string[] = []
            for (const op of ops) {
                try {
                    await op.run()
                    op.done = true
                } catch (error: any) {
                    console.error(`Failed to change ${op.label}:`, error)
                    failures.push(`${op.label} — ${error.response?.data?.detail || 'failed'}`)
                }
            }

            const finalTrusted = draft.trusted
            const finalExempt = draft.exempt
            // Reflect every op that landed on the server.
            if (failures.length === 0) {
                patchRow(target.id, { is_trusted: finalTrusted, moderation_exempt: finalExempt })
                closeAccessModal()
                // Revoking trust on the Trusted List removes the row — refresh
                // that list instead of leaving a stale mark behind.
                if (activeTab === 'trusted' && !!target.is_trusted !== finalTrusted) {
                    fetchTrusted()
                }
            } else if (failures.length < ops.length) {
                // Partial success: update what landed, keep the dialog open.
                const landedTrusted = ops.find(op => op.label.startsWith('Trusted'))?.done ? finalTrusted : target.is_trusted
                const landedExempt = ops.find(op => op.label.startsWith('Exempt') || op.label.startsWith('moderation'))?.done ? finalExempt : target.moderation_exempt
                patchRow(target.id, { is_trusted: landedTrusted, moderation_exempt: landedExempt })
                // Point the retry diff at what the server actually holds now.
                setAccessModal({
                    isOpen: true,
                    user: { ...target, is_trusted: landedTrusted, moderation_exempt: landedExempt },
                })
                setModalError(`${failures.join('; ')} The applied changes are active; retry the rest.`)
            } else {
                setModalError(`${failures.join('; ')} No change was applied.`)
            }
        } finally {
            setApplying(false)
        }
    }

    return (
        <div className="container-custom py-8">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-primary">Trusted Contributors</h1>
                    <p className="text-text-secondary">Trust grants and per-user review bypass</p>
                </div>
                <div className="flex gap-2 p-1 bg-background-secondary rounded-lg border border-border-subtle">
                    <button
                        onClick={() => setActiveTab('trusted')}
                        aria-pressed={activeTab === 'trusted'}
                        className={`px-4 py-1.5 rounded-md text-sm font-medium transition-[background-color,color] ${activeTab === 'trusted' ? 'bg-accent-primary text-accent-ink' : 'text-text-secondary hover:text-text-primary'}`}
                    >
                        Trusted List
                    </button>
                    <button
                        onClick={() => setActiveTab('search')}
                        aria-pressed={activeTab === 'search'}
                        className={`px-4 py-1.5 rounded-md text-sm font-medium transition-[background-color,color] ${activeTab === 'search' ? 'bg-accent-primary text-accent-ink' : 'text-text-secondary hover:text-text-primary'}`}
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

            {fetchError && (
                <FetchError
                    message={fetchError}
                    onRetry={() => (activeTab === 'trusted' ? fetchTrusted() : searchUsers(searchQuery))}
                    className="mb-4"
                />
            )}

            <div className="card shadow-md overflow-hidden border border-border-subtle">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        {(loading || (activeTab === 'trusted' ? users : allUsers).length > 0) && (
                        <thead className="bg-background-secondary border-b border-border-subtle">
                            <tr>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">User</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Stats</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Status</th>
                                <th className="px-6 py-4 text-right text-xs font-medium text-text-muted">Actions</th>
                            </tr>
                        </thead>
                        )}
                        <tbody className="divide-y divide-border-subtle">
                            {loading ? (
                                [...Array(3)].map((_, i) => (
                                    <tr key={i}><td colSpan={4} className="px-6 py-4"><div className="h-6 bg-background-tertiary animate-pulse rounded" /></td></tr>
                                ))
                            ) : (activeTab === 'trusted' ? users : allUsers).length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="px-6 py-12 text-center text-text-secondary">
                                        {activeTab === 'trusted' ? 'No trusted contributors yet.' : 'Search for users to grant access.'}
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
                                                    <Star className="w-3 h-3 text-warning-light" />
                                                    <span className="text-text-secondary">{u.upload_count || 0} Uploads</span>
                                                </div>
                                                <div className="flex items-center gap-2 text-xs">
                                                    <ThumbsUp className="w-3 h-3 text-success-light" />
                                                    <span className="text-text-secondary">{u.approved_count || 0} Approved</span>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            {u.is_trusted ? (
                                                <div className="flex items-center gap-1.5 px-2.5 py-1 bg-success/10 border border-success/20 rounded-md w-fit">
                                                    <ShieldCheck className="w-3.5 h-3.5 text-success-light" />
                                                    <span className="text-[11px] font-semibold text-success-light">Trusted</span>
                                                </div>
                                            ) : (
                                                <div className="flex items-center gap-1.5 px-2.5 py-1 bg-background-tertiary border border-border-subtle rounded-md w-fit">
                                                    <Shield className="w-3.5 h-3.5 text-text-muted" />
                                                    <span className="text-[11px] font-semibold text-text-muted">Regular</span>
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            {u.role !== 'admin' && (
                                                <button
                                                    onClick={() => openAccessModal(u)}
                                                    className="btn btn-secondary px-3 py-1.5 text-xs"
                                                >
                                                    Change access
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

            <div className="mt-8 p-6 bg-accent-primary/5 border border-accent-primary/20 rounded-xl">
                <div className="flex gap-4">
                    <div className="w-12 h-12 bg-accent-primary/10 rounded-lg flex items-center justify-center shrink-0">
                        <Info className="w-6 h-6 text-accent-primary" />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-text-primary mb-1">What is a Trusted Contributor?</h3>
                        <p className="text-sm text-text-secondary leading-relaxed max-w-2xl">
                            A Trusted Contributor is a person you have marked for a strong approval-to-upload history.
                            <strong> The per-user “Publish without review” switch is what actually lets uploads publish without review</strong>{' '}
                            — marking trusted status alone does not change moderation. Grant both when a user has earned zero-friction publishing.
                        </p>
                    </div>
                </div>
            </div>

            <AdminModal
                isOpen={accessModal.isOpen}
                onClose={closeAccessModal}
                title="Change access"
                maxWidth="md"
            >
                <div className="p-6 space-y-4">
                    {accessModal.user && (
                        <>
                            <div className="p-3 bg-background-tertiary rounded-lg border border-border-subtle">
                                <p className="font-bold text-text-primary text-sm">{accessModal.user.display_name || accessModal.user.email}</p>
                                <p className="text-xs text-text-muted">
                                    {accessModal.user.email} — {ROLE_LABELS[accessModal.user.role] || accessModal.user.role} account
                                </p>
                            </div>

                            {accessModal.user.role === 'admin' ? (
                                <p className="text-sm text-text-secondary">
                                    Admin accounts always publish without review, so trust and exemptions do not apply here.
                                </p>
                            ) : (
                                <>
                                    <div className="flex items-start justify-between gap-4 py-1">
                                        <div>
                                            <p className="text-sm font-semibold text-text-primary">Trusted Contributor</p>
                                            <p className="text-xs text-text-secondary mt-0.5">
                                                Marks them on the trusted list for their approval history. This alone does not change how uploads are moderated — pair it with the switch below for the publish effect.
                                            </p>
                                        </div>
                                        <button
                                            onClick={() => setDraft(prev => prev ? { ...prev, trusted: !prev.trusted } : prev)}
                                            role="switch"
                                            aria-checked={!!draft?.trusted}
                                            aria-label="Trusted Contributor"
                                            disabled={applying}
                                            className={`flex items-center gap-1 text-sm font-semibold shrink-0 transition-colors disabled:opacity-50 ${draft?.trusted ? 'text-success-light' : 'text-text-muted'}`}
                                        >
                                            {draft?.trusted ? <ToggleRight className="w-6 h-6" /> : <ToggleLeft className="w-6 h-6" />}
                                            {draft?.trusted ? 'Yes' : 'No'}
                                        </button>
                                    </div>

                                    {accessModal.user.role === 'user' ? (
                                        <div className="flex items-start justify-between gap-4 py-1">
                                            <div>
                                                <p className="text-sm font-semibold text-text-primary">Publish without review</p>
                                                <p className="text-xs text-text-secondary mt-0.5">
                                                    All their future uploads publish immediately. This is the switch the upload flow checks — the trust mark above does not publish anything by itself.
                                                </p>
                                            </div>
                                            <button
                                                onClick={() => setDraft(prev => prev ? { ...prev, exempt: !prev.exempt } : prev)}
                                                role="switch"
                                                aria-checked={!!draft?.exempt}
                                                aria-label="Publish without review"
                                                disabled={applying}
                                                className={`flex items-center gap-1 text-sm font-semibold shrink-0 transition-colors disabled:opacity-50 ${draft?.exempt ? 'text-warning-light' : 'text-text-muted'}`}
                                            >
                                                {draft?.exempt ? <ToggleRight className="w-6 h-6" /> : <ToggleLeft className="w-6 h-6" />}
                                                {draft?.exempt ? 'Yes' : 'No'}
                                            </button>
                                        </div>
                                    ) : (
                                        <p className="text-xs text-text-muted">
                                            Moderators and admins review uploads themselves, so a per-user bypass is not needed here.
                                        </p>
                                    )}

                                    {modalError && (
                                        <div className="p-3 bg-danger/10 border border-danger/30 rounded-lg text-danger text-sm" role="alert">
                                            {modalError}
                                        </div>
                                    )}

                                    <div className="pt-2 flex justify-end gap-3 border-t border-border-subtle">
                                        <button
                                            onClick={closeAccessModal}
                                            disabled={applying}
                                            className="btn btn-secondary"
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            onClick={applyAccessChanges}
                                            disabled={applying || !draft || (draft.trusted === !!accessModal.user.is_trusted && draft.exempt === !!accessModal.user.moderation_exempt)}
                                            className="btn btn-primary"
                                        >
                                            {applying ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                                            {applying ? 'Applying…' : 'Apply changes'}
                                        </button>
                                    </div>
                                </>
                            )}
                        </>
                    )}
                </div>
            </AdminModal>
        </div>
    )
}

// CRITICAL-002: same gate pattern as every other admin page
export default function UserPromotionPage() {
    return (
        <AdminAuthGate>
            <TrustedListContent />
        </AdminAuthGate>
    )
}
