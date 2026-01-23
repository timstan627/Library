'use client'

import { useState, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { Settings, User, Shield, Key, Bell, Trash2, AlertCircle, CheckCircle } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api } from '@/lib/api'

export default function SettingsPage() {
    const router = useRouter()
    const pathname = usePathname()
    const { user, isAuthenticated, isLoading, refreshUser } = useAuth()

    const [activeTab, setActiveTab] = useState('profile')
    const [loading, setLoading] = useState(false)
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

    // Profile form
    const [displayName, setDisplayName] = useState('')

    // Password form
    const [currentPassword, setCurrentPassword] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')

    // MFA
    const [mfaSecret, setMfaSecret] = useState('')
    const [mfaQr, setMfaQr] = useState('')
    const [mfaCode, setMfaCode] = useState('')

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push(`/auth/login?returnUrl=${encodeURIComponent(pathname)}`)
        }
    }, [isLoading, isAuthenticated, router, pathname])

    useEffect(() => {
        if (user) {
            setDisplayName(user.display_name || '')
        }
    }, [user])

    const handleProfileUpdate = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        setMessage(null)

        try {
            await api.put('/users/me', { display_name: displayName })
            await refreshUser()
            setMessage({ type: 'success', text: 'Profile updated successfully' })
        } catch (err: any) {
            setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to update profile' })
        } finally {
            setLoading(false)
        }
    }

    const handlePasswordChange = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        setMessage(null)

        if (newPassword !== confirmPassword) {
            setMessage({ type: 'error', text: 'Passwords do not match' })
            setLoading(false)
            return
        }

        try {
            await api.post('/users/me/change-password', {
                current_password: currentPassword,
                new_password: newPassword,
            })
            setMessage({ type: 'success', text: 'Password changed successfully' })
            setCurrentPassword('')
            setNewPassword('')
            setConfirmPassword('')
        } catch (err: any) {
            setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to change password' })
        } finally {
            setLoading(false)
        }
    }

    const handleSetupMfa = async () => {
        setLoading(true)
        setMessage(null)

        try {
            const response = await api.post('/auth/setup-mfa')
            setMfaSecret(response.data.secret)
            setMfaQr(response.data.qr_code_base64)
        } catch (err: any) {
            setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to setup MFA' })
        } finally {
            setLoading(false)
        }
    }

    const handleVerifyMfa = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        setMessage(null)

        try {
            await api.post('/auth/verify-mfa', { code: mfaCode })
            await refreshUser()
            setMessage({ type: 'success', text: 'MFA enabled successfully' })
            setMfaSecret('')
            setMfaQr('')
            setMfaCode('')
        } catch (err: any) {
            setMessage({ type: 'error', text: err.response?.data?.detail || 'Invalid MFA code' })
        } finally {
            setLoading(false)
        }
    }

    const handleDisableMfa = async () => {
        const code = prompt('Enter your MFA code to disable:')
        if (!code) return

        setLoading(true)
        setMessage(null)

        try {
            await api.post('/auth/disable-mfa', { code })
            await refreshUser()
            setMessage({ type: 'success', text: 'MFA disabled successfully' })
        } catch (err: any) {
            setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to disable MFA' })
        } finally {
            setLoading(false)
        }
    }

    if (isLoading || !isAuthenticated) {
        return (
            <div className="container-custom py-20 text-center">
                <div className="animate-pulse">Loading...</div>
            </div>
        )
    }

    const tabs = [
        { id: 'profile', label: 'Profile', icon: User },
        { id: 'security', label: 'Security', icon: Shield },
        { id: 'mfa', label: 'Two-Factor Auth', icon: Key },
    ]

    return (
        <div className="container-custom py-8">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-3xl font-bold text-text-primary mb-2">Settings</h1>
                <p className="text-text-secondary mb-8">Manage your account settings and preferences</p>

                <div className="flex flex-col md:flex-row gap-6">
                    {/* Sidebar */}
                    <div className="md:w-48 shrink-0">
                        <nav className="space-y-1">
                            {tabs.map((tab) => (
                                <button
                                    key={tab.id}
                                    onClick={() => {
                                        setActiveTab(tab.id)
                                        setMessage(null)
                                    }}
                                    className={`w-full flex items-center gap-3 px-4 py-2 rounded-md text-left transition-colors ${activeTab === tab.id
                                        ? 'bg-accent-primary/10 text-accent-primary'
                                        : 'text-text-secondary hover:text-text-primary hover:bg-background-tertiary'
                                        }`}
                                >
                                    <tab.icon className="w-4 h-4" />
                                    {tab.label}
                                </button>
                            ))}
                        </nav>
                    </div>

                    {/* Content */}
                    <div className="flex-1">
                        {message && (
                            <div
                                className={`flex items-center gap-2 p-3 rounded-md mb-6 ${message.type === 'success'
                                    ? 'bg-green-500/10 border border-green-500/30'
                                    : 'bg-red-500/10 border border-red-500/30'
                                    }`}
                            >
                                {message.type === 'success' ? (
                                    <CheckCircle className="w-5 h-5 text-green-500" />
                                ) : (
                                    <AlertCircle className="w-5 h-5 text-red-500" />
                                )}
                                <span className={message.type === 'success' ? 'text-green-500' : 'text-red-500'}>
                                    {message.text}
                                </span>
                            </div>
                        )}

                        {/* Profile Tab */}
                        {activeTab === 'profile' && (
                            <div className="card p-6">
                                <h2 className="text-lg font-semibold text-text-primary mb-4">Profile Information</h2>
                                <form onSubmit={handleProfileUpdate} className="space-y-4">
                                    <div>
                                        <label className="label">Email</label>
                                        <input
                                            type="email"
                                            value={user?.email || ''}
                                            disabled
                                            className="input bg-background-tertiary cursor-not-allowed"
                                        />
                                        <p className="text-text-muted text-xs mt-1">Email cannot be changed</p>
                                    </div>
                                    <div>
                                        <label className="label">Display Name</label>
                                        <input
                                            type="text"
                                            value={displayName}
                                            onChange={(e) => setDisplayName(e.target.value)}
                                            placeholder="Your name"
                                            className="input"
                                        />
                                    </div>
                                    <button type="submit" disabled={loading} className="btn btn-primary disabled:opacity-50">
                                        {loading ? 'Saving...' : 'Save Changes'}
                                    </button>
                                </form>
                            </div>
                        )}

                        {/* Security Tab */}
                        {activeTab === 'security' && (
                            <div className="card p-6">
                                <h2 className="text-lg font-semibold text-text-primary mb-4">Change Password</h2>
                                <form onSubmit={handlePasswordChange} className="space-y-4">
                                    <div>
                                        <label className="label">Current Password</label>
                                        <input
                                            type="password"
                                            value={currentPassword}
                                            onChange={(e) => setCurrentPassword(e.target.value)}
                                            placeholder="••••••••"
                                            className="input"
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label className="label">New Password</label>
                                        <input
                                            type="password"
                                            value={newPassword}
                                            onChange={(e) => setNewPassword(e.target.value)}
                                            placeholder="••••••••"
                                            className="input"
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label className="label">Confirm New Password</label>
                                        <input
                                            type="password"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            placeholder="••••••••"
                                            className="input"
                                            required
                                        />
                                    </div>
                                    <button type="submit" disabled={loading} className="btn btn-primary disabled:opacity-50">
                                        {loading ? 'Changing...' : 'Change Password'}
                                    </button>
                                </form>
                            </div>
                        )}

                        {/* MFA Tab */}
                        {activeTab === 'mfa' && (
                            <div className="card p-6">
                                <h2 className="text-lg font-semibold text-text-primary mb-4">Two-Factor Authentication</h2>

                                {user?.mfa_enabled ? (
                                    <div>
                                        <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/30 rounded-md mb-4">
                                            <CheckCircle className="w-5 h-5 text-green-500" />
                                            <span className="text-green-500">MFA is enabled on your account</span>
                                        </div>
                                        <button
                                            onClick={handleDisableMfa}
                                            disabled={loading}
                                            className="btn btn-secondary text-red-500 hover:bg-red-500/10"
                                        >
                                            Disable MFA
                                        </button>
                                    </div>
                                ) : mfaQr ? (
                                    <form onSubmit={handleVerifyMfa} className="space-y-4">
                                        <p className="text-text-secondary">
                                            Scan this QR code with your authenticator app:
                                        </p>
                                        <div className="bg-white p-4 rounded-md inline-block">
                                            <img src={`data:image/png;base64,${mfaQr}`} alt="MFA QR Code" className="w-48 h-48" />
                                        </div>
                                        <p className="text-text-muted text-sm">
                                            Or enter this secret manually: <code className="text-accent-primary">{mfaSecret}</code>
                                        </p>
                                        <div>
                                            <label className="label">Enter 6-digit code from app</label>
                                            <input
                                                type="text"
                                                value={mfaCode}
                                                onChange={(e) => setMfaCode(e.target.value)}
                                                placeholder="123456"
                                                maxLength={6}
                                                className="input w-32"
                                                required
                                            />
                                        </div>
                                        <button type="submit" disabled={loading} className="btn btn-primary disabled:opacity-50">
                                            {loading ? 'Verifying...' : 'Verify & Enable'}
                                        </button>
                                    </form>
                                ) : (
                                    <div>
                                        <p className="text-text-secondary mb-4">
                                            Add an extra layer of security to your account by enabling two-factor authentication.
                                        </p>
                                        <button
                                            onClick={handleSetupMfa}
                                            disabled={loading}
                                            className="btn btn-primary disabled:opacity-50"
                                        >
                                            {loading ? 'Setting up...' : 'Setup MFA'}
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
