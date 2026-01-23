'use client'

import { useState, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import {
    User, Settings, Upload, Download, Star, FileText,
    HardDrive, LogOut, Shield, Calendar
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { apiHelpers } from '@/lib/api'
import { SkeletonProfile } from '@/components/ui/Skeleton'

interface StorageInfo {
    quota_bytes: number
    used_bytes: number
    remaining_bytes: number
    usage_percent: number
    quota_mb: number
    used_mb: number
}

interface UserResource {
    id: string
    title: string
    slug: string
    course_code: string
    file_size: number
    downloads: number
    created_at: string
    uploader_name?: string
}

export default function ProfilePage() {
    const router = useRouter()
    const pathname = usePathname()
    const { user, isAuthenticated, isLoading, logout } = useAuth()

    const [storage, setStorage] = useState<StorageInfo | null>(null)
    const [resources, setResources] = useState<UserResource[]>([])
    const [loadingData, setLoadingData] = useState(true)

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push(`/auth/login?returnUrl=${encodeURIComponent(pathname)}`)
        }
    }, [isLoading, isAuthenticated, router, pathname])

    useEffect(() => {
        if (isAuthenticated) {
            fetchData()
        }
    }, [isAuthenticated])

    const fetchData = async () => {
        try {
            const [storageRes, resourcesRes] = await Promise.all([
                apiHelpers.getStorageInfo(),
                apiHelpers.getMyResources({ page: 1, size: 10 }),
            ])
            setStorage(storageRes.data)
            setResources(resourcesRes.data.results || [])
        } catch (error) {
            console.error('Failed to fetch profile data:', error)
        } finally {
            setLoadingData(false)
        }
    }

    const handleLogout = () => {
        logout()
        router.push('/')
    }

    if (isLoading || !isAuthenticated) {
        return (
            <div className="container-custom py-20">
                <SkeletonProfile />
            </div>
        )
    }

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
        })
    }

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    return (
        <div className="container-custom py-8">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="card p-6 mb-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="w-16 h-16 bg-accent-primary/10 rounded-full flex items-center justify-center">
                                <User className="w-8 h-8 text-accent-primary" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold text-text-primary">
                                    {user?.display_name || user?.email?.split('@')[0]}
                                </h1>
                                <p className="text-text-secondary">{user?.email}</p>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className="badge badge-primary text-xs capitalize">{user?.role}</span>
                                    {user?.mfa_enabled && (
                                        <span className="flex items-center gap-1 text-xs text-green-500">
                                            <Shield className="w-3 h-3" />
                                            MFA Enabled
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                        <div className="flex gap-2">
                            {user?.role === 'admin' && (
                                <Link
                                    href="/admin"
                                    className="btn bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:opacity-90 flex items-center shadow-md hover:shadow-lg transition-all transform hover:-translate-y-0.5"
                                >
                                    <Shield className="w-4 h-4 mr-2" />
                                    Admin Panel
                                </Link>
                            )}
                            <Link href="/settings" className="btn btn-secondary">
                                <Settings className="w-4 h-4 mr-2" />
                                Settings
                            </Link>
                            <button onClick={handleLogout} className="btn btn-ghost text-red-500">
                                <LogOut className="w-4 h-4 mr-2" />
                                Logout
                            </button>
                        </div>
                    </div>
                </div>

                <div className="grid md:grid-cols-3 gap-6 mb-6">
                    {/* Storage */}
                    <div className="card p-6">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 bg-accent-primary/10 rounded-lg flex items-center justify-center">
                                <HardDrive className="w-5 h-5 text-accent-primary" />
                            </div>
                            {storage && (
                                <div>
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-text-secondary">Storage Used</span>
                                        <span className="font-medium text-text-primary">
                                            {storage.used_mb.toFixed(1)} MB / Unlimited
                                        </span>
                                    </div>
                                    <div className="w-full h-2 bg-background-tertiary rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-accent-primary rounded-full transition-all duration-500"
                                            style={{ width: `${storage.used_bytes > 0 ? '5' : '0'}%` }}
                                        />
                                    </div>
                                    <p className="text-xs text-green-500 mt-2 flex items-center">
                                        <Shield className="w-3 h-3 mr-1" />
                                        Unlimited Storage
                                    </p>
                                </div>
                            )}
                            {!storage && (
                                <div>
                                    <p className="text-text-secondary text-sm">Storage Used</p>
                                    <p className="text-text-primary font-semibold">... / ...</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Uploads */}
                    <div className="card p-6">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center">
                                <Upload className="w-5 h-5 text-green-500" />
                            </div>
                            <div>
                                <p className="text-text-secondary text-sm">Total Uploads</p>
                                <p className="text-2xl font-bold text-text-primary">{resources.length}</p>
                            </div>
                        </div>
                    </div>

                    {/* Downloads */}
                    <div className="card p-6">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                                <Download className="w-5 h-5 text-blue-500" />
                            </div>
                            <div>
                                <p className="text-text-secondary text-sm">Total Downloads</p>
                                <p className="text-2xl font-bold text-text-primary">
                                    {resources.reduce((sum, r) => sum + r.downloads, 0)}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Your Resources */}
                <div className="card p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold text-text-primary">Your Uploads</h2>
                        <Link href="/upload" className="btn btn-primary text-sm">
                            <Upload className="w-4 h-4 mr-2" />
                            Upload New
                        </Link>
                    </div>

                    {loadingData ? (
                        <div className="animate-pulse space-y-3">
                            {[...Array(3)].map((_, i) => (
                                <div key={i} className="h-16 bg-background-tertiary rounded" />
                            ))}
                        </div>
                    ) : resources.length > 0 ? (
                        <div className="space-y-3">
                            {resources.map((resource) => (
                                <Link
                                    key={resource.id}
                                    href={`/resources/${resource.slug}`}
                                    className="flex items-center justify-between p-4 bg-background-tertiary rounded-md hover:bg-background-secondary transition-colors"
                                >
                                    <div className="flex items-center gap-3">
                                        <FileText className="w-5 h-5 text-text-muted" />
                                        <div>
                                            <p className="text-text-primary font-medium">{resource.title}</p>
                                            <p className="text-text-secondary text-sm">
                                                <span className="text-text-muted">Course:</span> {resource.course_code} • {formatFileSize(resource.file_size)}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-text-primary font-mono text-sm">
                                            {resource.downloads} downloads
                                        </p>
                                        <p className="text-text-muted text-xs">{formatDate(resource.created_at)}</p>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-12">
                            <FileText className="w-16 h-16 text-text-muted mx-auto mb-4" />
                            <p className="text-text-secondary mb-6">You haven't uploaded any resources yet</p>
                            <Link href="/upload" className="btn btn-primary inline-block">
                                Upload Your First Resource
                            </Link>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
