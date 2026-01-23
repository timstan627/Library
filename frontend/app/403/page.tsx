'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { ShieldX, Home, LogIn } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'

function ForbiddenContent() {
    const { isAuthenticated } = useAuth()
    const searchParams = useSearchParams()
    const returnUrl = searchParams.get('returnUrl') || '/'

    return (
        <div className="container-custom py-20 text-center">
            <div className="max-w-md mx-auto">
                <div className="w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                    <ShieldX className="w-10 h-10 text-red-500" />
                </div>

                <h1 className="text-4xl font-bold text-text-primary mb-4">
                    403 - Access Denied
                </h1>

                <p className="text-text-secondary mb-8">
                    You don't have permission to access this page.
                    {!isAuthenticated && ' Please log in with an authorized account.'}
                    {isAuthenticated && ' Your account does not have the required role.'}
                </p>

                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                    <Link href="/" className="btn btn-primary flex items-center justify-center gap-2">
                        <Home className="w-4 h-4" />
                        Go Home
                    </Link>
                    {!isAuthenticated && (
                        <Link
                            href={`/auth/login?returnUrl=${encodeURIComponent(returnUrl)}`}
                            className="btn btn-secondary flex items-center justify-center gap-2"
                        >
                            <LogIn className="w-4 h-4" />
                            Login
                        </Link>
                    )}
                </div>

                <p className="text-text-muted text-xs mt-8">
                    If you believe this is an error, please contact an administrator.
                </p>
            </div>
        </div>
    )
}

export default function ForbiddenPage() {
    return (
        <Suspense fallback={<div className="container-custom py-20 text-center text-text-muted">Loading...</div>}>
            <ForbiddenContent />
        </Suspense>
    )
}
