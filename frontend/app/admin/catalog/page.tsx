'use client'

import { useState, useEffect } from 'react'
import {
    Plus, Edit2, Trash2, ToggleLeft, ToggleRight,
    ChevronUp, ChevronDown, AlertCircle, Loader2, Info, Layers
} from 'lucide-react'
import { apiHelpers } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { AdminAuthGate } from '@/components/AuthGate'
import { ConfirmDeleteModal } from '@/components/ui/ConfirmDeleteModal'
import FetchError from '@/components/ui/FetchError'

interface Shelf {
    id: string
    title: string
    source_type: 'recent' | 'most_read' | 'most_downloaded' | 'top_rated' | 'tag' | 'branch' | 'subject'
    source_value?: string | null
    item_limit: number
    position: number
    is_active: boolean
}

const SOURCE_TYPES: { value: Shelf['source_type']; label: string; needsValue: string | null }[] = [
    { value: 'recent', label: 'Recently uploaded', needsValue: null },
    { value: 'most_read', label: 'Most read (views)', needsValue: null },
    { value: 'most_downloaded', label: 'Most downloaded', needsValue: null },
    { value: 'top_rated', label: 'Top rated', needsValue: null },
    { value: 'tag', label: 'By tag', needsValue: 'Tag, e.g. system-design' },
    { value: 'branch', label: 'By branch', needsValue: 'Branch, e.g. CSE' },
    { value: 'subject', label: 'By subject / department', needsValue: 'Department name, e.g. Computer Science' },
]

const emptyForm = { title: '', source_type: 'recent' as Shelf['source_type'], source_value: '', item_limit: 8 }

