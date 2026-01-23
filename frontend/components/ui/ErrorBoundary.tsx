'use client'

import React, { Component, ReactNode } from 'react'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'
import Link from 'next/link'

interface ErrorBoundaryProps {
    children: ReactNode
    fallback?: ReactNode
    onError?: (error: Error, errorInfo: React.ErrorInfo) => void
}

interface ErrorBoundaryState {
    hasError: boolean
    error: Error | null
}

/**
 * Error boundary component for catching and handling React errors.
 * - Displays friendly error page
 * - Provides retry and home navigation
 * - Logs errors for observability
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props)
        this.state = { hasError: false, error: null }
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error }
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        // Log error for observability
        console.error('[ErrorBoundary] Caught error:', error)
        console.error('[ErrorBoundary] Error info:', errorInfo)

        // Call optional error handler
        this.props.onError?.(error, errorInfo)

        // In production, send to error tracking service
        if (process.env.NODE_ENV === 'production') {
            // sendToErrorService(error, errorInfo)
        }
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null })
    }

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback
            }

            return (
                <div className="min-h-screen flex items-center justify-center p-4 bg-background-primary">
                    <div className="max-w-md w-full text-center">
                        <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                            <AlertTriangle className="w-8 h-8 text-red-500" />
                        </div>

                        <h1 className="text-2xl font-bold text-text-primary mb-2">
                            Something went wrong
                        </h1>

                        <p className="text-text-secondary mb-6">
                            We're sorry, but something unexpected happened. Please try again or return to the homepage.
                        </p>

                        {process.env.NODE_ENV !== 'production' && this.state.error && (
                            <details className="mb-6 text-left">
                                <summary className="cursor-pointer text-sm text-text-muted hover:text-text-secondary">
                                    Technical details
                                </summary>
                                <pre className="mt-2 p-3 bg-background-tertiary rounded text-xs text-red-400 overflow-auto max-h-32">
                                    {this.state.error.toString()}
                                </pre>
                            </details>
                        )}

                        <div className="flex gap-3 justify-center">
                            <button
                                onClick={this.handleRetry}
                                className="btn btn-secondary flex items-center gap-2"
                            >
                                <RefreshCw className="w-4 h-4" />
                                Try Again
                            </button>
                            <Link href="/" className="btn btn-primary flex items-center gap-2">
                                <Home className="w-4 h-4" />
                                Go Home
                            </Link>
                        </div>
                    </div>
                </div>
            )
        }

        return this.props.children
    }
}

/**
 * Higher-order component for wrapping pages with error boundary
 */
export function withErrorBoundary<P extends object>(
    Component: React.ComponentType<P>,
    fallback?: ReactNode
) {
    return function WrappedComponent(props: P) {
        return (
            <ErrorBoundary fallback={fallback}>
                <Component {...props} />
            </ErrorBoundary>
        )
    }
}
