'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Plus, BookOpen, FolderOpen, FileText, Trash2, Edit2, Loader2, AlertCircle, Clock, Archive, Lock, Link2, Key, Globe } from 'lucide-react'
import { COVER_ICONS, DEFAULT_COVER_ICON, CollectionCoverIcon } from '@/lib/collection-icons'
import { useAuth } from '@/lib/auth-context'
import { api } from '@/lib/api'

interface Collection {
    id: string
    name: string
    description: string | null
    emoji: string
    color: string
    sort_order: number
    item_count: number
    total_size: number
    created_at: string
    updated_at: string
}

interface RecentUpload {
    id: string
    title: string
    slug: string
    file_name: string
    file_size: number
    file_extension: string
    visibility: string
    created_at: string
}

const COLOR_OPTIONS = ['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f97316', '#eab308', '#22c55e', '#06b6d4', '#3b82f6', '#64748b']

function formatSize(bytes: number) {
    if (bytes === 0) return '0 B'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function getVisibilityBadge(v: string) {
    switch (v) {
        case 'private': return { Icon: Lock, cls: 'text-danger-light' }
        case 'unlisted': return { Icon: Link2, cls: 'text-warning-light' }
        case 'password': return { Icon: Key, cls: 'text-accent-light' }
        default: return { Icon: Globe, cls: 'text-success-light' }
    }
}

function timeAgo(dateStr: string) {
    const now = new Date()
    const date = new Date(dateStr)
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHrs = Math.floor(diffMins / 60)
    if (diffHrs < 24) return `${diffHrs}h ago`
    const diffDays = Math.floor(diffHrs / 24)
    if (diffDays < 30) return `${diffDays}d ago`
    return date.toLocaleDateString()
}

export default function LibraryPage() {
    const { user, isAuthenticated, isLoading: authLoading } = useAuth()
    const router = useRouter()

    const [collections, setCollections] = useState<Collection[]>([])
    const [recentUploads, setRecentUploads] = useState<RecentUpload[]>([])
    const [uncategorizedCount, setUncategorizedCount] = useState(0)
    const [totalCount, setTotalCount] = useState(0)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Create modal
    const [showCreate, setShowCreate] = useState(false)
    const [newName, setNewName] = useState('')
    const [newDesc, setNewDesc] = useState('')
    const [newEmoji, setNewEmoji] = useState(DEFAULT_COVER_ICON)
    const [newColor, setNewColor] = useState('#6366f1')
    const [creating, setCreating] = useState(false)

    // Edit modal
    const [editingId, setEditingId] = useState<string | null>(null)
    const [editName, setEditName] = useState('')
    const [editDesc, setEditDesc] = useState('')
    const [editEmoji, setEditEmoji] = useState(DEFAULT_COVER_ICON)
    const [editColor, setEditColor] = useState('#6366f1')

    // Redirect if not authenticated
    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.replace('/auth/login?returnUrl=/library')
        }
    }, [authLoading, isAuthenticated, router])

    const fetchData = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)
            const [collRes, recentRes, uncatRes] = await Promise.all([
                api.get('/library/collections'),
                api.get('/library/recent?limit=10'),
                api.get('/library/uncategorized-count'),
            ])
            setCollections(collRes.data || [])
            setRecentUploads(recentRes.data || [])
            setUncategorizedCount(uncatRes.data?.uncategorized || 0)
            setTotalCount(uncatRes.data?.total || 0)
        } catch (err: any) {
            setError(err?.response?.data?.detail || 'Failed to load library')
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        if (isAuthenticated) fetchData()
    }, [isAuthenticated, fetchData])

    const handleCreate = async () => {
        if (!newName.trim()) return
        try {
            setCreating(true)
            await api.post('/library/collections', {
                name: newName.trim(),
                description: newDesc.trim() || null,
                emoji: newEmoji,
                color: newColor,
            })
            setShowCreate(false)
            setNewName('')
            setNewDesc('')
            setNewEmoji(DEFAULT_COVER_ICON)
            setNewColor('#6366f1')
            await fetchData()
        } catch (err: any) {
            alert(err?.response?.data?.detail || 'Failed to create collection')
        } finally {
            setCreating(false)
        }
    }

    const handleUpdate = async (id: string) => {
        try {
            await api.put(`/library/collections/${id}`, {
                name: editName.trim(),
                description: editDesc.trim() || null,
                emoji: editEmoji,
                color: editColor,
            })
            setEditingId(null)
            await fetchData()
        } catch (err: any) {
            alert(err?.response?.data?.detail || 'Failed to update')
        }
    }

    const handleDelete = async (id: string, name: string) => {
        if (!confirm(`Delete "${name}"? Files won't be deleted, only the collection.`)) return
        try {
            await api.delete(`/library/collections/${id}`)
            await fetchData()
        } catch (err: any) {
            alert(err?.response?.data?.detail || 'Failed to delete')
        }
    }

    if (authLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background-primary">
                <div className="text-center">
                    <Loader2 className="w-8 h-8 animate-spin text-accent-primary mx-auto mb-3" />
                    <p className="text-sm text-text-muted">Loading...</p>
                </div>
            </div>
        )
    }

    if (!isAuthenticated) {
        return null // Redirect will happen via useEffect
    }

    return (
        <div className="min-h-screen bg-background-primary">
            <div className="container-custom py-6 sm:py-8 px-4 sm:px-6">
                {/* ── Page Header ── */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
                    <div>
                        <h1 className="text-2xl sm:text-3xl font-bold text-text-primary flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-accent-primary/15 flex items-center justify-center">
                                <BookOpen className="w-5 h-5 text-accent-primary" />
                            </div>
                            My Library
                        </h1>
                        <p className="text-sm text-text-secondary mt-2 ml-[52px] sm:ml-[52px]">
                            Organize your uploads into personal collections
                        </p>
                    </div>
                    <button
                        onClick={() => setShowCreate(true)}
                        className="btn btn-primary flex items-center justify-center gap-2 px-5 py-2.5 self-start sm:self-auto"
                    >
                        <Plus className="w-4 h-4" />
                        New Collection
                    </button>
                </div>

                {/* ── Stats Bar ── */}
                {!loading && !error && (
                    <div className="grid grid-cols-3 gap-3 sm:gap-4 mb-8">
                        <div className="p-4 bg-background-secondary rounded-xl border border-border-subtle text-center">
                            <p className="text-xl sm:text-2xl font-bold text-text-primary">{collections.length}</p>
                            <p className="text-xs text-text-muted mt-1">Collections</p>
                        </div>
                        <div className="p-4 bg-background-secondary rounded-xl border border-border-subtle text-center">
                            <p className="text-xl sm:text-2xl font-bold text-text-primary">{totalCount}</p>
                            <p className="text-xs text-text-muted mt-1">Total Files</p>
                        </div>
                        <div className="p-4 bg-background-secondary rounded-xl border border-border-subtle text-center">
                            <p className="text-xl sm:text-2xl font-bold text-accent-primary">{uncategorizedCount}</p>
                            <p className="text-xs text-text-muted mt-1">Uncategorized</p>
                        </div>
                    </div>
                )}

                {/* ── Error Banner ── */}
                {error && (
                    <div className="flex items-center gap-3 p-4 mb-8 bg-red-500/8 border border-red-500/20 rounded-xl">
                        <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-red-400">{error}</p>
                            <p className="text-xs text-red-400/60 mt-0.5">Try refreshing the page or check your connection</p>
                        </div>
                        <button onClick={fetchData} className="text-xs text-red-400 hover:text-red-300 font-medium shrink-0">
                            Retry
                        </button>
                    </div>
                )}

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-24">
                        <Loader2 className="w-8 h-8 animate-spin text-accent-primary mb-3" />
                        <p className="text-sm text-text-muted">Loading your library...</p>
                    </div>
                ) : (
                    <div className="space-y-10">
                        {/* ── Collections Section ── */}
                        <section>
                            <div className="flex items-center justify-between mb-5">
                                <h2 className="text-base sm:text-lg font-semibold text-text-primary flex items-center gap-2.5">
                                    <FolderOpen className="w-5 h-5 text-accent-primary" />
                                    Collections
                                    <span className="text-xs font-normal text-text-muted bg-background-tertiary px-2 py-0.5 rounded-full">
                                        {collections.length}
                                    </span>
                                </h2>
                            </div>

                            {collections.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-14 bg-background-secondary/50 rounded-2xl border border-dashed border-border-subtle">
                                    <div className="w-16 h-16 rounded-2xl bg-accent-primary/10 flex items-center justify-center mb-4">
                                        <FolderOpen className="w-8 h-8 text-accent-primary/50" />
                                    </div>
                                    <p className="text-base font-medium text-text-primary mb-1">No collections yet</p>
                                    <p className="text-sm text-text-muted mb-5 text-center max-w-xs">
                                        Create your first collection to organize your uploaded files
                                    </p>
                                    <button
                                        onClick={() => setShowCreate(true)}
                                        className="btn btn-primary btn-sm flex items-center gap-1.5"
                                    >
                                        <Plus className="w-4 h-4" /> Create Collection
                                    </button>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 stagger">
                                    {collections.map(c => (
                                        <div key={c.id} className="group relative">
                                            <Link
                                                href={`/library/${c.id}`}
                                                className="block card card-interactive p-5 h-full"
                                            >
                                                {/* Color accent bar */}
                                                <div className="h-1 w-12 rounded-full mb-4" style={{ backgroundColor: c.color }} />

                                                <div className="flex items-center gap-3 mb-2">
                                                <span className="w-10 h-10 rounded-lg bg-accent-primary/10 flex items-center justify-center shrink-0">
                                                    <CollectionCoverIcon name={c.emoji} className="w-5 h-5 text-accent-primary" />
                                                </span>
                                                    <h3 className="font-semibold text-text-primary truncate text-sm sm:text-base flex-1">{c.name}</h3>
                                                </div>

                                                {c.description && (
                                                    <p className="text-xs text-text-muted line-clamp-2 mb-3 leading-relaxed">{c.description}</p>
                                                )}

                                                <div className="flex items-center gap-3 text-xs text-text-secondary pt-3 border-t border-border-subtle mt-auto">
                                                    <span className="flex items-center gap-1">
                                                        <FileText className="w-3 h-3" />
                                                        {c.item_count} file{c.item_count !== 1 ? 's' : ''}
                                                    </span>
                                                    <span>{formatSize(c.total_size)}</span>
                                                </div>
                                            </Link>

                                            {/* Hover actions */}
                                            <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1 z-10">
                                                <button
                                                    onClick={(e) => {
                                                        e.preventDefault()
                                                        e.stopPropagation()
                                                        setEditingId(c.id)
                                                        setEditName(c.name)
                                                        setEditDesc(c.description || '')
                                                        setEditEmoji(COVER_ICONS[c.emoji] ? c.emoji : DEFAULT_COVER_ICON)
                                                        setEditColor(c.color)
                                                    }}
                                                    className="p-1.5 rounded-lg bg-background-primary/80 backdrop-blur-sm hover:bg-accent-primary/20 text-text-secondary hover:text-accent-primary transition-colors"
                                                    title="Edit collection"
                                                >
                                                    <Edit2 className="w-3.5 h-3.5" />
                                                </button>
                                                <button
                                                    onClick={(e) => {
                                                        e.preventDefault()
                                                        e.stopPropagation()
                                                        handleDelete(c.id, c.name)
                                                    }}
                                                    className="p-1.5 rounded-lg bg-background-primary/80 backdrop-blur-sm hover:bg-red-500/20 text-text-secondary hover:text-red-400 transition-colors"
                                                    title="Delete collection"
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </section>

                        {/* ── Recent Uploads Section ── */}
                        <section>
                            <h2 className="text-base sm:text-lg font-semibold text-text-primary flex items-center gap-2.5 mb-5">
                                <Clock className="w-5 h-5 text-accent-primary" />
                                Recent Uploads
                            </h2>

                            {recentUploads.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-10 bg-background-secondary/50 rounded-2xl border border-dashed border-border-subtle">
                                    <FileText className="w-10 h-10 text-text-muted/40 mb-3" />
                                    <p className="text-sm text-text-muted mb-2">No uploads yet</p>
                                    <Link href="/upload" className="text-sm text-accent-light hover:text-accent-bright hover:underline font-medium transition-colors">
                                        Upload your first file
                                    </Link>
                                </div>
                            ) : (
                                <div className="bg-background-secondary rounded-xl border border-border-subtle overflow-hidden divide-y divide-border-subtle">
                                    {recentUploads.map(r => {
                                        const badge = getVisibilityBadge(r.visibility)
                                        return (
                                            <Link
                                                key={r.id}
                                                href={`/resources/${r.slug}`}
                                                className="flex items-center gap-4 p-4 hover:bg-background-tertiary/50 transition-colors"
                                            >
                                                <div className="w-9 h-9 rounded-lg bg-accent-primary/10 flex items-center justify-center shrink-0">
                                                    <FileText className="w-4 h-4 text-accent-primary" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-sm font-medium text-text-primary truncate">{r.title}</p>
                                                    <p className="text-xs text-text-muted mt-0.5 flex flex-wrap gap-x-3">
                                                        <span>{r.file_extension?.toUpperCase()}</span>
                                                        <span>{formatSize(r.file_size)}</span>
                                                        <span>{timeAgo(r.created_at)}</span>
                                                    </p>
                                                </div>
                                                <span className={`shrink-0 inline-flex ${badge.cls}`} title={r.visibility}>
                                                    <badge.Icon className="w-4 h-4" aria-hidden="true" />
                                                </span>
                                            </Link>
                                        )
                                    })}
                                </div>
                            )}
                        </section>

                        {/* ── Uncategorized Notice ── */}
                        {uncategorizedCount > 0 && (
                            <section className="flex items-center gap-4 p-4 sm:p-5 bg-amber-500/5 border border-amber-500/15 rounded-xl">
                                <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center shrink-0">
                                    <Archive className="w-5 h-5 text-amber-400" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-amber-300">
                                        {uncategorizedCount} uncategorized file{uncategorizedCount !== 1 ? 's' : ''}
                                    </p>
                                    <p className="text-xs text-amber-400/60 mt-0.5">
                                        Create a collection and add them to stay organized
                                    </p>
                                </div>
                            </section>
                        )}
                    </div>
                )}

                {/* ── Create Collection Modal ── */}
                {showCreate && (
                    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowCreate(false)}>
                        <div className="bg-background-secondary rounded-2xl border border-border-subtle w-full max-w-md p-6 shadow-2xl" onClick={e => e.stopPropagation()}>
                            <h3 className="text-lg font-semibold text-text-primary mb-5">New Collection</h3>

                            <div className="space-y-5">
                                <div>
                                    <label className="block text-sm font-medium text-text-secondary mb-1.5">Name</label>
                                    <input
                                        type="text"
                                        className="input"
                                        value={newName}
                                        onChange={e => setNewName(e.target.value)}
                                        placeholder="e.g. Sem 4 Notes"
                                        autoFocus
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-text-secondary mb-1.5">Description (optional)</label>
                                    <input
                                        type="text"
                                        className="input"
                                        value={newDesc}
                                        onChange={e => setNewDesc(e.target.value)}
                                        placeholder="Brief description..."
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-text-secondary mb-2">Icon</label>
                                    <div className="flex flex-wrap gap-2">
                                        {Object.entries(COVER_ICONS).map(([name, Icon]) => (
                                            <button
                                                key={name}
                                                type="button"
                                                onClick={() => setNewEmoji(name)}
                                                aria-pressed={newEmoji === name}
                                                className={`w-10 h-10 rounded-lg flex items-center justify-center transition-[background-color,box-shadow] ${newEmoji === name
                                                        ? 'bg-accent-primary/20 ring-2 ring-accent-primary'
                                                        : 'bg-background-tertiary hover:bg-background-primary'
                                                    }`}
                                            >
                                                <Icon className="w-5 h-5 text-text-primary" aria-hidden="true" />
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-text-secondary mb-2">Color</label>
                                    <div className="flex flex-wrap gap-2.5">
                                        {COLOR_OPTIONS.map(c => (
                                            <button
                                                key={c}
                                                type="button"
                                                onClick={() => setNewColor(c)}
                                                aria-pressed={newColor === c}
                                                className={`w-8 h-8 rounded-full transition-[transform,box-shadow] ${newColor === c
                                                        ? 'scale-125 ring-2 ring-offset-2 ring-offset-background-secondary'
                                                        : 'hover:scale-110'
                                                    }`}
                                                style={{ backgroundColor: c, boxShadow: newColor === c ? `0 0 12px ${c}40` : undefined }}
                                            />
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="flex gap-3 mt-6">
                                <button
                                    onClick={() => setShowCreate(false)}
                                    className="btn flex-1 bg-background-tertiary text-text-secondary hover:text-text-primary transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleCreate}
                                    disabled={!newName.trim() || creating}
                                    className="btn btn-primary flex-1 disabled:opacity-50"
                                >
                                    {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* ── Edit Collection Modal ── */}
                {editingId && (
                    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setEditingId(null)}>
                        <div className="bg-background-secondary rounded-2xl border border-border-subtle w-full max-w-md p-6 shadow-2xl" onClick={e => e.stopPropagation()}>
                            <h3 className="text-lg font-semibold text-text-primary mb-5">Edit Collection</h3>

                            <div className="space-y-5">
                                <div>
                                    <label className="block text-sm font-medium text-text-secondary mb-1.5">Name</label>
                                    <input type="text" className="input" value={editName} onChange={e => setEditName(e.target.value)} autoFocus />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-text-secondary mb-1.5">Description</label>
                                    <input type="text" className="input" value={editDesc} onChange={e => setEditDesc(e.target.value)} />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-text-secondary mb-2">Icon</label>
                                    <div className="flex flex-wrap gap-2">
                                        {Object.entries(COVER_ICONS).map(([name, Icon]) => (
                                            <button key={name} type="button" onClick={() => setEditEmoji(name)} aria-pressed={editEmoji === name}
                                                className={`w-10 h-10 rounded-lg flex items-center justify-center transition-[background-color,box-shadow] ${editEmoji === name ? 'bg-accent-primary/20 ring-2 ring-accent-primary' : 'bg-background-tertiary hover:bg-background-primary'
                                                    }`}
                                            >
                                                <Icon className="w-5 h-5 text-text-primary" aria-hidden="true" />
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-text-secondary mb-2">Color</label>
                                    <div className="flex flex-wrap gap-2.5">
                                        {COLOR_OPTIONS.map(c => (
                                            <button key={c} type="button" onClick={() => setEditColor(c)} aria-pressed={editColor === c}
                                                className={`w-8 h-8 rounded-full transition-[transform,box-shadow] ${editColor === c ? 'scale-125 ring-2 ring-offset-2 ring-offset-background-secondary' : 'hover:scale-110'}`}
                                                style={{ backgroundColor: c, boxShadow: editColor === c ? `0 0 12px ${c}40` : undefined }}
                                            />
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="flex gap-3 mt-6">
                                <button onClick={() => setEditingId(null)} className="btn flex-1 bg-background-tertiary text-text-secondary hover:text-text-primary">Cancel</button>
                                <button onClick={() => handleUpdate(editingId)} disabled={!editName.trim()} className="btn btn-primary flex-1 disabled:opacity-50">Save Changes</button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
