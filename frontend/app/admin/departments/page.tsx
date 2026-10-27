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
        } catch (error) {
            console.error('Failed to fetch departments:', error)
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
            alert('Failed to toggle department status')
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

            <div className="card shadow-md overflow-hidden border border-border-subtle">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-background-secondary border-b border-border-subtle">
                            <tr>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Department</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Courses</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Status</th>
                                <th className="px-6 py-4 text-right text-xs font-medium text-text-muted">Actions</th>
                            </tr>
                        </thead>
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
                                            <span className="text-sm font-medium">{dept.course_count} active courses</span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <button
                                                onClick={() => handleToggle(dept.id)}
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
                                                >
                                                    <Edit2 className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => openDeleteModal(dept)}
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

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="card w-full max-w-lg p-0 animate-scale-in shadow-2xl overflow-hidden">
                        <div className="bg-background-secondary p-6 border-b border-border-subtle flex justify-between items-center">
                            <h2 className="text-xl font-bold text-text-primary">
                                {editingDept ? 'Edit Department' : 'Create New Department'}
                            </h2>
                            <button onClick={closeModal} className="text-text-muted hover:text-text-primary">
                                <Plus className="w-6 h-6 rotate-45" />
                            </button>
                        </div>

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
                                    {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : editingDept ? 'Save Changes' : 'Create Department'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

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
