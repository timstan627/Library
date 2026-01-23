'use client'

import { ReactNode } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { Loader2 } from 'lucide-react'

interface AuthGateProps {
    children: ReactNode
    requireAuth?: boolean
    requireAdmin?: boolean
    requireModerator?: boolean
    fallbackPath?: string
}

/**
 * CRITICAL-002: Auth Gate Component
 * 
 * This component BLOCKS rendering until auth state is resolved.
 * It prevents any protected UI from flashing before redirect.
 * 
 * Usage:
 *   <AuthGate requireAdmin>
 *     <AdminPage />
 *   </AuthGate>
 */
export function AuthGate({
    children,
    requireAuth = false,
    requireAdmin = false,
    requireModerator = false,
    fallbackPath = '/auth/login'
}: AuthGateProps) {
    const { user, isAuthenticated, isLoading } = useAuth()
    const router = useRouter()
    const pathname = usePathname()

    // BLOCK render during auth resolution - show full-page spinner
    if (isLoading) {
        return (
            <div className="fixed inset-0 flex items-center justify-center bg-background z-50">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 text-accent-primary animate-spin mx-auto mb-4" />
                    <p className="text-text-secondary text-sm">Verifying access...</p>
                </div>
            </div>
        )
    }

    // Check authentication
    if (requireAuth || requireAdmin || requireModerator) {
        if (!isAuthenticated) {
            // Redirect to login, NEVER render children
            const redirectUrl = `${fallbackPath}?returnUrl=${encodeURIComponent(pathname)}`
            router.replace(redirectUrl)
            return (
                <div className="fixed inset-0 flex items-center justify-center bg-background z-50">
                    <div className="text-center">
                        <Loader2 className="w-12 h-12 text-accent-primary animate-spin mx-auto mb-4" />
                        <p className="text-text-secondary text-sm">Redirecting to login...</p>
                    </div>
                </div>
            )
        }
    }

    // Check admin role
    if (requireAdmin) {
        if (user?.role !== 'admin') {
            router.replace(`/403?returnUrl=${encodeURIComponent(pathname)}`)
            return (
                <div className="fixed inset-0 flex items-center justify-center bg-background z-50">
                    <div className="text-center">
                        <Loader2 className="w-12 h-12 text-accent-primary animate-spin mx-auto mb-4" />
                        <p className="text-text-secondary text-sm">Access denied...</p>
                    </div>
                </div>
            )
        }
    }

    // Check moderator role (admin also passes)
    if (requireModerator) {
        if (user?.role !== 'admin' && user?.role !== 'moderator') {
            router.replace(`/403?returnUrl=${encodeURIComponent(pathname)}`)
            return (
                <div className="fixed inset-0 flex items-center justify-center bg-background z-50">
                    <div className="text-center">
                        <Loader2 className="w-12 h-12 text-accent-primary animate-spin mx-auto mb-4" />
                        <p className="text-text-secondary text-sm">Access denied...</p>
                    </div>
                </div>
            )
        }
    }

    // All checks passed - render children
    return <>{children}</>
}

/**
 * Convenience wrapper for admin-only pages
 */
export function AdminAuthGate({ children }: { children: ReactNode }) {
    return (
        <AuthGate requireAdmin fallbackPath="/403">
            {children}
        </AuthGate>
    )
}

/**
 * Convenience wrapper for moderator-or-admin pages
 */
export function ModeratorAuthGate({ children }: { children: ReactNode }) {
    return (
        <AuthGate requireModerator fallbackPath="/403">
            {children}
        </AuthGate>
    )
}

/**
 * Convenience wrapper for any authenticated user
 */
export function ProtectedAuthGate({ children }: { children: ReactNode }) {
    return (
        <AuthGate requireAuth fallbackPath="/auth/login">
            {children}
        </AuthGate>
    )
}
