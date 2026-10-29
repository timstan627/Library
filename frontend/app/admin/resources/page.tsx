'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
    Trash2, Search, FileText, Download, Eye, Edit2, Loader2, RefreshCcw, CheckSquare, Square
} from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { ModeratorAuthGate } from '@/components/AuthGate'
import FetchError from '@/components/ui/FetchError'

interface Resource {
    id: string
    title: string
    slug: string
    course_code: string
    file_name: string
    file_size: number
    downloads: number
    views: number
    visibility: string
    moderation_status: string
    created_at: string
}

function ResourcesContent() {
    const { user } = useAuth()
    const [resources, setResources] = useState<Resource[]>([])
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
    const [deleting, setDeleting] = useState(false)
    const [fetchError, setFetchError] = useState<string | null>(null)

    useEffect(() => {
        fetchResources()
    }, [page])

    const fetchResources = async () => {
        setLoading(true)
        try {
            const response = await api.get('/admin/resources', {
                params: { page, page_size: 50 }
            })
            setResources(response.data.results || [])
            setTotalPages(Math.ceil((response.data.total || 0) / 50))
            setFetchError(null)
        } catch (error) {
            console.error('Failed to fetch resources:', error)
            setFetchError('Failed to load resources. The list may not actually be empty.')
        } finally {
            setLoading(false)
        }
    }

    const toggleSelect = (id: string) => {
        setSelectedIds(prev => {
            const next = new Set(prev)
            if (next.has(id)) {
                next.delete(id)
            } else {
                next.add(id)
            }
            return next
        })
    }

    const selectAll = () => {
        if (selectedIds.size === filteredResources.length) {
            setSelectedIds(new Set())
        } else {
            setSelectedIds(new Set(filteredResources.map(r => r.id)))
        }
    }

    const handleDeleteSingle = async (id: string) => {
        setDeleting(true)
        try {
            await api.delete(`/admin/resources/${id}`)
            setResources(prev => prev.filter(r => r.id !== id))
            selectedIds.delete(id)
            setSelectedIds(new Set(selectedIds))
        } catch (error) {
            console.error('Delete failed:', error)
            alert('Delete failed')
        } finally {
            setDeleting(false)
        }
    }

    const handleBulkDelete = async () => {
        if (selectedIds.size === 0) return
        setDeleting(true)
        try {
            await api.post('/admin/resources/bulk-delete', Array.from(selectedIds))
            setResources(prev => prev.filter(r => !selectedIds.has(r.id)))
            setSelectedIds(new Set())
        } catch (error) {
            console.error('Bulk delete failed:', error)
            alert('Some deletes failed')
        } finally {
            setDeleting(false)
        }
    }

    const handleDeleteAll = async () => {
        if (!confirm('Are you sure you want to delete ALL resources? This cannot be undone!')) return
        setDeleting(true)
        try {
            await api.delete('/admin/clear-all-data', { params: { confirm: 'CONFIRM_DELETE_ALL' } })
            setResources([])
            setSelectedIds(new Set())
            alert('All resources deleted')
        } catch (error) {
            console.error('Clear all failed:', error)
            alert('Clear all failed')
        } finally {
            setDeleting(false)
        }
    }

    const filteredResources = resources.filter(r =>
        r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.file_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.course_code.toLowerCase().includes(searchQuery.toLowerCase())
    )

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    return (
        <div className="container-custom py-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-primary">Resource Management</h1>
                    <p className="text-text-secondary">View, edit and delete all uploaded resources</p>
                </div>
                <div className="flex gap-2">
                    <button onClick={fetchResources} className="btn btn-secondary" disabled={loading}>
                        <RefreshCcw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                    <button
                        onClick={handleDeleteAll}
                        className="btn bg-red-600 hover:bg-red-700 text-white"
                        disabled={deleting}
                    >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Delete All
                    </button>
                </div>
            </div>

            {/* Search and Bulk Actions */}
            <div className="card mb-6 p-4">
                <div className="flex flex-col md:flex-row gap-4">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                        <input
                            type="text"
                            placeholder="Search by title, filename, or course code..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="input pl-10"
                        />
                    </div>
                    {selectedIds.size > 0 && (
                        <button
                            onClick={handleBulkDelete}
                            disabled={deleting}
                            className="btn bg-red-600 hover:bg-red-700 text-white"
                        >
                            {deleting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Trash2 className="w-4 h-4 mr-2" />}
                            Delete Selected ({selectedIds.size})
                        </button>
                    )}
                </div>
            </div>

            {/* Resources Table */}
            {fetchError && (
                <FetchError message={fetchError} onRetry={fetchResources} className="mb-4" />
            )}
            <div className="card shadow-md overflow-hidden border border-border-subtle">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        {(loading || filteredResources.length > 0) && (
                        <thead className="bg-background-secondary border-b border-border-subtle">
                            <tr>
                                <th className="px-4 py-4 text-left">
                                    <button onClick={selectAll} className="text-text-muted hover:text-text-primary">
                                        {selectedIds.size === filteredResources.length && filteredResources.length > 0 ? (
                                            <CheckSquare className="w-5 h-5" />
                                        ) : (
                                            <Square className="w-5 h-5" />
                                        )}
                                    </button>
                                </th>
                                <th className="px-4 py-4 text-left text-xs font-medium text-text-muted">Resource</th>
                                <th className="px-4 py-4 text-left text-xs font-medium text-text-muted">Course</th>
                                <th className="px-4 py-4 text-left text-xs font-medium text-text-muted">Stats</th>
                                <th className="px-4 py-4 text-right text-xs font-medium text-text-muted">Actions</th>
                            </tr>
                        </thead>
                        )}
                        <tbody className="divide-y divide-border-subtle">
                            {loading ? (
                                [...Array(5)].map((_, i) => (
                                    <tr key={i}><td colSpan={5} className="px-4 py-4"><div className="h-6 bg-background-tertiary animate-pulse rounded" /></td></tr>
                                ))
                            ) : filteredResources.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="px-4 py-12 text-center text-text-secondary">
                                        No resources found.
                                    </td>
                                </tr>
                            ) : (
                                filteredResources.map((resource) => (
                                    <tr key={resource.id} className="hover:bg-background-tertiary transition-colors">
                                        <td className="px-4 py-4">
                                            <button onClick={() => toggleSelect(resource.id)} className="text-text-muted hover:text-text-primary">
                                                {selectedIds.has(resource.id) ? (
                                                    <CheckSquare className="w-5 h-5 text-accent-primary" />
                                                ) : (
                                                    <Square className="w-5 h-5" />
                                                )}
                                            </button>
                                        </td>
                                        <td className="px-4 py-4">
                                            <div className="flex items-center gap-3">
                                                <FileText className="w-5 h-5 text-text-muted" />
                                                <div>
                                                    <p className="font-semibold text-text-primary">{resource.title}</p>
                                                    <p className="text-xs text-text-muted flex items-center gap-2">
                                                        <span className="truncate">{resource.file_name}</span>
                                                        <span className="shrink-0">{formatFileSize(resource.file_size)}</span>
                                                    </p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-4 py-4">
                                            <span className="font-mono text-sm">{resource.course_code}</span>
                                        </td>
                                        <td className="px-4 py-4">
                                            <div className="flex items-center gap-4 text-sm text-text-muted">
                                                <span className="flex items-center gap-1"><Eye className="w-4 h-4" /> {resource.views}</span>
                                                <span className="flex items-center gap-1"><Download className="w-4 h-4" /> {resource.downloads}</span>
                                            </div>
                                        </td>
                                        <td className="px-4 py-4 text-right">
                                            <div className="flex justify-end gap-1">
                                                <Link
                                                    href={`/resources/${resource.slug}/edit`}
                                                    className="p-2 text-blue-500 hover:bg-blue-500/10 rounded-md transition-colors"
                                                    title="Edit"
                                                >
                                                    <Edit2 className="w-4 h-4" />
                                                </Link>
                                                <button
                                                    onClick={() => handleDeleteSingle(resource.id)}
                                                    disabled={deleting}
                                                    className="p-2 text-red-500 hover:bg-red-500/10 rounded-md transition-colors"
                                                    title="Delete"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex justify-center gap-2 mt-6">
                    <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn btn-secondary">Previous</button>
                    <span className="px-4 py-2 text-text-secondary">Page {page} of {totalPages}</span>
                    <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="btn btn-secondary">Next</button>
                </div>
            )}
        </div>
    )
}

export default function AdminResourcesPage() {
    return (
        <ModeratorAuthGate>
            <ResourcesContent />
        </ModeratorAuthGate>
    )
}
