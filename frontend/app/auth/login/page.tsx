'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Mail, Lock, Eye, EyeOff, LogIn, AlertCircle } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { useFormStateMachine, useScrollPosition, useFocusOnMount } from '@/lib/hooks'
import { FormButton } from '@/components/ui/Button'

export default function LoginPage() {
    const router = useRouter()
    const { login, isAuthenticated, isLoading: authLoading } = useAuth()

    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [requiresMfa, setRequiresMfa] = useState(false)
    const [mfaCode, setMfaCode] = useState('')

    // State machine for form
    const formState = useFormStateMachine()

    // Focus and scroll management
    const emailRef = useRef<HTMLInputElement>(null)
    const passwordRef = useRef<HTMLInputElement>(null)
    const { scrollToTop } = useScrollPosition()

    // Redirect if already authenticated
    useEffect(() => {
        if (!authLoading && isAuthenticated) {
            router.replace('/')
        }
    }, [authLoading, isAuthenticated, router])

    // Focus first field on mount
    useEffect(() => {
        emailRef.current?.focus()
    }, [])

    // Clear error on input change
    const handleInputChange = (setter: (v: string) => void) => (e: React.ChangeEvent<HTMLInputElement>) => {
        if (formState.isError) {
            formState.transition('IDLE')
        }
        setter(e.target.value)
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        // Prevent double submission (state machine enforces this)
        if (formState.isLocked) return

        // Validate
        formState.transition('VALIDATING')

        if (!email.trim()) {
            formState.transition('ERROR', { error: 'Email is required' })
            emailRef.current?.focus()
            return
        }
        if (!password) {
            formState.transition('ERROR', { error: 'Password is required' })
            passwordRef.current?.focus()
            return
        }

        // Submit
        formState.transition('SUBMITTING')

        try {
            await login(email, password, mfaCode || undefined)
            formState.transition('SUCCESS')
            scrollToTop()

            // Check for returnUrl
            const searchParams = new URLSearchParams(window.location.search)
            const returnUrl = searchParams.get('returnUrl')
            if (returnUrl && returnUrl.startsWith('/')) {
                router.push(returnUrl)
            } else {
                router.push('/')
            }
        } catch (err: any) {
            if (err.message === 'MFA_REQUIRED') {
                setRequiresMfa(true)
                formState.transition('IDLE')
                return
            }

            const errorMessage = err.response?.data?.detail || err.message || 'Login failed'
            formState.transition('ERROR', { error: errorMessage })

            // Clear password on error, focus password field
            setPassword('')
            passwordRef.current?.focus()
        }
    }

    // Show loading while checking auth
    if (authLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }

    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-background-primary">
            {/* Background decoration */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-[-10%] right-[-5%] w-[500px] h-[500px] bg-accent-primary/5 rounded-full blur-[100px]" />
                <div className="absolute bottom-[-10%] left-[-5%] w-[500px] h-[500px] bg-accent-secondary/5 rounded-full blur-[100px]" />
            </div>

            <div className="w-full max-w-md relative z-10">
                <div className="card p-8">
                    {/* Header */}
                    <div className="text-center mb-8">
                        <div className="w-12 h-12 bg-accent-primary/10 rounded-xl flex items-center justify-center mx-auto mb-4">
                            <LogIn className="w-6 h-6 text-accent-primary" />
                        </div>
                        <h1 className="text-2xl font-bold text-text-primary">Welcome Back</h1>
                        <p className="text-text-secondary mt-2">Sign in to your account</p>
                    </div>

                    {/* Error Display */}
                    {formState.isError && formState.error && (
                        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3 animate-fade-in">
                            <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                            <p className="text-red-500 text-sm">{formState.error}</p>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
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
                                    disabled={formState.isLocked}
                                    autoComplete="email"
                                    aria-invalid={formState.isError && !email}
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
                                    ref={passwordRef}
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={handleInputChange(setPassword)}
                                    placeholder="••••••••"
                                    className="input pl-10 pr-10 w-full"
                                    disabled={formState.isLocked}
                                    autoComplete="current-password"
                                    aria-invalid={formState.isError && !password}
                                    required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors"
                                    tabIndex={-1}
                                    disabled={formState.isLocked}
                                >
                                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>
                        </div>

                        {/* MFA Code (conditional) */}
                        {requiresMfa && (
                            <div className="animate-fade-in">
                                <label htmlFor="mfa" className="block text-sm font-medium text-text-secondary mb-1">
                                    2FA Code
                                </label>
                                <input
                                    id="mfa"
                                    type="text"
                                    value={mfaCode}
                                    onChange={handleInputChange(setMfaCode)}
                                    placeholder="123456"
                                    className="input w-full text-center tracking-widest text-lg"
                                    disabled={formState.isLocked}
                                    maxLength={6}
                                    pattern="[0-9]{6}"
                                    autoComplete="one-time-code"
                                />
                            </div>
                        )}

                        {/* Forgot Password Link */}
                        <div className="text-right">
                            <Link
                                href="/auth/forgot-password"
                                className={`text-sm text-accent-light hover:text-accent-primary transition-colors ${formState.isLocked ? 'pointer-events-none opacity-50' : ''}`}
                                tabIndex={formState.isLocked ? -1 : 0}
                            >
                                Forgot password?
                            </Link>
                        </div>

                        {/* Submit Button */}
                        <FormButton
                            isLoading={formState.isSubmitting}
                            isSuccess={formState.isSuccess}
                            loadingText="Signing in..."
                            successText="Success!"
                            fullWidth
                            className="py-3"
                        >
                            Sign In
                        </FormButton>
                    </form>

                    {/* Register Link */}
                    <div className="mt-6 pt-6 border-t border-border-subtle text-center">
                        <p className="text-text-secondary">
                            Don't have an account?{' '}
                            <Link
                                href="/auth/register"
                                className={`text-accent-light hover:text-accent-primary font-medium transition-colors ${formState.isLocked ? 'pointer-events-none opacity-50' : ''}`}
                                tabIndex={formState.isLocked ? -1 : 0}
                            >
                                Create one
                            </Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
