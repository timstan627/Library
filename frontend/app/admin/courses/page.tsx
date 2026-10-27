'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
    Plus, Edit2, Trash2, Search, AlertCircle, Loader2,
    BookOpen, Filter, ChevronRight, ChevronLeft
} from 'lucide-react'
import { apiHelpers } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { SkeletonTable } from '@/components/ui/Skeleton'
import { AdminAuthGate } from '@/components/AuthGate'
import { ConfirmDeleteModal } from '@/components/ui/ConfirmDeleteModal'
import FetchError from '@/components/ui/FetchError'

interface Course {
    id: string
    name: string
    code: string
    department_id: string
    department_name?: string
    description?: string
    is_active: boolean
}

interface Department {
    id: string
    name: string
    code: string
}

function CoursesContent() {
    const { user, isAuthenticated } = useAuth()
    const router = useRouter()

    const [courses, setCourses] = useState<Course[]>([])
    const [departments, setDepartments] = useState<Department[]>([])
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)

    // Filters
    const [selectedDeptId, setSelectedDeptId] = useState('')
    const [searchQuery, setSearchQuery] = useState('')

    // Modal states
    const [showModal, setShowModal] = useState(false)
    const [editingCourse, setEditingCourse] = useState<Course | null>(null)
    const [submitting, setSubmitting] = useState(false)
    const [formData, setFormData] = useState({
        name: '',
        code: '',
        department_id: '',
        description: ''
    })
    const [error, setError] = useState('')
    const [fetchError, setFetchError] = useState<string | null>(null)

    // Delete modal state
    const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; course: Course | null }>({
        isOpen: false,
        course: null
    })

    useEffect(() => {
        if (isAuthenticated && user?.role === 'admin') {
            fetchDepartments()
        }
    }, [isAuthenticated, user])

    useEffect(() => {
        if (isAuthenticated && user?.role === 'admin') {
            fetchCourses()
        }
    }, [isAuthenticated, user, page, selectedDeptId])

    const fetchDepartments = async () => {
        try {
            const response = await apiHelpers.getDepartmentsAdmin(1, 100)
            setDepartments(response.data.results)
            setFetchError(null)
        } catch (error) {
            console.error('Failed to fetch departments:', error)
            setFetchError('Failed to load departments. The list may not actually be empty.')
        }
    }

    const fetchCourses = async () => {
        setLoading(true)
        try {
            const response = await apiHelpers.getCoursesAdmin(
                selectedDeptId || undefined,
                page
            )
            setCourses(response.data.results)
            setTotalPages(Math.ceil(response.data.total / 20))
            setFetchError(null)
        } catch (error) {
            console.error('Failed to fetch courses:', error)
            setFetchError('Failed to load courses. The list may not actually be empty.')
        } finally {
            setLoading(false)
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setSubmitting(true)
        setError('')
        try {
            if (editingCourse) {
                await apiHelpers.updateCourse(editingCourse.id, formData)
            } else {
                await apiHelpers.createCourse(formData)
            }
            fetchCourses()
            closeModal()
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Operation failed')
        } finally {
            setSubmitting(false)
        }
    }

    // Open delete modal instead of using confirm()
    const openDeleteModal = (course: Course) => {
        setDeleteModal({ isOpen: true, course })
    }

    const handleDelete = async () => {
        if (!deleteModal.course) return
        await apiHelpers.deleteCourse(deleteModal.course.id)
        fetchCourses()
    }

    const openModal = (course: Course | null = null) => {
        if (course) {
            setEditingCourse(course)
            setFormData({
                name: course.name,
                code: course.code,
                department_id: course.department_id,
                description: course.description || ''
            })
        } else {
            setEditingCourse(null)
            setFormData({
                name: '',
                code: '',
                department_id: selectedDeptId || '',
                description: ''
            })
        }
        setShowModal(true)
    }

    const closeModal = () => {
        setShowModal(false)
        setEditingCourse(null)
        setFormData({ name: '', code: '', department_id: '', description: '' })
        setError('')
    }

    return (
        <div className="container-custom py-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-text-primary">Course Management</h1>
                    <p className="text-text-secondary">Manage academic courses and their associations</p>
                </div>
                <button
                    onClick={() => openModal()}
                    className="btn btn-primary flex items-center justify-center gap-2"
                >
                    <Plus className="w-5 h-5" />
                    New Course
                </button>
            </div>

            <div className="grid md:grid-cols-3 gap-4 mb-6">
                <div className="relative col-span-2">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                    <input
                        type="text"
                        placeholder="Search courses..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="input pl-10"
                    />
                </div>
                <div className="relative">
                    <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                    <select
                        value={selectedDeptId}
                        onChange={(e) => {
                            setSelectedDeptId(e.target.value)
                            setPage(1)
                        }}
                        className="input pl-10"
                    >
                        <option value="">All Departments</option>
                        {departments.map(d => (
                            <option key={d.id} value={d.id}>{d.name}</option>
                        ))}
                    </select>
                </div>
            </div>

            {fetchError && (
                <FetchError
                    message={fetchError}
                    onRetry={() => { fetchDepartments(); fetchCourses() }}
                    className="mb-6"
                />
            )}

            <div className="card shadow-md overflow-hidden border border-border-subtle">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-background-secondary border-b border-border-subtle">
                            <tr>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Course</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Department</th>
                                <th className="px-6 py-4 text-left text-xs font-medium text-text-muted">Status</th>
                                <th className="px-6 py-4 text-right text-xs font-medium text-text-muted">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border-subtle">
                            {loading ? (
                                [...Array(5)].map((_, i) => (
                                    <tr key={i}><td colSpan={4} className="px-6 py-4"><div className="h-6 bg-background-tertiary animate-pulse rounded" /></td></tr>
                                ))
                            ) : courses.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="px-6 py-12 text-center text-text-secondary">
                                        No courses found. Add one to get started!
                                    </td>
                                </tr>
                            ) : (
                                courses.map((course) => (
                                    <tr key={course.id} className="hover:bg-background-tertiary transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 bg-purple-500/10 rounded flex items-center justify-center">
                                                    <BookOpen className="w-4 h-4 text-purple-600" />
                                                </div>
                                                <div className="flex flex-col">
                                                    <span className="font-bold text-text-primary text-sm">{course.name}</span>
                                                    <span className="text-xs text-text-muted font-mono">{course.code}</span>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="text-sm text-text-secondary">{course.department_name || 'N/A'}</span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`text-xs font-semibold ${course.is_active ? 'text-success-light' : 'text-text-muted'}`}>
                                                {course.is_active ? 'Active' : 'Hidden'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex justify-end gap-2">
                                                <button
                                                    onClick={() => openModal(course)}
                                                    className="p-2 text-blue-500 hover:bg-blue-500/10 rounded-md transition-colors"
                                                    title="Edit"
                                                >
                                                    <Edit2 className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => openDeleteModal(course)}
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

                {totalPages > 1 && (
                    <div className="px-6 py-4 bg-background-secondary border-t border-border-subtle flex items-center justify-between">
                        <p className="text-sm text-text-secondary">Page {page} of {totalPages}</p>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="btn btn-secondary p-2 disabled:opacity-50"
                            >
                                <ChevronLeft className="w-4 h-4" />
                            </button>
                            <button
                                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                disabled={page === totalPages}
                                className="btn btn-secondary p-2 disabled:opacity-50"
                            >
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="card w-full max-w-lg p-0 animate-scale-in shadow-2xl overflow-hidden">
                        <div className="bg-background-secondary p-6 border-b border-border-subtle flex justify-between items-center">
                            <h2 className="text-xl font-bold text-text-primary">
                                {editingCourse ? 'Edit Course' : 'Create New Course'}
                            </h2>
                            <button onClick={closeModal} className="text-text-muted hover:text-text-primary">
                                <Plus className="w-6 h-6 rotate-45" />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            <div className="grid grid-cols-3 gap-4">
                                <div className="col-span-2">
                                    <label className="label">Course Name *</label>
                                    <input
                                        type="text"
                                        required
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                        placeholder="e.g. Data Structures"
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
                                        placeholder="e.g. CS201"
                                        className="input"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="label">Department *</label>
                                <select
                                    required
                                    value={formData.department_id}
                                    onChange={(e) => setFormData({ ...formData, department_id: e.target.value })}
                                    className="input"
                                >
                                    <option value="">Select Department</option>
                                    {departments.map(d => (
                                        <option key={d.id} value={d.id}>{d.name}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="label">Description (Optional)</label>
                                <textarea
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    placeholder="Brief course objectives..."
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
                                    {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : editingCourse ? 'Save Changes' : 'Create Course'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Type-to-confirm delete modal */}
            <ConfirmDeleteModal
                isOpen={deleteModal.isOpen}
                onClose={() => setDeleteModal({ isOpen: false, course: null })}
                onConfirm={handleDelete}
                title="Delete Course"
                itemName={deleteModal.course?.name || ''}
                itemType="course"
                cascadeWarning="This will also delete all resources associated with this course!"
            />
        </div>
    )
}

// Wrapper with AdminAuthGate
export default function CoursesAdminPage() {
    return (
        <AdminAuthGate>
            <CoursesContent />
        </AdminAuthGate>
    )
}
