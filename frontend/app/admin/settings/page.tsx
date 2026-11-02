'use client'

import { useState, useEffect } from 'react'
import { ToggleLeft, ToggleRight, AlertTriangle, Loader2, ShieldCheck, ShieldAlert, Info } from 'lucide-react'
import { apiHelpers } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { AdminAuthGate } from '@/components/AuthGate'
import FetchError from '@/components/ui/FetchError'

function SettingsContent() {
    const { user, isAuthenticated } = useAuth()
    const [autoApprove, setAutoApprove] = useState<boolean | null>(null) // null = loading
    const [saving, setSaving] = useState(false)
    const [fetchError, setFetchError] = useState<string | null>(null)

    useEffect(() => {
        if (isAuthenticated && user?.role === 'admin') {
            fetchSetting()
        }
    }, [isAuthenticated, user])

    const fetchSetting = async () => {
        try {
            const response = await apiHelpers.getModerationSetting()
            setAutoApprove(response.data.auto_approve_moderation)
            setFetchError(null)
        } catch (error) {
            console.error('Failed to fetch moderation setting:', error)
            setFetchError('Failed to load the moderation setting. Check that the backend is running.')
        }
    }

    const handleToggle = async () => {
        if (autoApprove === null) return
        const next = !autoApprove
        setSaving(true)
        try {
            const response = await apiHelpers.setModerationAutoApprove(next)
            setAutoApprove(response.data.auto_approve_moderation)
        } catch {
            alert('Failed to update moderation setting')
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="container-custom py-8">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-text-primary">Site Settings</h1>
                <p className="text-text-secondary">Global policies for the whole library</p>
            </div>

            {fetchError && (
                <FetchError message={fetchError} onRetry={fetchSetting} className="mb-6" />
            )}

            <div className="card p-6 border border-border-subtle">
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                    <div className="flex gap-3">
                        {autoApprove ? (
                            <ShieldAlert className="w-7 h-7 text-yellow-500 shrink-0" />
                        ) : (
                            <ShieldCheck className="w-7 h-7 text-success-light shrink-0" />
                        )}
                        <div>
                            <h2 className="text-lg font-bold text-text-primary">Upload Moderation</h2>
                            <p className="text-sm text-text-secondary mt-1">
                                {autoApprove === null
                                    ? 'Loading…'
                                    : autoApprove
                                        ? 'OFF — anyone can upload and content is published immediately, without review.'
                                        : 'ON — uploads by regular users go to the moderation queue for review before appearing publicly.'}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={handleToggle}
                        disabled={autoApprove === null || saving}
                        className={`flex items-center gap-1 text-sm font-semibold shrink-0 transition-colors disabled:opacity-50 ${autoApprove ? 'text-success-light' : 'text-text-muted'}`}
                        aria-label={autoApprove ? 'Disable auto-approval (enable moderation)' : 'Enable auto-approval (disable moderation)'}
                    >
                        {(saving) ? (
                            <Loader2 className="w-6 h-6 animate-spin" />
                        ) : autoApprove ? (
                            <ToggleRight className="w-6 h-6" />
                        ) : (
                            <ToggleLeft className="w-6 h-6" />
                        )}
                        {autoApprove ? 'Review before publishing' : 'Publish immediately'}
                    </button>
                </div>

                {autoApprove && (
                    <div className="flex gap-2 items-start mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-md text-sm text-yellow-500">
                        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                        <span>
                            Public uploads appear instantly for all users. Individual trusted users can still be handled per-user on the Users page, and admins/moderators are unaffected either way.
                        </span>
                    </div>
                )}

                <div className="flex gap-2 items-start mt-4 p-3 bg-background-secondary border border-border-subtle rounded-md text-sm text-text-secondary">
                    <Info className="w-4 h-4 shrink-0 mt-0.5 text-text-muted" />
                    <span>
                        When publishing immediately is enabled, every non-private upload by any user skips the queue. Private uploads are unaffected (only the uploader can see them), and admin/moderator uploads have always bypassed review.
                    </span>
                </div>
            </div>
        </div>
    )
}

export default function SettingsAdminPage() {
    return (
        <AdminAuthGate>
            <SettingsContent />
        </AdminAuthGate>
    )
}
