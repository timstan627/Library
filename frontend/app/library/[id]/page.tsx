'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Plus, FileText, Trash2, Loader2, Search, Check, X as XIcon, AlertCircle, FolderOpen, Lock, Link2, Key, Globe } from 'lucide-react'
import { CollectionCoverIcon } from '@/lib/collection-icons'
import { useAuth } from '@/lib/auth-context'
import { api } from '@/lib/api'
import FetchError from '@/components/ui/FetchError'

interface CollectionItem {
    id: string
    resource_id: string
    sort_order: number
    added_at: string
    title: string | null
    file_name: string | null
    file_size: number | null
    file_extension: string | null
    mime_type: string | null
    visibility: string | null
    slug: string | null
}

interface CollectionDetail {
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
    items: CollectionItem[]
}

interface UserResource {
    id: string
    title: string
    slug: string
    file_name: string
    file_size: number
    file_extension: string
    visibility: string
    created_at: string
}

function formatSize(bytes: number) {
    if (!bytes || bytes === 0) return '0 B'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function getVisibilityBadge(v: string | null) {
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

export default function CollectionDetailPage() {
    const { user, isAuthenticated, isLoading: authLoading } = useAuth()
    const router = useRouter()
    const params = useParams()
    const collectionId = params.id as string

    const [collection, setCollection] = useState<CollectionDetail | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Add files modal
    const [showAddFiles, setShowAddFiles] = useState(false)
    const [userResources, setUserResources] = useState<UserResource[]>([])
    const [loadingResources, setLoadingResources] = useState(false)
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
    const [searchFilter, setSearchFilter] = useState('')
    const [adding, setAdding] = useState(false)
    const [pickerError, setPickerError] = useState(false)

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.replace('/auth/login?returnUrl=/library')
        }
    }, [authLoading, isAuthenticated, router])

    const fetchCollection = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)
            const res = await api.get(`/library/collections/${collectionId}`)
            setCollection(res.data)
        } catch (err: any) {
            setError(err?.response?.data?.detail || 'Collection not found')
        } finally {
            setLoading(false)
        }
    }, [collectionId])

    useEffect(() => {
        if (isAuthenticated && collectionId) fetchCollection()
    }, [isAuthenticated, collectionId, fetchCollection])

    const openAddFiles = async () => {
        setShowAddFiles(true)
        setSelectedIds(new Set())
        setSearchFilter('')
        try {
            setLoadingResources(true)
            const res = await api.get('/library/recent?limit=50')
            setUserResources(res.data || [])
            setPickerError(false)
        } catch (err) {
            console.error('Failed to load resources:', err)
            setPickerError(true)
        } finally {
            setLoadingResources(false)
        }
    }

    const toggleSelect = (id: string) => {
        setSelectedIds(prev => {
            const next = new Set(prev)
            if (next.has(id)) next.delete(id)
            else next.add(id)
            return next
        })
    }

    const handleAddSelected = async () => {
        if (selectedIds.size === 0) return
        try {
            setAdding(true)
            await api.post(`/library/collections/${collectionId}/items`, {
                resource_ids: Array.from(selectedIds),
            })
            setShowAddFiles(false)
            await fetchCollection()
        } catch (err: any) {
            alert(err?.response?.data?.detail || 'Failed to add files')
        } finally {
            setAdding(false)
        }
    }

    const handleRemoveItem = async (resourceId: string, title: string | null) => {
        if (!confirm(`Remove "${title || 'this file'}" from collection?`)) return
        try {
            await api.delete(`/library/collections/${collectionId}/items/${resourceId}`)
            await fetchCollection()
        } catch (err: any) {
            alert(err?.response?.data?.detail || 'Failed to remove')
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

    if (!isAuthenticated) return null

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background-primary">
                <div className="text-center">
                    <Loader2 className="w-8 h-8 animate-spin text-accent-primary mx-auto mb-3" />
                    <p className="text-sm text-text-muted">Loading collection...</p>
                </div>
            </div>
        )
    }

    if (error || !collection) {
        return (
            <div className="min-h-screen bg-background-primary">
                <div className="container-custom py-8 px-4">
                    <Link href="/library" className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary mb-8 transition-colors">
                        <ArrowLeft className="w-4 h-4" />
                        Back to Library
                    </Link>
                    <div className="flex flex-col items-center justify-center py-20">
                        <AlertCircle className="w-12 h-12 text-red-400/50 mb-4" />
                        <p className="text-base font-medium text-text-primary mb-1">Collection not found</p>
                        <p className="text-sm text-text-muted">{error || 'This collection may have been deleted'}</p>
                    </div>
                </div>
            </div>
        )
    }

    // Filter resources already in collection from the add picker
    const existingResourceIds = new Set(collection.items.map(i => i.resource_id))
    const filteredResources = userResources.filter(r => {
        if (existingResourceIds.has(r.id)) return false
        if (searchFilter) {
            return r.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
                r.file_name.toLowerCase().includes(searchFilter.toLowerCase())
        }
        return true
    })

    return (
        <div className="min-h-screen bg-background-primary">
            <div className="container-custom py-6 sm:py-8 px-4 sm:px-6">
                {/* Back link */}
                <Link href="/library" className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary mb-6 transition-colors">
                    <ArrowLeft className="w-4 h-4" />
                    My Library
                </Link>

                {/* ── Collection Header ── */}
                <div className="bg-background-secondary rounded-2xl border border-border-subtle p-6 sm:p-8 mb-8">
                    {/* Color accent */}
                    <div className="h-1.5 w-16 rounded-full mb-5" style={{ backgroundColor: collection.color }} />

                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                        <div className="flex-1 min-w-0">
                            <h1 className="text-xl sm:text-2xl font-bold text-text-primary flex items-center gap-3">
                                <span className="w-12 h-12 rounded-xl bg-accent-primary/10 flex items-center justify-center shrink-0">
                                    <CollectionCoverIcon name={collection.emoji} className="w-6 h-6 text-accent-primary" />
                                </span>
                                <span className="truncate">{collection.name}</span>
                            </h1>
                            {collection.description && (
                                <p className="text-sm text-text-secondary mt-2 ml-[44px]">{collection.description}</p>
                            )}
                            <div className="flex flex-wrap items-center gap-3 sm:gap-5 mt-3 ml-[44px] text-xs text-text-muted">
                                <span className="flex items-center gap-1.5">
                                    <FileText className="w-3 h-3" />
                                    {collection.item_count} file{collection.item_count !== 1 ? 's' : ''}
                                </span>
                                <span>{formatSize(collection.total_size)}</span>
                                <span>Created {new Date(collection.created_at).toLocaleDateString()}</span>
                            </div>
                        </div>
                        <button
                            onClick={openAddFiles}
                            className="btn btn-primary flex items-center justify-center gap-2 px-5 py-2.5 self-start"
                        >
                            <Plus className="w-4 h-4" />
                            Add Files
                        </button>
                    </div>
                </div>

                {/* ── File List ── */}
                {collection.items.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 bg-background-secondary/50 rounded-2xl border border-dashed border-border-subtle">
                        <div className="w-16 h-16 rounded-2xl bg-accent-primary/10 flex items-center justify-center mb-4">
                            <FolderOpen className="w-8 h-8 text-accent-primary/50" />
                        </div>
                        <p className="text-base font-medium text-text-primary mb-1">Empty collection</p>
                        <p className="text-sm text-text-muted mb-5 text-center max-w-xs">
                            Add files from your uploads to this collection
                        </p>
                        <button onClick={openAddFiles} className="btn btn-primary btn-sm flex items-center gap-1.5">
                            <Plus className="w-4 h-4" /> Add Files
                        </button>
                    </div>
                ) : (
                    <div className="bg-background-secondary rounded-xl border border-border-subtle overflow-hidden divide-y divide-border-subtle">
                        {collection.items.map(item => {
                            const badge = getVisibilityBadge(item.visibility)
                            return (
                                <div
                                    key={item.id}
                                    className="flex items-center gap-4 p-4 hover:bg-background-tertiary/50 transition-colors group"
                                >
                                    <Link
                                        href={item.slug ? `/resources/${item.slug}` : '#'}
                                        className="flex items-center gap-4 min-w-0 flex-1"
                                    >
                                        <div className="w-9 h-9 rounded-lg bg-accent-primary/10 flex items-center justify-center shrink-0">
                                            <FileText className="w-4 h-4 text-accent-primary" />
                                        </div>
                                        <div className="min-w-0 flex-1">
                                            <p className="text-sm font-medium text-text-primary truncate">
                                                {item.title || item.file_name || 'Untitled'}
                                            </p>
                                            <p className="text-xs text-text-muted mt-0.5 flex flex-wrap gap-x-3">
                                                <span>{(item.file_extension || '').toUpperCase()}</span>
                                                <span>{formatSize(item.file_size || 0)}</span>
                                                <span>Added {timeAgo(item.added_at)}</span>
                                            </p>
                                        </div>
                                    </Link>

                                    <div className="flex items-center gap-2 shrink-0">
                                        <span className={`inline-flex ${badge.cls}`} title={item.visibility || 'public'}>
                                            <badge.Icon className="w-4 h-4" aria-hidden="true" />
                                        </span>
                                        <button
                                            onClick={() => handleRemoveItem(item.resource_id, item.title)}
                                            className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-danger/15 text-text-muted hover:text-danger-light transition-[opacity,background-color,color]"
                                            title="Remove from collection"
                                        >
                                            <XIcon className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                )}

                {/* ── Add Files Modal ── */}
                {showAddFiles && (
                    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowAddFiles(false)}>
                        <div className="bg-background-secondary rounded-2xl border border-border-subtle w-full max-w-lg max-h-[80vh] flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
                            {/* Modal header */}
                            <div className="p-6 pb-4">
                                <h3 className="text-lg font-semibold text-text-primary mb-4">
                                    Add Files to &quot;{collection.name}&quot;
                                </h3>
                                <div className="relative">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                                    <input
                                        type="text"
                                        className="input pl-10"
                                        placeholder="Search your uploads..."
                                        value={searchFilter}
                                        onChange={e => setSearchFilter(e.target.value)}
                                        autoFocus
                                    />
                                </div>
                            </div>

                            {/* File list */}
                            <div className="flex-1 overflow-y-auto px-6 pb-4">
                                {loadingResources ? (
                                    <div className="flex justify-center py-10">
                                        <Loader2 className="w-6 h-6 animate-spin text-accent-primary" />
                                    </div>
                                ) : pickerError ? (
                                    <div className="py-6">
                                        <FetchError
                                            message="Your files could not be loaded. Close and reopen this dialog to retry."
                                        />
                                    </div>
                                ) : filteredResources.length === 0 ? (
                                    <div className="text-center py-10">
                                        <FileText className="w-8 h-8 text-text-muted/40 mx-auto mb-2" />
                                        <p className="text-sm text-text-muted">
                                            {searchFilter ? 'No matching files found' : 'All your files are already in this collection'}
                                        </p>
                                    </div>
                                ) : (
                                    <div className="space-y-1.5">
                                        {filteredResources.map(r => {
                                            const isSelected = selectedIds.has(r.id)
                                            const badge = getVisibilityBadge(r.visibility)
                                            return (
                                                <button
                                                    key={r.id}
                                                    onClick={() => toggleSelect(r.id)}
                                                    className={`w-full flex items-center gap-3 p-3.5 rounded-xl text-left transition-[background-color,border-color] ${isSelected
                                                            ? 'bg-accent-primary/10 border border-accent-primary/30'
                                                            : 'hover:bg-background-tertiary/70 border border-transparent'
                                                        }`}
                                                >
                                                    <div className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 transition-[background-color,border-color] ${isSelected
                                                            ? 'bg-accent-primary border-accent-primary'
                                                            : 'border-border-medium'
                                                        }`}>
                                                        {isSelected && <Check className="w-3 h-3 text-white" />}
                                                    </div>
                                                    <div className="min-w-0 flex-1">
                                                        <p className="text-sm font-medium text-text-primary truncate">{r.title}</p>
                                                        <p className="text-xs text-text-muted mt-0.5 flex flex-wrap gap-x-3">
                                                            <span>{r.file_extension?.toUpperCase()}</span>
                                                            <span>{formatSize(r.file_size)}</span>
                                                        </p>
                                                    </div>
                                                    <span className={`shrink-0 inline-flex ${badge.cls}`} title={r.visibility}>
                                                        <badge.Icon className="w-4 h-4" aria-hidden="true" />
                                                    </span>
                                                </button>
                                            )
                                        })}
                                    </div>
                                )}
                            </div>

                            {/* Modal footer */}
                            <div className="p-6 pt-4 border-t border-border-subtle flex gap-3">
                                <button onClick={() => setShowAddFiles(false)} className="btn flex-1 bg-background-tertiary text-text-secondary hover:text-text-primary">
                                    Cancel
                                </button>
                                <button
                                    onClick={handleAddSelected}
                                    disabled={selectedIds.size === 0 || adding}
                                    className="btn btn-primary flex-1 disabled:opacity-50"
                                >
                                    {adding ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        `Add ${selectedIds.size || ''} Selected`
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
