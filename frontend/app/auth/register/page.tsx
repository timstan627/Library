'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Mail, Lock, Eye, EyeOff, UserPlus, AlertCircle, CheckCircle, User } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { useAsyncAction } from '@/lib/hooks/useAsyncAction'
import { FormButton } from '@/components/ui/Button'

export default function RegisterPage() {
    const router = useRouter()
    const { register, isAuthenticated, isLoading: authLoading } = useAuth()

    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [displayName, setDisplayName] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [success, setSuccess] = useState(false)

    const emailRef = useRef<HTMLInputElement>(null)

    const { isLoading, isError, error, execute, reset } = useAsyncAction({
        timeout: 15000,
        onSuccess: () => {
            setSuccess(true)
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

    // Redirect if authenticated
    useEffect(() => {
        if (!authLoading && isAuthenticated) {
            router.replace('/')
        }
    }, [authLoading, isAuthenticated, router])

    // Focus first field
    useEffect(() => {
        emailRef.current?.focus()
    }, [])

    // Clear error on input change
    const handleInputChange = (setter: (v: string) => void) => (e: React.ChangeEvent<HTMLInputElement>) => {
        if (isError) reset()
        setter(e.target.value)
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!allRequirementsMet) return

        await execute(async () => {
            await register(email, password, displayName || undefined)
        })
    }

    const isFormDisabled = isLoading

    if (authLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }

    // Success state
    if (success) {
        return (
            <div className="min-h-screen flex items-center justify-center p-4 bg-background-primary">
                <div className="w-full max-w-md">
                    <div className="card p-8 text-center animate-fade-in">
                        <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                            <CheckCircle className="w-8 h-8 text-green-500" />
                        </div>
                        <h2 className="text-2xl font-bold text-text-primary mb-2">Account Created!</h2>
                        <p className="text-text-secondary mb-6">
                            Your account has been created successfully. You can now sign in.
                        </p>
                        <Link href="/auth/login" className="btn btn-primary w-full py-3 inline-flex justify-center">
                            Sign In
                        </Link>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-background-primary">
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-[-10%] right-[-5%] w-[500px] h-[500px] bg-accent-primary/5 rounded-full blur-[100px]" />
                <div className="absolute bottom-[-10%] left-[-5%] w-[500px] h-[500px] bg-accent-secondary/5 rounded-full blur-[100px]" />
            </div>

            <div className="w-full max-w-md relative z-10">
                <div className="card p-8">
                    <div className="text-center mb-8">
                        <div className="w-12 h-12 bg-accent-primary/10 rounded-xl flex items-center justify-center mx-auto mb-4">
                            <UserPlus className="w-6 h-6 text-accent-primary" />
                        </div>
                        <h1 className="text-2xl font-bold text-text-primary">Create Account</h1>
                        <p className="text-text-secondary mt-2">Join the student community</p>
                    </div>

                    {isError && error && (
                        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3 animate-fade-in">
                            <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                            <p className="text-red-500 text-sm">{error}</p>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {/* Display Name */}
                        <div>
                            <label htmlFor="displayName" className="block text-sm font-medium text-text-secondary mb-1">
                                Display Name <span className="text-text-muted">(optional)</span>
                            </label>
                            <div className="relative">
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                                <input
                                    id="displayName"
                                    type="text"
                                    value={displayName}
                                    onChange={handleInputChange(setDisplayName)}
                                    placeholder="John Doe"
                                    className="input pl-10 w-full"
                                    disabled={isFormDisabled}
                                />
                            </div>
                        </div>

                        {/* Email */}
                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-text-secondary mb-1">
                                Email
                            </label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                                <input
                                    ref={emailRef}
                                    id="email"
                                    type="email"
                                    value={email}
                                    onChange={handleInputChange(setEmail)}
                                    placeholder="you@example.com"
                                    className="input pl-10 w-full"
                                    disabled={isFormDisabled}
                                    autoComplete="email"
                                    required
                                />
                            </div>
                        </div>

                        {/* Password */}
                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-text-secondary mb-1">
                                Password
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                                <input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={handleInputChange(setPassword)}
                                    placeholder="••••••••"
                                    className="input pl-10 pr-10 w-full"
                                    disabled={isFormDisabled}
                                    autoComplete="new-password"
                                    required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary"
                                    tabIndex={-1}
                                    disabled={isFormDisabled}
                                >
                                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
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
                            loadingText="Creating account..."
                            disabled={!allRequirementsMet}
                            fullWidth
                            className="py-3"
                        >
                            Create Account
                        </FormButton>
                    </form>

                    <div className="mt-6 pt-6 border-t border-border-subtle text-center">
                        <p className="text-text-secondary">
                            Already have an account?{' '}
                            <Link
                                href="/auth/login"
                                className={`text-accent-light hover:text-accent-primary font-medium ${isFormDisabled ? 'pointer-events-none opacity-50' : ''}`}
                                tabIndex={isFormDisabled ? -1 : 0}
                            >
                                Sign in
                            </Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
