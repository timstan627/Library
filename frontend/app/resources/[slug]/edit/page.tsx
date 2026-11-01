'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Save, Loader2, AlertCircle, CheckCircle, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

interface Resource {
    id: string
    title: string
    slug: string
    description: string | null
    course_code: string
    department: string | null
    semester: string | null
    branch: string | null
    tags: string[]
    visibility: string
    moderation_status: string
}

export default function EditResourcePage() {
    const router = useRouter()
    const params = useParams()
    const slug = params.slug as string
    const { user, isAuthenticated, isLoading: authLoading } = useAuth()

    const [resource, setResource] = useState<Resource | null>(null)
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState(false)

    // Form state
    const [title, setTitle] = useState('')
    const [description, setDescription] = useState('')
    const [visibility, setVisibility] = useState('public')
    const [tags, setTags] = useState('')

    // Check permissions
    const isAdmin = user?.role === 'admin' || user?.role === 'moderator'

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.replace('/auth/login')
            return
        }

        if (slug && isAuthenticated) {
            fetchResource()
        }
    }, [slug, authLoading, isAuthenticated])

    const fetchResource = async () => {
        try {
            setLoading(true)
            const response = await api.get(`/resources/slug/${slug}`)
            const data = response.data

            setResource(data)
            setTitle(data.title)
            setDescription(data.description || '')
            setVisibility(data.visibility)
            setTags((data.tags || []).join(', '))
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load resource')
        } finally {
            setLoading(false)
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (saving || !resource) return

        setSaving(true)
        setError(null)

        try {
            await api.put(`/resources/${resource.id}`, {
                title: title.trim(),
                description: description.trim() || null,
                visibility,
                tags: tags.split(',').map(t => t.trim()).filter(Boolean),
            })

            setSuccess(true)
            setTimeout(() => {
                router.push(`/resources/${slug}`)
            }, 1500)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update resource')
        } finally {
            setSaving(false)
        }
    }

    const handleDelete = async () => {
        if (!resource) return
        if (!confirm('Are you sure you want to delete this resource? This cannot be undone.')) return

        try {
            await api.delete(`/resources/${resource.id}`)
            router.push('/admin/resources')
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to delete resource')
        }
    }

    if (authLoading || loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-accent-primary" />
            </div>
        )
    }

    if (error && !resource) {
        return (
            <div className="container-custom py-8">
                <div className="max-w-xl mx-auto text-center">
                    <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <h1 className="text-2xl font-bold text-text-primary mb-2">Error</h1>
                    <p className="text-text-secondary mb-6">{error}</p>
                    <Link href="/admin/resources" className="btn btn-primary">
                        Back to Resources
                    </Link>
                </div>
            </div>
        )
    }

    if (!resource) return null

    return (
        <div className="container-custom py-8">
            <div className="max-w-2xl mx-auto">
                {/* Back Link */}
                <Link
                    href="/admin/resources"
                    className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary mb-6 transition-colors"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Resources
                </Link>

                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-text-primary">Edit Resource</h1>
                        <p className="text-text-secondary mt-1">{resource.slug}</p>
                    </div>
                    {isAdmin && (
                        <button
                            onClick={handleDelete}
                            className="btn btn-danger"
                        >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Delete
                        </button>
                    )}
                </div>

                {/* Success Message */}
                {success && (
                    <div className="mb-6 p-4 bg-green-500/10 border border-green-500/20 rounded-lg flex items-center gap-3 animate-fade-in">
                        <CheckCircle className="w-5 h-5 text-green-500" />
                        <p className="text-green-500">Resource updated successfully! Redirecting...</p>
                    </div>
                )}

                {/* Error Message */}
                {error && (
                    <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3 animate-fade-in">
                        <AlertCircle className="w-5 h-5 text-red-500" />
                        <p className="text-red-500">{error}</p>
                    </div>
                )}

                {/* Edit Form */}
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="card p-6 space-y-6">
                        {/* Title */}
                        <div>
                            <label htmlFor="title" className="label">Title *</label>
                            <input
                                id="title"
                                type="text"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                className="input"
                                required
                                disabled={saving}
                            />
                        </div>

                        {/* Description */}
                        <div>
                            <label htmlFor="description" className="label">Description</label>
                            <textarea
                                id="description"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                className="input resize-none"
                                rows={4}
                                disabled={saving}
                            />
                        </div>

                        {/* Tags */}
                        <div>
                            <label htmlFor="tags" className="label">Tags</label>
                            <input
                                id="tags"
                                type="text"
                                value={tags}
                                onChange={(e) => setTags(e.target.value)}
                                placeholder="Comma-separated tags"
                                className="input"
                                disabled={saving}
                            />
                        </div>

                        {/* Visibility */}
                        <div>
                            <label className="label">Visibility</label>
                            <div className="grid grid-cols-3 gap-3">
                                {['public', 'unlisted', 'private'].map(v => (
                                    <button
                                        key={v}
                                        type="button"
                                        onClick={() => setVisibility(v)}
                                        disabled={saving}
                                        className={`p-3 rounded-lg border text-center capitalize ${visibility === v
                                                ? 'border-accent-primary bg-accent-primary/10 text-accent-primary'
                                                : 'border-border-subtle text-text-secondary hover:border-border-medium'
                                            }`}
                                    >
                                        {v}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Non-editable Info */}
                        <div className="pt-4 border-t border-border-subtle space-y-2 text-sm text-text-muted">
                            {resource.course_code && <p><strong>Course:</strong> {resource.course_code}</p>}
                            <p><strong>Status:</strong> <span className={
                                resource.moderation_status === 'approved' ? 'text-green-500' :
                                    resource.moderation_status === 'pending' ? 'text-yellow-500' : 'text-red-500'
                            }>{resource.moderation_status}</span></p>
                        </div>
                    </div>

                    {/* Submit Button */}
                    <button
                        type="submit"
                        disabled={saving}
                        className="btn btn-primary w-full py-3 flex items-center justify-center gap-2"
                    >
                        {saving ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin" />
                                Saving...
                            </>
                        ) : (
                            <>
                                <Save className="w-5 h-5" />
                                Save Changes
                            </>
                        )}
                    </button>
                </form>
            </div>
        </div>
    )
}
