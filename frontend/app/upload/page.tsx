'use client'

import { useState, useCallback, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { api, apiHelpers } from '@/lib/api'
import { FileUploadWithPreview } from '@/components/ui/DropZone'
import { AlertCircle, CheckCircle, Loader2, Upload, ArrowLeft, Info } from 'lucide-react'
import Link from 'next/link'

interface Department {
    id: string
    name: string
}

interface Course {
    id: string
    name: string
    code: string
    semester: string | null
    department_id: string | null
    department_name: string | null
}

export default function UploadPage() {
    const router = useRouter()
    const { user, isAuthenticated, isLoading: authLoading } = useAuth()

    // Form state
    const [files, setFiles] = useState<File[]>([])
    const [title, setTitle] = useState('')
    const [description, setDescription] = useState('')
    const [selectedDepartment, setSelectedDepartment] = useState('')
    const [selectedCourse, setSelectedCourse] = useState('')
    const [semester, setSemester] = useState('')
    const [branch, setBranch] = useState('')
    const [tags, setTags] = useState('')
    const [visibility, setVisibility] = useState('public')
    const [password, setPassword] = useState('')

    // Data for dropdowns
    const [departments, setDepartments] = useState<Department[]>([])
    const [courses, setCourses] = useState<Course[]>([])
    const [loadingData, setLoadingData] = useState(true)
    const [loadingCourses, setLoadingCourses] = useState(false)

    // UI state
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({})
    const [uploadStage, setUploadStage] = useState('')
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState(false)
    const [uploadedResource, setUploadedResource] = useState<any>(null)

    // Check if user is trusted (admin/moderator/trusted - auto-approved)
    const isTrustedUploader = user && (user.role === 'admin' || user.role === 'moderator' || user.is_trusted)

    // Fetch departments on mount
    useEffect(() => {
        const fetchDepartments = async () => {
            try {
                setLoadingData(true)
                const deptRes = await api.get('/departments')
                setDepartments(deptRes.data || [])
            } catch (err) {
                console.error('Failed to fetch departments:', err)
            } finally {
                setLoadingData(false)
            }
        }
        fetchDepartments()
    }, [])

    // Fetch courses from API when department changes (server-side filtering)
    useEffect(() => {
        const fetchCourses = async () => {
            try {
                setLoadingCourses(true)
                setCourses([])
                setSelectedCourse('')

                // Use API's department_id parameter for server-side filtering
                const url = selectedDepartment
                    ? `/courses?department_id=${selectedDepartment}`
                    : '/courses'

                const courseRes = await api.get(url)
                setCourses(courseRes.data || [])
            } catch (err) {
                console.error('Failed to fetch courses:', err)
                setCourses([])
            } finally {
                setLoadingCourses(false)
            }
        }

        fetchCourses()
    }, [selectedDepartment])

    // Get selected course object
    const courseObj = courses.find(c => c.id === selectedCourse)

    // Redirect if not authenticated
    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.replace('/auth/login?returnUrl=/upload')
        }
    }, [authLoading, isAuthenticated, router])

    const handleFilesSelected = useCallback((newFiles: File[]) => {
        setFiles(newFiles)
        setError(null)
        if (!title && newFiles.length > 0) {
            const fileName = newFiles[0].name.replace(/\.[^/.]+$/, '')
            setTitle(fileName)
        }
    }, [title])

    const handleRemoveFile = useCallback((index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index))
    }, [])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        window.scrollTo({ top: 0, behavior: 'smooth' })

        if (isSubmitting) return

        // Validation
        if (files.length === 0) {
            setError('Please select a file to upload')
            return
        }
        if (!title.trim()) {
            setError('Title is required')
            return
        }
        if (!selectedDepartment) {
            setError('Please select a department')
            return
        }
        if (!selectedCourse) {
            setError('Please select a course')
            return
        }
        if (visibility === 'private' && !password) {
            setError('Password is required for private resources')
            return
        }

        setIsSubmitting(true)
        setError(null)

        try {
            const file = files[0]
            setUploadProgress({ [file.name]: 0 })
            setUploadStage('Preparing file...')

            const formData = new FormData()
            formData.append('file', file)
            formData.append('title', title.trim())
            formData.append('course_code', courseObj?.code || '')
            formData.append('visibility', visibility)

            if (description.trim()) formData.append('description', description.trim())
            if (selectedDepartment) {
                const deptName = departments.find(d => d.id === selectedDepartment)?.name
                if (deptName) formData.append('department', deptName)
            }
            if (semester.trim()) formData.append('semester', semester.trim())
            if (branch.trim()) formData.append('branch', branch.trim())
            if (tags.trim()) {
                formData.append('tags', tags.split(',').map(t => t.trim()).filter(Boolean).join(','))
            }
            if (visibility === 'private' && password) {
                formData.append('password', password)
            }

            // Upload stages with progress simulation
            const stages = [
                { progress: 10, text: 'Reading file...' },
                { progress: 25, text: 'Caching file locally...' },
                { progress: 40, text: 'Connecting to server...' },
                { progress: 55, text: 'Uploading to cloud storage...' },
                { progress: 70, text: 'Processing file...' },
                { progress: 85, text: 'Saving metadata...' },
                { progress: 95, text: 'Finalizing upload...' },
            ]

            let stageIndex = 0
            const progressInterval = setInterval(() => {
                if (stageIndex < stages.length) {
                    setUploadProgress({ [file.name]: stages[stageIndex].progress })
                    setUploadStage(stages[stageIndex].text)
                    stageIndex++
                }
            }, 400)

            const response = await apiHelpers.uploadResource(formData)

            clearInterval(progressInterval)
            setUploadProgress({ [file.name]: 100 })
            setUploadStage('Upload complete!')

            setUploadedResource(response.data)
            setSuccess(true)

        } catch (err: any) {
            const errorMessage = err.response?.data?.detail || 'Upload failed. Please try again.'
            setError(errorMessage)
            setUploadProgress({})
            setUploadStage('')
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleReset = () => {
        setFiles([])
        setTitle('')
        setDescription('')
        setSelectedDepartment('')
        setSelectedCourse('')
        setSemester('')
        setBranch('')
        setTags('')
        setVisibility('public')
        setPassword('')
        setSuccess(false)
        setUploadedResource(null)
        setUploadProgress({})
        setError(null)
    }

    if (authLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-accent-primary" />
            </div>
        )
    }

    if (!isAuthenticated) {
        return null
    }

    return (
        <div className="container-custom py-8">
            <div className="max-w-2xl mx-auto">
                {/* Back Link */}
                <Link
                    href="/"
                    className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary mb-6 transition-colors"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Home
                </Link>

                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 bg-accent-primary/10 rounded-lg flex items-center justify-center">
                            <Upload className="w-5 h-5 text-accent-primary" />
                        </div>
                        <h1 className="text-3xl font-bold text-text-primary">Upload Resource</h1>
                    </div>
                    <p className="text-text-secondary">
                        Share your notes, assignments, and study materials with fellow students.
                    </p>
                </div>

                {/* Success State */}
                {success && uploadedResource && (
                    <div className="card p-8 text-center animate-fade-in">
                        <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                            <CheckCircle className="w-8 h-8 text-green-500" />
                        </div>
                        <h2 className="text-2xl font-bold text-text-primary mb-2">Upload Successful!</h2>
                        <p className="text-text-secondary mb-2">
                            Your resource "{uploadedResource.title}" has been uploaded.
                        </p>
                        {uploadedResource.moderation_status === 'pending' ? (
                            <p className="text-sm text-yellow-500 mb-6">
                                ⏳ It will be available after admin approval.
                            </p>
                        ) : (
                            <p className="text-sm text-green-500 mb-6">
                                ✓ Auto-approved! Your resource is now live.
                            </p>
                        )}
                        <div className="flex gap-3 justify-center">
                            <Link
                                href={`/resources/${uploadedResource.slug}`}
                                className="btn btn-primary"
                            >
                                View Resource
                            </Link>
                            <button onClick={handleReset} className="btn btn-secondary">
                                Upload Another
                            </button>
                        </div>
                    </div>
                )}

                {/* Upload Form */}
                {!success && (
                    <form onSubmit={handleSubmit} className="space-y-6">
                        {/* Error Display */}
                        {error && (
                            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3 animate-fade-in">
                                <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                                <p className="text-red-500 text-sm">{error}</p>
                            </div>
                        )}

                        {/* File Upload */}
                        <div className="card p-6">
                            <label className="block text-sm font-medium text-text-secondary mb-3">
                                File <span className="text-red-500">*</span>
                            </label>
                            <FileUploadWithPreview
                                files={files}
                                onFilesSelected={handleFilesSelected}
                                onRemoveFile={handleRemoveFile}
                                uploadProgress={uploadProgress}
                                uploadStatus={uploadStage}
                                maxFiles={1}
                                maxSize={50 * 1024 * 1024}
                                accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.zip,.rar,.md"
                                disabled={isSubmitting}
                            />
                        </div>

                        {/* Title */}
                        <div>
                            <label htmlFor="title" className="label">
                                Title <span className="text-red-500">*</span>
                            </label>
                            <input
                                id="title"
                                type="text"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                placeholder="e.g., Data Structures Lecture Notes Week 5"
                                className="input"
                                disabled={isSubmitting}
                                required
                            />
                        </div>

                        {/* Department */}
                        <div>
                            <label htmlFor="department" className="label">
                                Department <span className="text-red-500">*</span>
                            </label>
                            <select
                                id="department"
                                value={selectedDepartment}
                                onChange={(e) => setSelectedDepartment(e.target.value)}
                                className="input"
                                disabled={isSubmitting || loadingData}
                                required
                            >
                                <option value="">Select a Department</option>
                                {departments.map(dept => (
                                    <option key={dept.id} value={dept.id}>{dept.name}</option>
                                ))}
                            </select>
                        </div>

                        {/* Course */}
                        <div>
                            <label htmlFor="course" className="label">
                                Course <span className="text-red-500">*</span>
                            </label>
                            <select
                                id="course"
                                value={selectedCourse}
                                onChange={(e) => setSelectedCourse(e.target.value)}
                                className="input"
                                disabled={isSubmitting || loadingData || loadingCourses}
                                required
                            >
                                <option value="">{loadingCourses ? 'Loading courses...' : 'Select a Course'}</option>
                                {courses.map((course: Course) => (
                                    <option key={course.id} value={course.id}>
                                        {course.code} - {course.name}
                                    </option>
                                ))}
                            </select>
                            {courseObj && (
                                <p className="text-xs text-text-muted mt-1">
                                    {courseObj.department_name && `Department: ${courseObj.department_name}`}
                                    {courseObj.semester && ` • Semester: ${courseObj.semester}`}
                                </p>
                            )}
                        </div>

                        {/* Semester */}
                        <div>
                            <label htmlFor="semester" className="label">
                                Semester
                            </label>
                            <select
                                id="semester"
                                value={semester}
                                onChange={(e) => setSemester(e.target.value)}
                                className="input"
                                disabled={isSubmitting}
                            >
                                <option value="">Select Semester (optional)</option>
                                <option value="1">Semester 1</option>
                                <option value="2">Semester 2</option>
                                <option value="3">Semester 3</option>
                                <option value="4">Semester 4</option>
                                <option value="5">Semester 5</option>
                                <option value="6">Semester 6</option>
                                <option value="7">Semester 7</option>
                                <option value="8">Semester 8</option>
                            </select>
                        </div>

                        {/* Branch */}
                        <div>
                            <label htmlFor="branch" className="label">
                                Branch / Specialization
                            </label>
                            <input
                                id="branch"
                                type="text"
                                value={branch}
                                onChange={(e) => setBranch(e.target.value)}
                                placeholder="e.g., Computer Science, Electrical Engineering"
                                className="input"
                                disabled={isSubmitting}
                            />
                        </div>

                        {/* Description */}
                        <div>
                            <label htmlFor="description" className="label">
                                Description
                            </label>
                            <textarea
                                id="description"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="Brief description of what this resource contains..."
                                rows={4}
                                className="input resize-none"
                                disabled={isSubmitting}
                            />
                        </div>

                        {/* Tags */}
                        <div>
                            <label htmlFor="tags" className="label">
                                Tags
                            </label>
                            <input
                                id="tags"
                                type="text"
                                value={tags}
                                onChange={(e) => setTags(e.target.value)}
                                placeholder="notes, exam, midterm, lecture (comma-separated)"
                                className="input"
                                disabled={isSubmitting}
                            />
                        </div>

                        {/* Visibility */}
                        <div>
                            <label className="label">Visibility</label>
                            <div className="grid grid-cols-3 gap-3">
                                {[
                                    { value: 'public', label: 'Public', desc: 'Anyone can find' },
                                    { value: 'unlisted', label: 'Unlisted', desc: 'Only with link' },
                                    { value: 'private', label: 'Private', desc: 'Password required' },
                                ].map(opt => (
                                    <button
                                        key={opt.value}
                                        type="button"
                                        onClick={() => setVisibility(opt.value)}
                                        disabled={isSubmitting}
                                        className={`
                                            p-3 rounded-lg border text-left transition-colors
                                            ${visibility === opt.value
                                                ? 'border-accent-primary bg-accent-primary/10'
                                                : 'border-border-subtle hover:border-border-medium'
                                            }
                                        `}
                                    >
                                        <p className="font-medium text-text-primary text-sm">{opt.label}</p>
                                        <p className="text-xs text-text-muted">{opt.desc}</p>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Password (for private) */}
                        {visibility === 'private' && (
                            <div className="animate-fade-in">
                                <label htmlFor="password" className="label">
                                    Access Password <span className="text-red-500">*</span>
                                </label>
                                <input
                                    id="password"
                                    type="text"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="Enter password for accessing this resource"
                                    className="input"
                                    disabled={isSubmitting}
                                    required
                                />
                                <p className="text-xs text-text-muted mt-1">
                                    Share this password with people you want to give access.
                                </p>
                            </div>
                        )}

                        {/* Moderation Notice */}
                        <div className="flex items-start gap-3 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                            <Info className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />
                            <p className="text-sm text-blue-400">
                                All uploads are reviewed by moderators before becoming publicly available.
                            </p>
                        </div>

                        {/* Submit Button */}
                        <button
                            type="submit"
                            disabled={isSubmitting || files.length === 0}
                            className={`
                                btn btn-primary w-full py-3 flex items-center justify-center gap-2
                                disabled:opacity-50 disabled:cursor-not-allowed
                            `}
                        >
                            {isSubmitting ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Uploading...
                                </>
                            ) : (
                                <>
                                    <Upload className="w-5 h-5" />
                                    Upload Resource
                                </>
                            )}
                        </button>

                        {/* Storage Info */}
                        {user && (
                            <p className="text-center text-xs text-text-muted">
                                {user.role === 'admin' ? (
                                    'Unlimited storage (Admin)'
                                ) : (
                                    `Storage: ${Math.round(user.storage_used_bytes / (1024 * 1024))} MB / ${user.storage_quota_bytes > 100 * 1024 * 1024 * 1024 ? 'Unlimited' : `${Math.round(user.storage_quota_bytes / (1024 * 1024))} MB`}`
                                )}
                            </p>
                        )}
                    </form>
                )}
            </div>
        </div>
    )
}
