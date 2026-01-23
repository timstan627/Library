'use client'

import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import { Mail, ArrowLeft, CheckCircle, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { useAsyncAction } from '@/lib/hooks/useAsyncAction'
import { FormButton } from '@/components/ui/Button'

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('')
    const [submitted, setSubmitted] = useState(false)

    const emailRef = useRef<HTMLInputElement>(null)

    const { isLoading, isError, error, execute, reset } = useAsyncAction({
        timeout: 15000,
        onSuccess: () => {
            setSubmitted(true)
        },
    })

    useEffect(() => {
        emailRef.current?.focus()
    }, [])

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (isError) reset()
        setEmail(e.target.value)
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!email.trim()) {
            emailRef.current?.focus()
            return
        }

        await execute(async () => {
            await api.post('/auth/forgot-password', { email })
        })
    }

    const isFormDisabled = isLoading

    // Success state
    if (submitted) {
        return (
            <div className="min-h-screen flex items-center justify-center p-4 bg-background-primary">
                <div className="w-full max-w-md">
                    <div className="card p-8 text-center animate-fade-in">
                        <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                            <CheckCircle className="w-8 h-8 text-green-500" />
                        </div>
                        <h2 className="text-2xl font-bold text-text-primary mb-2">Check Your Email</h2>
                        <p className="text-text-secondary mb-6">
                            If an account exists for <span className="font-medium text-text-primary">{email}</span>,
                            you'll receive a password reset link shortly.
                        </p>
                        <Link href="/auth/login" className="btn btn-primary w-full py-3 inline-flex justify-center">
                            <ArrowLeft className="w-4 h-4 mr-2" />
                            Back to Login
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
                            <Mail className="w-6 h-6 text-accent-primary" />
                        </div>
                        <h1 className="text-2xl font-bold text-text-primary">Forgot Password?</h1>
                        <p className="text-text-secondary mt-2">
                            Enter your email and we'll send you a reset link.
                        </p>
                    </div>

                    {isError && error && (
                        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3 animate-fade-in">
                            <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                            <p className="text-red-500 text-sm">{error}</p>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-text-secondary mb-1">
                                Email Address
                            </label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                                <input
                                    ref={emailRef}
                                    id="email"
                                    type="email"
                                    value={email}
                                    onChange={handleInputChange}
                                    placeholder="you@example.com"
                                    className="input pl-10 w-full"
                                    disabled={isFormDisabled}
                                    autoComplete="email"
                                    required
                                />
                            </div>
                        </div>

                        <FormButton
                            isLoading={isLoading}
                            loadingText="Sending..."
                            fullWidth
                            className="py-3"
                        >
                            Send Reset Link
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
            </div>
        </div>
    )
}
