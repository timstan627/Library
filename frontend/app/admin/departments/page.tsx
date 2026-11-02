'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
    Plus, Edit2, Trash2, ToggleLeft, ToggleRight,
    Search, AlertCircle, CheckCircle, Info, Loader2
} from 'lucide-react'
import { apiHelpers } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { SkeletonTable } from '@/components/ui/Skeleton'
import { AdminAuthGate } from '@/components/AuthGate'
import { ConfirmDeleteModal } from '@/components/ui/ConfirmDeleteModal'
import { AdminModal } from '@/components/ui/AdminModal'
import FetchError from '@/components/ui/FetchError'

interface Department {
    id: string
    name: string
    code: string
    description?: string
    is_active: boolean
    course_count: number
}

function DepartmentsContent() {
    const { user, isAuthenticated } = useAuth()
    const router = useRouter()

    const [departments, setDepartments] = useState<Department[]>([])
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')

    // Modal states
    const [showModal, setShowModal] = useState<boolean>(false)
    const [editingDept, setEditingDept] = useState<Department | null>(null)
    const [submitting, setSubmitting] = useState(false)
    const [formData, setFormData] = useState({ name: '', code: '', description: '' })
    const [error, setError] = useState('')
    const [fetchError, setFetchError] = useState<string | null>(null)
    const [notice, setNotice] = useState<string | null>(null)

    // HIGH-003 & HIGH-004: Delete modal state
    const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; dept: Department | null }>({
        isOpen: false,
        dept: null
    })

    useEffect(() => {
        if (isAuthenticated && user?.role === 'admin') {
            fetchDepartments()
        }
    }, [isAuthenticated, user])

    const fetchDepartments = async () => {
        setLoading(true)
        try {
            const response = await apiHelpers.getDepartmentsAdmin(1, 100)
            setDepartments(response.data.results)
            setFetchError(null)
        } catch (error) {
            console.error('Failed to fetch departments:', error)
            setFetchError('Failed to load departments. The list may not actually be empty.')
        } finally {
            setLoading(false)
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setSubmitting(true)
        setError('')
        try {
            if (editingDept) {
                await apiHelpers.updateDepartment(editingDept.id, formData)
            } else {
                await apiHelpers.createDepartment(formData)
            }
            fetchDepartments()
            closeModal()
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Operation failed')
        } finally {
            setSubmitting(false)
        }
    }

    const handleToggle = async (id: string) => {
        try {
            await apiHelpers.toggleDepartment(id)
            setDepartments(departments.map(d =>
                d.id === id ? { ...d, is_active: !d.is_active } : d
            ))
        } catch (error) {
            setNotice('Failed to change the department status. Check the connection and try again.')
        }
    }

    // HIGH-004: Open type-to-confirm delete modal instead of using confirm()
    const openDeleteModal = (dept: Department) => {
        setDeleteModal({ isOpen: true, dept })
    }

    const handleDelete = async () => {
        if (!deleteModal.dept) return
        await apiHelpers.deleteDepartment(deleteModal.dept.id)
        setDepartments(departments.filter(d => d.id !== deleteModal.dept!.id))
    }

    const openModal = (dept: Department | null = null) => {
        if (dept) {
            setEditingDept(dept)
            setFormData({ name: dept.name, code: dept.code, description: dept.description || '' })
        } else {
            setEditingDept(null)
            setFormData({ name: '', code: '', description: '' })
        }
        setShowModal(true)
    }

    const closeModal = () => {
        setShowModal(false)
        setEditingDept(null)
        setFormData({ name: '', code: '', description: '' })
        setError('')
    }

    const filteredDepts = departments.filter(d =>
        d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.code.toLowerCase().includes(searchQuery.toLowerCase())
    )

    // Loading handled by AuthGate wrapper
    if (loading && departments.length === 0) {
        return <div className="p-8"><SkeletonTable rows={5} columns={4} /></div>
    }

    return (
        <div className="container-custom py-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-primary">Department Management</h1>
                    <p className="text-text-secondary">Organize courses by academic departments</p>
                </div>
                <button
                    onClick={() => openModal()}
                    className="btn btn-primary flex items-center justify-center gap-2"
                >
                    <Plus className="w-5 h-5" />
                    New Department
                </button>
            </div>

            <div className="card mb-6 p-4">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                    <input
                        type="text"
                        placeholder="Search by name or code..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="input pl-10"
                    />
                </div>
            </div>

            {fetchError && (
                <FetchError message={fetchError} onRetry={fetchDepartments} className="mb-6" />
            )}

            {notice && (
                <div className="mb-4 flex items-start justify-between gap-3 p-3 rounded-md border bg-danger/10 border-danger/30 text-danger text-sm" role="alert">
                    <span>{notice}</span>
                    <button
                        onClick={() => setNotice(null)}
                        className="shrink-0 text-text-muted hover:text-text-primary"
                        aria-label="Dismiss notice"
                    >
                        <AlertCircle className="w-4 h-4" />
                    </button>
                </div>
            )}

            <div className="card shadow-md overflow-hidden border border-border-subtle">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        {(loading || filteredDepts.length > 0) && (
                        <thead className="bg-background-secondary border-b border-border-subtle">
                            <tr>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Department</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Courses</th>
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
                            ) : filteredDepts.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="px-6 py-12 text-center text-text-secondary">
                                        No departments found matching your search.
                                    </td>
                                </tr>
                            ) : (
                                filteredDepts.map((dept) => (
                                    <tr key={dept.id} className="hover:bg-background-tertiary transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="flex flex-col">
                                                <span className="font-bold text-text-primary">{dept.name}</span>
                                                <span className="text-xs text-text-muted font-mono">{dept.code}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="text-sm font-medium tabular-nums">
                                                {typeof dept.course_count === 'number'
                                                    ? `${dept.course_count} active course${dept.course_count === 1 ? '' : 's'}`
                                                    : '—'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <button
                                                onClick={() => handleToggle(dept.id)}
                                                aria-label={dept.is_active ? `Deactivate department "${dept.name}"` : `Activate department "${dept.name}"`}
                                                className={`flex items-center gap-1 text-xs font-semibold transition-colors ${dept.is_active ? 'text-success-light' : 'text-text-muted'}`}
                                            >
                                                {dept.is_active ? (
                                                    <><ToggleRight className="w-5 h-5" /> Active</>
                                                ) : (
                                                    <><ToggleLeft className="w-5 h-5" /> Inactive</>
                                                )}
                                            </button>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex justify-end gap-2">
                                                <button
                                                    onClick={() => openModal(dept)}
                                                    className="p-2 text-blue-500 hover:bg-blue-500/10 rounded-md transition-colors"
                                                    title="Edit"
                                                    aria-label={`Edit department "${dept.name}"`}
                                                >
                                                    <Edit2 className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => openDeleteModal(dept)}
                                                    className="p-2 text-red-500 hover:bg-red-500/10 rounded-md transition-colors"
                                                    title="Delete"
                                                    aria-label={`Delete department "${dept.name}"`}
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

            {/* Modal */}
            <AdminModal
                isOpen={showModal}
                onClose={closeModal}
                title={editingDept ? 'Edit Department' : 'Create New Department'}
                maxWidth="lg"
            >
                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            <div className="grid grid-cols-3 gap-4">
                                <div className="col-span-2">
                                    <label className="label">Department Name *</label>
                                    <input
                                        type="text"
                                        required
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                        placeholder="e.g. Computer Science"
                                        className="input"
                                    />
                                </div>
                                <div>
                                    <label className="label">Code *</label>
                                    <input
                                        type="text"
                                        required
                                        value={formData.code}
                                        onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                                        placeholder="e.g. CS"
                                        className="input"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="label">Description (Optional)</label>
                                <textarea
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    placeholder="Brief details about this department..."
                                    rows={3}
                                    className="input resize-none"
                                />
                            </div>

                            {error && (
                                <div className="flex items-center gap-2 p-3 bg-danger/10 border border-danger/30 rounded-md text-danger text-sm">
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
                                    {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : editingDept ? 'Save Changes' : 'Create Department'}
                                </button>
                            </div>
                        </form>
            </AdminModal>

            {/* HIGH-004: Type-to-confirm delete modal */}
            <ConfirmDeleteModal
                isOpen={deleteModal.isOpen}
                onClose={() => setDeleteModal({ isOpen: false, dept: null })}
                onConfirm={handleDelete}
                title="Delete Department"
                itemName={deleteModal.dept?.name || ''}
                itemType="department"
                cascadeWarning={deleteModal.dept?.course_count && deleteModal.dept.course_count > 0
                    ? `This will also delete ${deleteModal.dept.course_count} course(s) and all their resources!`
                    : undefined}
                cascadeCount={deleteModal.dept?.course_count}
            />
        </div>
    )
}

// CRITICAL-002: Wrap with AdminAuthGate to block render until auth resolved
export default function DepartmentsAdminPage() {
    return (
        <AdminAuthGate>
            <DepartmentsContent />
        </AdminAuthGate>
    )
}
