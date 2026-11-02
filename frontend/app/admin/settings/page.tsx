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
    const [actionError, setActionError] = useState<string | null>(null)
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

    // The switch reflects moderation being enabled: checked = ON.
    const handleToggle = async () => {
        if (autoApprove === null) return
        const next = !autoApprove
        setSaving(true)
        setActionError(null)
        try {
            const response = await apiHelpers.setModerationAutoApprove(next)
            setAutoApprove(response.data.auto_approve_moderation)
        } catch {
            setActionError('Could not change the moderation setting. Nothing was saved — try again.')
        } finally {
            setSaving(false)
        }
    }

    const moderationOn = autoApprove === false

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
                        {moderationOn ? (
                            <ShieldCheck className="w-7 h-7 text-success-light shrink-0" />
                        ) : (
                            <ShieldAlert className="w-7 h-7 text-warning-light shrink-0" />
                        )}
                        <div>
                            <h2 className="text-lg font-bold text-text-primary">Upload Moderation</h2>
                            <p
                                className="text-sm text-text-secondary mt-1"
                                aria-live="polite"
                            >
                                {autoApprove === null
                                    ? 'Loading…'
                                    : moderationOn
                                        ? 'Moderation is ON — uploads by regular users wait in the moderation queue before appearing publicly.'
                                        : 'Moderation is OFF — uploads by regular users publish immediately, without review.'}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={handleToggle}
                        disabled={autoApprove === null || saving}
                        role="switch"
                        aria-checked={autoApprove === null ? undefined : moderationOn}
                        aria-label={moderationOn ? 'Turn moderation off (publish without review)' : 'Turn moderation on (queue uploads for review)'}
                        className={`flex items-center gap-1 text-sm font-semibold shrink-0 transition-colors disabled:opacity-50 ${moderationOn ? 'text-success-light' : 'text-warning-light'}`}
                    >
                        {(saving) ? (
                            <Loader2 className="w-6 h-6 animate-spin" />
                        ) : moderationOn ? (
                            <ToggleRight className="w-6 h-6" />
                        ) : (
                            <ToggleLeft className="w-6 h-6" />
                        )}
                        {autoApprove === null ? 'Loading…' : moderationOn ? 'Moderation ON' : 'Moderation OFF'}
                    </button>
                </div>

                {actionError && (
                    <div className="mt-4 flex gap-2 items-start p-3 bg-danger/10 border border-danger/30 rounded-md text-sm text-danger" role="alert">
                        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                        <span>{actionError}</span>
                    </div>
                )}

                {autoApprove && (
                    <div className="flex gap-2 items-start mt-4 p-3 bg-warning/10 border border-warning/30 rounded-md text-sm text-warning-light">
                        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                        <span>
                            Every regular upload publishes instantly without review while moderation is OFF. Trusted Contributor grants on the Users page make no difference for these uploads, and admins/moderators are always unaffected.
                        </span>
                    </div>
                )}

                <div className="flex gap-2 items-start mt-4 p-3 bg-background-secondary border border-border-subtle rounded-md text-sm text-text-secondary">
                    <Info className="w-4 h-4 shrink-0 mt-0.5 text-text-muted" />
                    <span>
                        Individual users can publish without review at any time via the per-user switch on the Users page — it is not tied to this global setting. Private uploads stay visible only to the uploader, and admin/moderator uploads always skip review.
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