function CatalogContent() {
    const { user, isAuthenticated } = useAuth()
    const [shelves, setShelves] = useState<Shelf[]>([])
    const [loading, setLoading] = useState(true)
    const [fetchError, setFetchError] = useState<string | null>(null)

    const [showModal, setShowModal] = useState(false)
    const [editingShelf, setEditingShelf] = useState<Shelf | null>(null)
    const [submitting, setSubmitting] = useState(false)
    const [formData, setFormData] = useState(emptyForm)
    const [error, setError] = useState('')
    const [departments, setDepartments] = useState<string[]>([])
    const [subjectOptions, setSubjectOptions] = useState<string>(`${new Date().getFullYear()}`)

    const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; shelf: Shelf | null }>({
        isOpen: false,
        shelf: null,
    })

    useEffect(() => {
        if (isAuthenticated && user?.role === 'admin') {
            fetchShelves()
            fetchDepartmentsLight()
        }
    }, [isAuthenticated, user])

    const fetchShelves = async () => {
        setLoading(true)
        try {
            const response = await apiHelpers.getShelvesAdmin()
            setShelves(response.data)
            setFetchError(null)
        } catch (error) {
            console.error('Failed to fetch shelves:', error)
            setFetchError('Failed to load catalog shelves. Check that the backend is running.')
        } finally {
            setLoading(false)
        }
    }

    async function fetchDepartmentsLight() {
        try {
            const response = await apiHelpers.getDepartments()
            const names: string[] = (response.data || []).map((d: { name?: string }) => d.name).filter(Boolean)
            setDepartments(names)
        } catch {
            // datalist is a nicety, not a requirement
        }
    }

    const openModal = (shelf?: Shelf) => {
        if (shelf) {
            setEditingShelf(shelf)
            setFormData({
                title: shelf.title,
                source_type: shelf.source_type,
                source_value: shelf.source_value || '',
                item_limit: shelf.item_limit,
            })
        } else {
            setEditingShelf(null)
            setFormData(emptyForm)
        }
        setError('')
        setShowModal(true)
    }

    const closeModal = () => {
        setShowModal(false)
        setEditingShelf(null)
        setFormData(emptyForm)
        setError('')
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        const typeDef = SOURCE_TYPES.find(t => t.value === formData.source_type)
        if (typeDef?.needsValue && !formData.source_value.trim()) {
            setError(`A ${typeDef.needsValue.split(',')[0].toLowerCase()} value is required for this shelf type`)
            return
        }
        setSubmitting(true)
        setError('')
        try {
            const payload: any = {
                title: formData.title.trim(),
                source_type: formData.source_type,
                source_value: typeDef?.needsValue ? formData.source_value.trim() : null,
                item_limit: formData.item_limit,
            }
            if (editingShelf) {
                payload.position = editingShelf.position
                await apiHelpers.updateShelf(editingShelf.id, payload)
            } else {
                await apiHelpers.createShelf(payload)
            }
            closeModal()
            fetchShelves()
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Operation failed')
        } finally {
            setSubmitting(false)
        }
    }

    const handleToggle = async (shelf: Shelf) => {
        try {
            const response = await apiHelpers.toggleShelf(shelf.id)
            setShelves(shelves.map(s => s.id === shelf.id ? { ...s, is_active: response.data.is_active } : s))
        } catch {
            alert('Failed to toggle shelf status')
        }
    }

    const handleMove = async (shelf: Shelf, direction: 'up' | 'down') => {
        try {
            const response = await apiHelpers.moveShelf(shelf.id, direction)
            setShelves(response.data)
        } catch {
            alert('Failed to move shelf')
        }
    }

    const handleDelete = async () => {
        if (!deleteModal.shelf) return
        try {
            await apiHelpers.deleteShelf(deleteModal.shelf.id)
            setDeleteModal({ isOpen: false, shelf: null })
            fetchShelves()
        } catch {
            alert('Failed to delete shelf')
            setDeleteModal({ isOpen: false, shelf: null })
        }
    }

    const activeShelves = shelves.filter(s => s.is_active)
    const typeLabel = (t: Shelf['source_type']) => SOURCE_TYPES.find(x => x.value === t)?.label || t

    return (
        <div className="container-custom py-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                <div>
                    <h1 className="text-3xl font-bold text-text-primary">Catalog Shelves</h1>
                    <p className="text-text-secondary">Manage the discovery rows shown on the homepage and /browse</p>
                </div>
                <button
                    onClick={() => openModal()}
                    className="btn btn-primary flex items-center justify-center gap-2"
                >
                    <Plus className="w-5 h-5" />
                    New Shelf
                </button>
            </div>

            <div className="card p-4 mb-6 flex gap-2 items-start">
                <Info className="w-5 h-5 text-text-muted shrink-0 mt-0.5" />
                <p className="text-sm text-text-secondary">
                    {activeShelves.length === 0
                        ? <>No active shelves configured. The homepage and /browse currently show their built-in default rows.</>
                        : <>{activeShelves.length} active shelf{activeShelves.length === 1 ? '' : 's'} — these replace the built-in default rows on the homepage and /browse. Disabled (inactive) shelves are hidden entirely.</>}
                </p>
            </div>

            {fetchError && (
                <FetchError message={fetchError} onRetry={fetchShelves} className="mb-6" />
            )}

            <div className="card shadow-md overflow-hidden border border-border-subtle">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        {(loading || shelves.length > 0) && (
                            <thead className="bg-background-secondary border-b border-border-subtle">
                                <tr>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Order</th>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Shelf</th>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Source</th>
                                    <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Items</th>
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
                            ) : shelves.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center">
                                        <Layers className="w-10 h-10 text-text-muted mx-auto mb-3" />
                                        <p className="font-semibold text-text-primary mb-1">No shelves configured</p>
                                        <p className="text-sm text-text-secondary">The frontend shows its built-in discovery rows until you create one.</p>
                                    </td>
                                </tr>
                            ) : (
                                shelves.map((shelf, index) => (
                                    <tr key={shelf.id} className="hover:bg-background-tertiary transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-1">
                                                <button
                                                    onClick={() => handleMove(shelf, 'up')}
                                                    disabled={index === 0}
                                                    className="p-1.5 rounded-md transition-colors hover:bg-background-tertiary disabled:opacity-30 disabled:cursor-not-allowed text-text-secondary"
                                                    title="Move up"
                                                >
                                                    <ChevronUp className="w-4 h-4" />
                                                </button>
                                                <span className="w-8 h-8 flex items-center justify-center rounded-full bg-background-tertiary text-xs font-bold tabular-nums text-text-secondary">
                                                    {index + 1}
                                                </span>
                                                <button
                                                    onClick={() => handleMove(shelf, 'down')}
                                                    disabled={index === shelves.length - 1}
                                                    className="p-1.5 rounded-md transition-colors hover:bg-background-tertiary disabled:opacity-30 disabled:cursor-not-allowed text-text-secondary"
                                                    title="Move down"
                                                >
                                                    <ChevronDown className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-col gap-0.5">
                                                <span className="font-bold text-text-primary">{shelf.title}</span>
                                                {!shelf.is_active && <span className="text-xs text-text-muted">hidden while inactive</span>}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-col gap-0.5">
                                                <span className="text-sm font-medium text-text-secondary">{typeLabel(shelf.source_type)}</span>
                                                {shelf.source_value && (
                                                    <span className="text-xs text-text-muted font-mono">{shelf.source_value}</span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="text-sm font-medium tabular-nums">up to {shelf.item_limit}</span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <button
                                                onClick={() => handleToggle(shelf)}
                                                className={`flex items-center gap-1 text-xs font-semibold transition-colors ${shelf.is_active ? 'text-success-light' : 'text-text-muted'}`}
                                            >
                                                {shelf.is_active ? (
                                                    <><ToggleRight className="w-5 h-5" /> Active</>
                                                ) : (
                                                    <><ToggleLeft className="w-5 h-5" /> Inactive</>
                                                )}
                                            </button>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex justify-end gap-2">
                                                <button
                                                    onClick={() => openModal(shelf)}
                                                    className="p-2 text-blue-500 hover:bg-blue-500/10 rounded-md transition-colors"
                                                    title="Edit"
                                                >
                                                    <Edit2 className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => setDeleteModal({ isOpen: true, shelf })}
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

            {/* Shelf modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="card w-full max-w-lg p-0 animate-scale-in shadow-2xl overflow-hidden">
                        <div className="bg-background-secondary p-6 border-b border-border-subtle flex justify-between items-center">
                            <h2 className="text-xl font-bold text-text-primary">
                                {editingShelf ? 'Edit Shelf' : 'Create New Shelf'}
                            </h2>
                            <button onClick={closeModal} className="text-text-muted hover:text-text-primary" aria-label="Close">
                                ✕
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            <div>
                                <label className="label">Shelf Title *</label>
                                <input
                                    type="text"
                                    required
                                    value={formData.title}
                                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                    placeholder="e.g. System Design Gems"
                                    className="input"
                                />
                            </div>

                            <div>
                                <label className="label">Source *</label>
                                <select
                                    value={formData.source_type}
                                    onChange={(e) => setFormData({ ...formData, source_type: e.target.value as Shelf['source_type'] })}
                                    className="input"
                                >
                                    {SOURCE_TYPES.map(t => (
                                        <option key={t.value} value={t.value}>{t.label}</option>
                                    ))}
                                </select>
                            </div>

                            {SOURCE_TYPES.find(t => t.value === formData.source_type)?.needsValue && (
                                <div>
                                    <label className="label">Value *</label>
                                    {formData.source_type === 'subject' ? (
                                        <>
                                            <input
                                                type="text"
                                                list="shelf-departments"
                                                required
                                                value={formData.source_value}
                                                onChange={(e) => setFormData({ ...formData, source_value: e.target.value })}
                                                placeholder="Department name"
                                                className="input"
                                            />
                                            <datalist id="shelf-departments">
                                                {departments.map(name => <option key={name} value={name} />)}
                                            </datalist>
                                        </>
                                    ) : (
                                        <input
                                            type="text"
                                            required
                                            value={formData.source_value}
                                            onChange={(e) => setFormData({ ...formData, source_value: e.target.value })}
                                            placeholder={SOURCE_TYPES.find(t => t.value === formData.source_type)?.needsValue ?? ''}
                                            className="input"
                                        />
                                    )}
                                </div>
                            )}

                            <div>
                                <label className="label">Max Items (1–48)</label>
                                <input
                                    type="number"
                                    min={1}
                                    max={48}
                                    required
                                    value={formData.item_limit}
                                    onChange={(e) => setFormData({ ...formData, item_limit: Math.max(1, Math.min(48, Number(e.target.value) || 1)) })}
                                    className="input"
                                />
                            </div>

                            {error && (
                                <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-md text-red-600 text-sm">
                                    <AlertCircle className="w-4 h-4" />
                                    {error}
                                </div>
                            )}

                            <div className="pt-4 flex justify-end gap-3 border-t border-border-subtle">
                                <button type="button" onClick={closeModal} className="btn btn-secondary">Cancel</button>
                                <button
                                    type="submit"
                                    disabled={submitting}
                                    className="btn btn-primary"
                                >
                                    {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : editingShelf ? 'Save Changes' : 'Create Shelf'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            <ConfirmDeleteModal
                isOpen={deleteModal.isOpen}
                onClose={() => setDeleteModal({ isOpen: false, shelf: null })}
                onConfirm={handleDelete}
                title="Delete Shelf"
                itemName={deleteModal.shelf?.title || ''}
                itemType="shelf"
            />
        </div>
    )
}

export default function CatalogAdminPage() {
    return (
        <AdminAuthGate>
            <CatalogContent />
        </AdminAuthGate>
    )
}
