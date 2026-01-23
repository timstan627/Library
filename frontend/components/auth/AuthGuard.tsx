'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'

interface AuthGuardProps {
    children: React.ReactNode
    requireAuth?: boolean
    requireRole?: 'admin' | 'moderator' | 'trusted' | 'user'
    redirectTo?: string
}

/**
 * Route guard component that handles authentication and authorization.
 * 
 * Features:
 * - Redirects unauthenticated users to login
 * - Redirects authenticated users away from auth pages
 * - Role-based access control
 * - Prevents back button from exposing protected routes
 */
export function AuthGuard({
    children,
    requireAuth = true,
    requireRole,
    redirectTo,
}: AuthGuardProps) {
    const router = useRouter()
    const pathname = usePathname()
    const { user, isAuthenticated, isLoading } = useAuth()

    useEffect(() => {
        if (isLoading) return

        // Auth pages should not be accessible when logged in
        const isAuthPage = pathname?.startsWith('/auth/')

        if (isAuthPage && isAuthenticated) {
            // Redirect authenticated users away from auth pages
            router.replace(redirectTo || '/')
            return
        }

        if (requireAuth && !isAuthenticated) {
            // Redirect to login with return URL
            const returnUrl = encodeURIComponent(pathname || '/')
            router.replace(`/auth/login?returnUrl=${returnUrl}`)
            return
        }

        // Role check
        if (requireRole && user) {
            const roleHierarchy: Record<string, number> = {
                admin: 4,
                moderator: 3,
                trusted: 2,
                user: 1,
            }

            const userRoleLevel = roleHierarchy[user.role] || 0
            const requiredRoleLevel = roleHierarchy[requireRole] || 0

            if (userRoleLevel < requiredRoleLevel) {
                router.replace('/')
                return
            }
        }
    }, [isLoading, isAuthenticated, user, pathname, requireAuth, requireRole, redirectTo, router])

    // Show loading spinner while checking auth
    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background-primary">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-3 border-accent-primary border-t-transparent rounded-full animate-spin" />
                    <p className="text-text-muted text-sm">Loading...</p>
                </div>
            </div>
        )
    }

    // Don't render protected content if not authorized
    if (requireAuth && !isAuthenticated) {
        return null
    }

    // Don't render role-restricted content if insufficient role
    if (requireRole && user) {
        const roleHierarchy: Record<string, number> = {
            admin: 4,
            moderator: 3,
            trusted: 2,
            user: 1,
        }

        const userRoleLevel = roleHierarchy[user.role] || 0
        const requiredRoleLevel = roleHierarchy[requireRole] || 0

        if (userRoleLevel < requiredRoleLevel) {
            return null
        }
    }

    return <>{children}</>
}

/**
 * HOC for protecting pages that require authentication
 */
export function withAuth<P extends object>(
    Component: React.ComponentType<P>,
    options?: Omit<AuthGuardProps, 'children'>
) {
    return function ProtectedPage(props: P) {
        return (
            <AuthGuard {...options}>
                <Component {...props} />
            </AuthGuard>
        )
    }
}

/**
 * Hook for checking if navigation to a route is allowed
 */
export function useNavigationGuard() {
    const { isAuthenticated, user, isLoading } = useAuth()
    const pathname = usePathname()

    const canNavigateTo = (path: string, requiredRole?: string): boolean => {
        if (isLoading) return false

        // Auth pages
        if (path.startsWith('/auth/')) {
            return !isAuthenticated
        }

        // Protected pages
        const protectedPaths = ['/profile', '/settings', '/upload', '/admin']
        const isProtected = protectedPaths.some(p => path.startsWith(p))

        if (isProtected && !isAuthenticated) {
            return false
        }

        // Role check
        if (requiredRole && user) {
            const roleHierarchy: Record<string, number> = {
                admin: 4,
                moderator: 3,
                trusted: 2,
                user: 1,
            }

            const userRoleLevel = roleHierarchy[user.role] || 0
            const requiredRoleLevel = roleHierarchy[requiredRole] || 0

            return userRoleLevel >= requiredRoleLevel
        }

        return true
    }

    return {
        canNavigateTo,
        isLoading,
        currentPath: pathname,
    }
}
