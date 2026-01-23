'use client'

import { useState } from 'react'
import { useParams, useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { Flag, ArrowLeft, AlertCircle, CheckCircle } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api } from '@/lib/api'

export default function ReportPage() {
    const params = useParams()
    const router = useRouter()
    const pathname = usePathname()
    const { isAuthenticated } = useAuth()
    const resourceId = params.id as string

    const [reason, setReason] = useState('')
    const [description, setDescription] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState(false)

    const reasons = [
        { value: 'copyright', label: 'Copyright Violation' },
        { value: 'inappropriate', label: 'Inappropriate Content' },
        { value: 'spam', label: 'Spam or Misleading' },
        { value: 'malware', label: 'Malware or Virus' },
        { value: 'other', label: 'Other' },
    ]

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!reason) {
            setError('Please select a reason')
            return
        }

        setLoading(true)
        setError('')

        try {
            await api.post('/reports', {
                resource_id: resourceId,
                reason,
                description,
            })
            setSuccess(true)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit report')
        } finally {
            setLoading(false)
        }
    }

    if (!isAuthenticated) {
        return (
            <div className="container-custom py-20 text-center">
                <Flag className="w-16 h-16 text-text-muted mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-text-primary mb-4">Login Required</h2>
                <p className="text-text-secondary mb-6">You need to be logged in to report content.</p>
                <Link
                    href={`/auth/login?returnUrl=${encodeURIComponent(pathname)}`}
                    className="btn btn-primary"
                >
                    Login
                </Link>
            </div>
        )
    }

    if (success) {
        return (
            <div className="container-custom py-20 text-center">
                <div className="card max-w-md mx-auto p-8">
                    <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                    <h2 className="text-2xl font-bold text-text-primary mb-2">Report Submitted</h2>
                    <p className="text-text-secondary mb-6">
                        Thank you for your report. Our moderators will review it shortly.
                    </p>
                    <button onClick={() => router.back()} className="btn btn-primary">
                        Go Back
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="container-custom py-8">
            <div className="max-w-lg mx-auto">
                <button
                    onClick={() => router.back()}
                    className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary mb-6"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back
                </button>

                <div className="card p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-10 h-10 bg-red-500/10 rounded-lg flex items-center justify-center">
                            <Flag className="w-5 h-5 text-red-500" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-text-primary">Report Content</h1>
                            <p className="text-text-secondary text-sm">Help us maintain quality</p>
                        </div>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="label">Reason *</label>
                            <div className="space-y-2">
                                {reasons.map((r) => (
                                    <label
                                        key={r.value}
                                        className={`flex items-center gap-3 p-3 rounded-md border cursor-pointer transition-colors ${reason === r.value
                                            ? 'border-accent-primary bg-accent-primary/5'
                                            : 'border-border-subtle hover:border-border-medium'
                                            }`}
                                    >
                                        <input
                                            type="radio"
                                            name="reason"
                                            value={r.value}
                                            checked={reason === r.value}
                                            onChange={(e) => setReason(e.target.value)}
                                            className="sr-only"
                                        />
                                        <div
                                            className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${reason === r.value
                                                ? 'border-accent-primary'
                                                : 'border-border-medium'
                                                }`}
                                        >
                                            {reason === r.value && (
                                                <div className="w-2 h-2 rounded-full bg-accent-primary" />
                                            )}
                                        </div>
                                        <span className="text-text-primary">{r.label}</span>
                                    </label>
                                ))}
                            </div>
                        </div>

                        <div>
                            <label className="label">Additional Details (optional)</label>
                            <textarea
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="Provide more context about this report..."
                                rows={4}
                                className="input resize-none"
                            />
                        </div>

                        {error && (
                            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-md">
                                <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
                                <p className="text-red-500 text-sm">{error}</p>
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="btn btn-primary w-full py-3 disabled:opacity-50"
                        >
                            {loading ? 'Submitting...' : 'Submit Report'}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    )
}
