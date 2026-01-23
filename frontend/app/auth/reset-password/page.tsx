'use client'

import { useState, useRef, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Key, Lock, CheckCircle, AlertCircle, ArrowLeft } from 'lucide-react'
import { api } from '@/lib/api'
import { useAsyncAction } from '@/lib/hooks/useAsyncAction'
import { FormButton } from '@/components/ui/Button'

function ResetPasswordForm() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const token = searchParams.get('token')

    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [success, setSuccess] = useState(false)

    const passwordRef = useRef<HTMLInputElement>(null)

    const { isLoading, isError, error, execute, reset } = useAsyncAction({
        timeout: 15000,
        onSuccess: () => {
            setSuccess(true)
            setTimeout(() => {
                router.push('/auth/login')
            }, 2000)
        },
    })

    // Password requirements
    const passwordRequirements = [
        { label: 'At least 8 characters', valid: password.length >= 8 },
        { label: 'One uppercase letter', valid: /[A-Z]/.test(password) },
        { label: 'One lowercase letter', valid: /[a-z]/.test(password) },
        { label: 'One number', valid: /\d/.test(password) },
        { label: 'Passwords match', valid: password.length > 0 && password === confirmPassword },
    ]

    const allRequirementsMet = passwordRequirements.every(r => r.valid)

    useEffect(() => {
        passwordRef.current?.focus()
    }, [])

    const handleInputChange = (setter: (v: string) => void) => (e: React.ChangeEvent<HTMLInputElement>) => {
        if (isError) reset()
        setter(e.target.value)
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!allRequirementsMet) return

        if (!token) {
            return
        }

        await execute(async () => {
            await api.post('/auth/reset-password', {
                token,
                new_password: password,
            })
        })
    }

    const isFormDisabled = isLoading

    // No token
    if (!token) {
        return (
            <div className="card p-8 text-center">
                <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-6" />
                <h2 className="text-2xl font-bold text-text-primary mb-2">Invalid Link</h2>
                <p className="text-text-secondary mb-6">
                    This password reset link is invalid or missing. Please request a new one.
                </p>
                <Link href="/auth/forgot-password" className="btn btn-primary w-full py-3 inline-flex justify-center">
                    Request New Link
                </Link>
            </div>
        )
    }

    // Success state
    if (success) {
        return (
            <div className="card p-8 text-center animate-fade-in">
                <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                    <CheckCircle className="w-8 h-8 text-green-500" />
                </div>
                <h2 className="text-2xl font-bold text-text-primary mb-2">Password Reset!</h2>
                <p className="text-text-secondary mb-6">
                    Your password has been updated successfully. Redirecting to login...
                </p>
                <Link href="/auth/login" className="btn btn-primary w-full py-3 inline-flex justify-center">
                    Go to Login
                </Link>
            </div>
        )
    }

    return (
        <div className="card p-8">
            <div className="text-center mb-8">
                <div className="w-12 h-12 bg-accent-primary/10 rounded-xl flex items-center justify-center mx-auto mb-4">
                    <Key className="w-6 h-6 text-accent-primary" />
                </div>
                <h1 className="text-2xl font-bold text-text-primary">Set New Password</h1>
                <p className="text-text-secondary mt-2">
                    Create a strong password for your account.
                </p>
            </div>

            {isError && error && (
                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3 animate-fade-in">
                    <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                    <p className="text-red-500 text-sm">{error}</p>
                </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
                {/* New Password */}
                <div>
                    <label htmlFor="password" className="block text-sm font-medium text-text-secondary mb-1">
                        New Password
                    </label>
                    <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                        <input
                            ref={passwordRef}
                            id="password"
                            type="password"
                            value={password}
                            onChange={handleInputChange(setPassword)}
                            placeholder="••••••••"
                            className="input pl-10 w-full"
                            disabled={isFormDisabled}
                            autoComplete="new-password"
                            required
                        />
                    </div>
                </div>

                {/* Confirm Password */}
                <div>
                    <label htmlFor="confirmPassword" className="block text-sm font-medium text-text-secondary mb-1">
                        Confirm Password
                    </label>
                    <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                        <input
                            id="confirmPassword"
                            type="password"
                            value={confirmPassword}
                            onChange={handleInputChange(setConfirmPassword)}
                            placeholder="••••••••"
                            className="input pl-10 w-full"
                            disabled={isFormDisabled}
                            autoComplete="new-password"
                            required
                        />
                    </div>
                </div>

                {/* Password Requirements */}
                <div className="space-y-1.5 py-2">
                    {passwordRequirements.map((req) => (
                        <div
                            key={req.label}
                            className={`flex items-center gap-2 text-xs transition-colors ${req.valid ? 'text-green-500' : 'text-text-muted'
                                }`}
                        >
                            <CheckCircle className="w-3.5 h-3.5" />
                            {req.label}
                        </div>
                    ))}
                </div>

                {/* Submit */}
                <FormButton
                    isLoading={isLoading}
                    loadingText="Updating password..."
                    disabled={!allRequirementsMet}
                    fullWidth
                    className="py-3"
                >
                    Reset Password
                </FormButton>
            </form>

            <div className="mt-6 pt-6 border-t border-border-subtle text-center">
                <Link
                    href="/auth/login"
                    className={`text-text-secondary hover:text-text-primary inline-flex items-center gap-2 ${isFormDisabled ? 'pointer-events-none opacity-50' : ''}`}
                    tabIndex={isFormDisabled ? -1 : 0}
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Login
                </Link>
            </div>
        </div>
    )
}

export default function ResetPasswordPage() {
    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-background-primary">
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-[-10%] right-[-5%] w-[500px] h-[500px] bg-accent-primary/5 rounded-full blur-[100px]" />
                <div className="absolute bottom-[-10%] left-[-5%] w-[500px] h-[500px] bg-accent-secondary/5 rounded-full blur-[100px]" />
            </div>

            <div className="w-full max-w-md relative z-10">
                <Suspense fallback={
                    <div className="flex items-center justify-center py-12">
                        <div className="w-8 h-8 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
                    </div>
                }>
                    <ResetPasswordForm />
                </Suspense>
            </div>
        </div>
    )
}
